"""GTK3 Preferences dialog (incl. backend selector)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402


class PreferencesDialog:
    def __init__(self, window) -> None:
        self.window = window
        self.config = window.config
        self.dialog = Gtk.Dialog(title="Preferences", transient_for=window,
                                 modal=True)
        self.dialog.add_button("Close", Gtk.ResponseType.CLOSE)
        box = self.dialog.get_content_area()
        box.set_spacing(8)
        box.set_border_width(12)

        # Data folder (app-wide, shared across all workspaces)
        box.pack_start(Gtk.Label(
            label="Data folder (shared across all workspaces)",
            xalign=0.0), False, False, 0)
        drow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.data_label = Gtk.Label(label=self.config.data_folder, xalign=0.0)
        self.data_label.set_selectable(True)
        self.data_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        dbtn = Gtk.Button(label="Change…")
        dbtn.connect("clicked", self._on_change_data_folder)
        drow.pack_start(self.data_label, True, True, 0)
        drow.pack_start(dbtn, False, False, 0)
        box.pack_start(drow, False, False, 0)

        # Toolbar style
        box.pack_start(Gtk.Label(label="Toolbar style", xalign=0.0), False, False, 0)
        self.toolbar_combo = Gtk.ComboBoxText()
        self.toolbar_combo.append("both", "Icons above labels")
        self.toolbar_combo.append("beside", "Icons beside labels")
        self.toolbar_combo.set_active_id(self.config.toolbar_style)
        self.toolbar_combo.connect("changed", self._on_toolbar_changed)
        box.pack_start(self.toolbar_combo, False, False, 0)

        # Backend selector (takes effect next launch)
        box.pack_start(Gtk.Label(label="UI backend (takes effect after restart)",
                                 xalign=0.0), False, False, 0)
        self.backend_combo = Gtk.ComboBoxText()
        self.backend_combo.append("gtk3", "GTK 3 (classic)")
        self.backend_combo.append("gtk4", "GTK 4 / libadwaita")
        self.backend_combo.set_active_id(self.config.ui_backend)
        self.backend_combo.connect("changed", self._on_backend_changed)
        box.pack_start(self.backend_combo, False, False, 0)

        # Reopen last
        self.reopen = Gtk.CheckButton(label="Reopen last workspace on launch")
        self.reopen.set_active(bool(self.config.get("reopen_last", True)))
        self.reopen.connect("toggled",
                            lambda w: self.config.set("reopen_last", w.get_active()))
        box.pack_start(self.reopen, False, False, 0)

    def _on_toolbar_changed(self, combo) -> None:
        self.config.toolbar_style = combo.get_active_id()
        self.window.apply_toolbar_style()

    def _on_change_data_folder(self, _btn) -> None:
        dlg = Gtk.FileChooserDialog(
            title="Choose the data folder", parent=self.dialog,
            action=Gtk.FileChooserAction.SELECT_FOLDER)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Select", Gtk.ResponseType.OK)
        dlg.set_current_folder(self.config.data_folder)
        if dlg.run() == Gtk.ResponseType.OK:
            path = dlg.get_filename()
            dlg.destroy()
            self.config.data_folder = path
            self.data_label.set_text(self.config.data_folder)
            if self.window.workspace:
                self.window.open_workspace(self.window.workspace.root)
        else:
            dlg.destroy()

    def _on_backend_changed(self, combo) -> None:
        self.config.ui_backend = combo.get_active_id()

    def run_and_apply(self) -> None:
        self.dialog.show_all()
        self.dialog.run()
        self.dialog.destroy()
