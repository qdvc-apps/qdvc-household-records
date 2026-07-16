# Maintenance — QDVC Household Records

## Design philosophy

Files are the database. No SQLite, no ORM. All business data is plain-text YAML
in a user-chosen **workspace folder**; the app is a viewer/editor plus an
in-memory model. Any external edit is recovered by re-scanning (`Reload`).

The code splits into a **pure** layer (`qdvc/`, no `gi` imports) and two
**view** layers (`qdvc/gtk3/`, `qdvc/gtk4/`). The view layers never import each
other and never reimplement model/formatting logic — they call the pure core.

## Runtime requirements

Python 3.10+, PyGObject, exactly one toolkit (GTK 3 default, or GTK 4 +
libadwaita), and PyYAML.

## Directory & file layout

```
qdvc_household_records.py     Thin backend dispatcher.
qdvc/                          PURE package.
    __init__.py                APP_ID, APP_NAME, APP_SHORT, __version__.
    config.py                  YAML preferences at XDG location.
    models.py                  Person, ZoneBlock, Zone, Account, Document.
    naming.py                  id / slug / zone-key helpers.
    workspace.py               Workspace aggregate + file I/O + derivation.
    ui_prefs.py                SHORTCUTS, icon list, formatters, report.
    platform_utils.py          Open / reveal helpers.
    gtk3/                      GTK3 front-end (all gtk3_*).
    gtk4/                      GTK4 front-end (all gtk4_*).
docs/                          This file + the GTK3/GTK4 comparison.
tests/                         Model tests + fake-gi import smoke test.
```

## Two folders: workspace vs data

- **Workspace folder** — chosen per workspace; holds this workspace's YAML
  (`household.yml`, `accounts/*.yml`). The app reads and writes here.
- **Data folder** — a single, app-wide location configured in Preferences
  (`data_folder` key; default `$XDG_DATA_HOME/qdvc-household-records/data`). It
  holds the PDFs. **The app treats the data folder as strictly read-only: it
  never creates, moves, deletes, or modifies anything inside it**, and it does
  not even create the folder itself. Assume it may be a read-only mount.

## Folder-based documents (no importing)

An account points at a **folder** (stored relative to the data folder). The
top-level PDFs directly inside that folder ARE the account's documents,
discovered by `Workspace.scan_account`. There is no import/link/add-file/remove
concept — the folder's contents define the document set, no more and no less.

- Discovery is **top-level only**; if subfolders are present, `scan_account`
  sets `has_subfolders=True` and the UI shows a warning bar in Pane 3.
- Catalogue tags (statement no., date issued, notes) are stored in the account
  YAML keyed **by filename**. A catalogue entry whose file is absent from the
  folder is surfaced as a *missing* document (`present=False`) with its tags
  retained and shown greyed.

## Data formats

`accounts/<id>.yml`:

```yaml
id: freja_bank_of_atlantis
zone_key: bank_statements::freja
name: Bank of Atlantis
folder: freja/bank-of-atlantis     # RELATIVE to the data folder
periodic: true
cycle_days: 30
notes: ""
catalogues:                        # keyed by filename; empty entries omitted
  - filename: "2026-01.pdf"
    statement_number: "001"
    date_issued: "2026-01-31"
    notes: ""
```

Colliding slugs are de-duplicated with a numeric suffix. All WORKSPACE writes
are atomic (temp file + `os.replace`); nothing in the data folder is ever
written.

## Model / load pipeline

`Workspace.load(root)` reads `household.yml` then every `accounts/*.yml`.
`Workspace.zones()` derives Pane-1 zones on demand from `people × zoneblocks`
(individual → per-person; shared → one "Shared X"; both → both). Zones are
derived, never stored; accounts attach to a zone by its stable `zone_key`.

## Query & mutation API (workspace.py)

- `zones()`, `accounts_for_zone(key)`, `account_by_id(id)`, `zone_by_key(key)`
- `add_person / remove_person / update_person`
- `add_zoneblock / remove_zoneblock / update_zoneblock`
- `add_account`, `save_account`, `delete_account`, `update_account_settings`
- `set_account_folder(account, absolute_path)` — point at a folder inside the
  data folder (enforces containment); `clear_account_folder`
- `scan_account(account)` → `FolderScan(documents, has_subfolders, exists)`,
  read-only top-level PDF discovery merged with catalogue tags
- `set_catalogue(account, filename, stmt, date, notes)` — store/clear tags
- `document_path(account, filename)` — absolute path for opening
- `remove_document`  *(removed — folder contents define the document set)*
- `relativise / absolutise / is_inside`
- `is_fresh(account)` → True/False/None; `fresh_and_stale()`
- `validate()` → categorised problem lists

## Read-only data folder & containment

`set_account_folder` calls `relativise`, which uses `os.path.commonpath` to
reject any folder not inside the data folder (`PathOutsideDataFolderError`).
Beyond that, the workspace layer performs **no writes to the data folder at
all** — discovery (`scan_account`) only lists and reads. Opening a document
hands its absolute path to the OS default handler; the app itself never writes.

## Freshness rule

`is_fresh` returns `None` for non-periodic / unconfigured accounts, `False` when
there are no dated (present) documents, else `True` iff
`today − timedelta(cycle_days) < newest date_issued`. The newest date is taken
over the account's *discovered, present* documents (via `scan_account`), so it
reflects the current folder contents.

## UI layer

GTK3: menubar (File/Edit/View/Tools/Help) + toolbar subset + `Gtk.Notebook`
of three tabs + statusbar. GTK4: `Adw.ViewStack` + `Adw.ViewSwitcher`, single
header bar with a primary menu. Both call the same pure core.

Account settings (periodic / cycle / notes) are edited through an on-demand
popup dialog, reached by right-clicking an account row (or the "Settings…"
button in GTK4). There is no inline, always-live account editor — this both
declutters Pane 2 and avoids libadwaita `SpinRow` re-entrancy crashes.

Dates (a document's *date issued*) are entered with a calendar picker dialog
rather than a free-text field; the value is still stored as ISO `YYYY-MM-DD`.

Clicking a document in Pane 3 only selects it (showing its catalogue in Pane 4);
it does not open the PDF. Use the "Open" button to launch the file. Documents
are the top-level PDFs in the account's folder; there is no import/add. Set an
account's folder via right-click → "Set folder…" (or the "Set folder…" button).
Missing catalogued files are shown greyed, and a warning bar appears atop Pane 3
if the folder has subfolders.

In **GTK4**, Pane 1 (zones) is a sidebar via `Adw.OverlaySplitView`, toggled by
a header button shown only on the Organiser page. Panes 2 and 3 (accounts,
documents) sit in a `Gtk.Paned` whose start child has `resize=False`, so the
divider stays put and the panes don't auto-resize while navigating.

The **data folder** is app-wide and configured in Preferences (Edit →
Preferences in GTK3; primary menu → Preferences in GTK4), not in the Setup tab,
because it is shared across all workspaces. The Setup tab configures per-house
data (people and zoneblocks), shown as editable lists: GTK4 gives each row an
edit and delete button with an "Add…" row beneath; GTK3 exposes edit/delete via
a right-click context menu with an "Add…" button beneath.

## Common maintenance tasks — where to touch

- **New document/catalogue field:** add to `models.Catalogue` (and `Document`
  if it's a display field), the load/save in `workspace.py` (`_load_accounts`,
  `save_account`, and the merge in `scan_account`), and Pane 4 in both
  `*_organiser_*` modules.
- **New freshness logic:** edit `Workspace.is_fresh` only.
- **New shortcut/command:** add to `ui_prefs.SHORTCUTS`, wire in
  `gtk3_shortcuts.py` and `gtk4_actions.py`, add to both menus.
- **New icon choice for zoneblocks:** `ui_prefs.ZONEBLOCK_ICONS`.

## Testing

`tests/test_model.py` runs against the pure layer with no display.
`tests/test_import_smoke.py` imports every view module under a fake `gi` stub.
```
python3 -m py_compile qdvc/*.py qdvc/gtk3/*.py qdvc/gtk4/*.py qdvc_household_records.py
```

## Deployment

Ship the folder, install the `.desktop` launcher (see README), ensure
`StartupWMClass=qdvc-household-records` matches `GLib.set_prgname`.
