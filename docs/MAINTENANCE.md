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

There are **two distinct locations**, and they are not the same thing:

- **Workspace folder** — chosen per workspace; holds this workspace's YAML
  (`household.yml`, `accounts/*.yml`). You may have several workspaces.
- **Data folder** — a single, app-wide location configured in the XDG config
  (`data_folder` key; default `$XDG_DATA_HOME/qdvc-household-records/data`).
  It holds all the PDFs referenced by *every* workspace. Every document path is
  stored **relative to the data folder**, and a file can only be added as a
  document if it lives inside the data folder.

The data folder is configured in the Setup tab; the current workspace folder is
shown there too (info + open/change button).

## Data formats

Inside a workspace folder:

```
<workspace>/
    household.yml              people + zoneblocks (Setup-tab config)
    accounts/
        <account_id>.yml       one file per account, documents nested inside
```

The PDFs themselves live under the separate **data folder**, not here.

`household.yml` — IDs are slugified snake_case, derived from the name:

```yaml
people:
  - {id: freja, name: Freja}
  - {id: ludvig, name: Ludvig}
zoneblocks:
  - {id: bank_statements, name: Bank Statements, scope: both, icon: accessories-calculator-symbolic}
```

`accounts/freja_bank_of_atlantis.yml` — the file name IS the account id, which
combines the owner id (person id or `shared`) with the snake_case account name:

```yaml
id: freja_bank_of_atlantis
zone_key: bank_statements::freja       # zoneblock_id::person_id (or ::shared)
name: Bank of Atlantis
periodic: true
cycle_days: 30
notes: ""
documents:
  - id: doc-1a2b3c4d5e6f              # documents keep random ids (no name key)
    path: statements/2026-01.pdf       # RELATIVE to the DATA FOLDER
    statement_number: "001"
    date_issued: "2026-01-31"
    notes: ""
```

Colliding slugs are de-duplicated with a numeric suffix (`freja_2`,
`freja_bank_of_atlantis_2`). All writes are atomic (temp file + `os.replace`).

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
- `add_document(account, absolute_path, …)` — *link*: catalogue a file that is
  already inside the data folder (enforces relative path)
- `import_document(account, source_path, …)` — *import*: copy a file from
  anywhere into `<data_folder>/<account_id>/` (numeric suffix on name clash),
  then catalogue it
- `remove_document`
- `relativise / absolutise / is_inside`
- `is_fresh(account)` → True/False/None; `fresh_and_stale()`
- `validate()` → categorised problem lists

## Relative-path enforcement

`add_document` calls `relativise`, which uses `os.path.commonpath` to reject any
file whose absolute path is not inside the **data folder**, raising
`PathOutsideDataFolderError` (aliased as `PathOutsideWorkspaceError` for
compatibility). Both front-ends catch it and show an error, and their file
choosers open rooted at the data folder. Changing the data folder in Setup
re-opens the current workspace against the new folder.

## Freshness rule

`is_fresh` returns `None` for non-periodic / unconfigured accounts, `False` when
there are no dated documents, else `True` iff
`today − timedelta(cycle_days) < newest date_issued`.

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
it does not open the PDF. Use the "Open" button to launch the file.

The **data folder** is app-wide and configured in Preferences (Edit →
Preferences in GTK3; primary menu → Preferences in GTK4), not in the Setup tab,
because it is shared across all workspaces. The Setup tab configures per-house
data (people and zoneblocks), shown as editable lists: GTK4 gives each row an
edit and delete button with an "Add…" row beneath; GTK3 exposes edit/delete via
a right-click context menu with an "Add…" button beneath.

## Common maintenance tasks — where to touch

- **New document field:** add to `models.Document`, the load/save dicts in
  `workspace.py`, and Pane 4 in both `*_organiser_*` modules.
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
