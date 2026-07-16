# GTK3 ↔ GTK4 comparison

Both front-ends sit on the same pure core (`qdvc/`) and only differ in view
mechanics.

## Element-by-element map

| Concern            | GTK3 (`qdvc/gtk3/`)                         | GTK4 / libadwaita (`qdvc/gtk4/`)                        |
|--------------------|---------------------------------------------|---------------------------------------------------------|
| Application        | `Gtk.Application` (`gtk3_app.py`)           | `Adw.Application` (`gtk4_app.py`)                        |
| Main container     | `Gtk.ApplicationWindow`                     | `Adw.ApplicationWindow` + `Adw.ToolbarView`             |
| Commands           | direct callbacks + `Gtk.AccelGroup`         | `Gio.SimpleAction` under `win.` (`gtk4_actions.py`)     |
| Top chrome         | menubar + toolbar + statusbar               | single `Adw.HeaderBar` + primary menu                   |
| Tab switching      | `Gtk.Notebook`                              | `Adw.ViewStack` + `Adw.ViewSwitcher`                    |
| Preferences        | `Gtk.Dialog` (`gtk3_preferences.py`)        | `Adw.PreferencesWindow`, live-apply (`gtk4_preferences.py`) |
| Toolbar-style pref | present (below/beside)                      | omitted (no toolbar)                                    |
| Backend selector   | `Gtk.ComboBoxText`                          | `Adw.ComboRow` ("takes effect after restart")           |
| Modal flows        | `dialog.run()`                              | async `Gtk.FileDialog` / `Adw.MessageDialog` callbacks  |
| Shortcuts          | accelerators via `AccelGroup`               | `set_accels_for_action` + `Gtk.ShortcutsWindow`         |
| Lists (panes)      | `Gtk.TreeView` + `Gtk.ListStore`            | `Gtk.ListBox` of rows / `Adw.PreferencesGroup` rows     |
| Detail editors     | `Gtk.Grid` of entries                       | `Adw.PreferencesGroup` with `EntryRow`/`SwitchRow`/`SpinRow` |

| Detail editors     | popup dialogs (`gtk3_dialogs.py`)           | popup dialogs (`gtk4_dialogs.py`)                       |
| Account settings   | right-click row → context menu → dialog     | right-click row (or "Settings…" button) → dialog        |
| Setup item editing | right-click row → context menu (edit/delete)| per-row edit + delete buttons; "Add…" row               |
| Date entry         | `Gtk.Calendar` in a dialog (0-based month)  | `Gtk.Calendar` in a dialog (`GLib.DateTime`, 1-based)   |
| Data folder        | Preferences dialog                          | Preferences window                                      |

## List-model / data-binding cheat-sheet

- **GTK3** panes use `Gtk.ListStore` columns; the last hidden column stores the
  record id (`zone.key`, `account.id`, `document.id`) so selection handlers can
  resolve back to the pure model via `workspace.account_by_id(...)` etc.
- **GTK4** panes use `Gtk.ListBox`; each `Gtk.ListBoxRow` carries the id as a
  plain Python attribute (`row._zone_key`, `row._account_id`, `row._doc_id`),
  read back in the `row-selected` handler.
- Freshness labels and date formatting come from `ui_prefs` in both — no
  toolkit-specific formatting.

## Window placement

The GTK3 window calls `set_position(Gtk.WindowPosition.CENTER)` so it opens
centred. GTK4 has no application-level window-positioning API — placement is the
compositor's responsibility — so the GTK4 window does not attempt to centre
itself. Both restore the saved size from the `window` config key.

## Parity notes

- `F2 rename` is marked GTK3-specific in `SHORTCUTS`; there is no rename command
  yet, so it is a placeholder and not surfaced in GTK4.
- Everything else (open/new workspace, quit, preferences, `Alt+1..3` tab
  switching) is shared across both toolkits from the single `SHORTCUTS` table.
