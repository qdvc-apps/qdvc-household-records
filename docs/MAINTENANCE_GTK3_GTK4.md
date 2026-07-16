# GTK3 ↔ GTK4 comparison

Both front-ends sit on the same pure core (`qdvc/`) and only differ in view
mechanics.

## Element-by-element map

| Concern            | GTK3 (`qdvc/gtk3/`)                         | GTK4 / libadwaita (`qdvc/gtk4/`)                        |
|--------------------|---------------------------------------------|---------------------------------------------------------|
| Application        | `Gtk.Application` (`gtk3_app.py`)           | `Adw.Application` (`gtk4_app.py`)                        |
| Main container     | `Gtk.ApplicationWindow`                     | `Adw.ApplicationWindow` + `Adw.ToolbarView`             |
| Commands           | menu items own accelerators on the window `AccelGroup` | `Gio.SimpleAction` under `win.` (`gtk4_actions.py`)     |
| Top chrome         | menubar + toolbar + statusbar               | single `Adw.HeaderBar` + primary menu                   |
| Tab switching      | `Gtk.Notebook`                              | `Adw.ViewStack` + `Adw.ViewSwitcher`                    |
| Preferences        | `Gtk.Dialog` (`gtk3_preferences.py`)        | `Adw.PreferencesWindow`, live-apply (`gtk4_preferences.py`) |
| Toolbar-style pref | present (below/beside)                      | omitted (no toolbar)                                    |
| Backend selector   | `Gtk.ComboBoxText`                          | `Adw.ComboRow` ("takes effect after restart")           |
| Modal flows        | `dialog.run()`                              | async `Gtk.FileDialog` / `Adw.MessageDialog` callbacks  |
| Shortcuts          | menu-item accelerators (no separate module) | `set_accels_for_action` + `Gtk.ShortcutsWindow`         |
| Lists (panes)      | `Gtk.TreeView` + `Gtk.ListStore`            | `Gtk.ListBox` of rows / `Adw.PreferencesGroup` rows     |
| Menu items         | `Gtk.ImageMenuItem` + mnemonics + `add_accelerator` (MATE look, per spec §8) | model-based `Gio.Menu` primary menu |
| Accelerators       | owned by the menu items' `add_accelerator` | `set_accels_for_action` on `win.*` |
| Organiser Pane 1  | column in a `Gtk.Paned` chain; counts via a right-aligned cell renderer | sidebar via `Adw.OverlaySplitView`; counts via a badge label |
| Sidebar width     | natural (tree column)                       | pinned min==max to fit longest label; never auto-resizes |
| Add account       | right-click zone row or Pane-2 blank space → menu | right-click zone row or Pane-2 blank space → popover menu |
| Organiser P2/P3   | `Gtk.Paned` chain                           | `Gtk.Paned`, start child `resize=False` (no auto-resize)|
| Documents source  | top-level PDFs in the account's folder      | same (shared core `scan_account`)                       |
| Pane 3 rows       | pixbuf `application-pdf` + `document_label` (single column, no filename) | `application-pdf` image + `document_label` (single line, no filename) |
| Open button       | `Gtk.Image` `application-pdf` + label        | `Adw.ButtonContent` icon `application-pdf` + label      |
| Subfolder warning | `Gtk.InfoBar` atop Pane 3                    | `Adw.Banner` atop Pane 3                                 |
| Detail editors    | popup dialogs (`gtk3_dialogs.py`)           | popup dialogs (`gtk4_dialogs.py`)                       |
| Account settings   | right-click row → context menu → dialog     | right-click row → popover menu → dialog                 |
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
