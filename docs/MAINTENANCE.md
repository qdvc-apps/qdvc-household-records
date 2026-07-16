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

## Data formats

Inside a workspace:

```
<workspace>/
    household.yml              people + zoneblocks (Setup-tab config)
    accounts/
        <account_id>.yml       one file per account, documents nested inside
    <your document files>      PDFs etc., referenced by RELATIVE path
```

`household.yml`:

```yaml
people:
  - {id: person-abc123, name: Freja}
zoneblocks:
  - {id: zb-def456, name: Bank Statements, scope: both, icon: accessories-calculator-symbolic}
```

`accounts/<id>.yml`:

```yaml
id: acc-...
zone_key: zb-def456::person-abc123     # zoneblock_id::person_id (or ::shared)
name: Bank of Atlantis
periodic: true
cycle_days: 30
notes: ""
documents:
  - id: doc-...
    path: statements/2026-01.pdf       # RELATIVE to the workspace root
    statement_number: "001"
    date_issued: "2026-01-31"
    notes: ""
```

All writes are atomic (temp file + `os.replace`).

## Model / load pipeline

`Workspace.load(root)` reads `household.yml` then every `accounts/*.yml`.
`Workspace.zones()` derives Pane-1 zones on demand from `people × zoneblocks`
(individual → per-person; shared → one "Shared X"; both → both). Zones are
derived, never stored; accounts attach to a zone by its stable `zone_key`.

## Query & mutation API (workspace.py)

- `zones()`, `accounts_for_zone(key)`, `account_by_id(id)`, `zone_by_key(key)`
- `add_person / remove_person`, `add_zoneblock / remove_zoneblock`
- `add_account`, `save_account`, `delete_account`
- `add_document(account, absolute_path, …)` — enforces relative path
- `remove_document`
- `relativise / absolutise / is_inside`
- `is_fresh(account)` → True/False/None; `fresh_and_stale()`
- `validate()` → categorised problem lists

## Relative-path enforcement

`add_document` calls `relativise`, which uses `os.path.commonpath` to reject any
file whose absolute path is not inside the workspace root, raising
`PathOutsideWorkspaceError`. Both front-ends catch it and show an error.

## Freshness rule

`is_fresh` returns `None` for non-periodic / unconfigured accounts, `False` when
there are no dated documents, else `True` iff
`today − timedelta(cycle_days) < newest date_issued`.

## UI layer

GTK3: menubar (File/Edit/View/Tools/Help) + toolbar subset + `Gtk.Notebook`
of three tabs + statusbar. GTK4: `Adw.ViewStack` + `Adw.ViewSwitcher`, single
header bar with a primary menu. Both call the same pure core.

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
