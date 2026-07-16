"""GTK4 Adw.PreferencesWindow (live-apply + backend selector)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

_BACKENDS = [("gtk3", "GTK 3 (classic)"), ("gtk4", "GTK 4 / libadwaita")]


class PreferencesWindow(Adw.PreferencesWindow):
    def __init__(self, window) -> None:
        super().__init__(transient_for=window, modal=True)
        self.window = window
        self.config = window.config
        self.set_title("Preferences")

        page = Adw.PreferencesPage()
        self.add(page)

        # data folder (app-wide, shared across all workspaces)
        data_group = Adw.PreferencesGroup(
            title="Data folder",
            description="Shared across all workspaces. Every PDF must live "
                        "inside this folder; document paths are stored relative "
                        "to it.")
        page.add(data_group)
        self.data_row = Adw.ActionRow(title="Folder",
                                      subtitle=self.config.data_folder)
        dbtn = Gtk.Button(label="Change…")
        dbtn.set_valign(Gtk.Align.CENTER)
        dbtn.connect("clicked", self._on_change_data_folder)
        self.data_row.add_suffix(dbtn)
        data_group.add(self.data_row)

        group = Adw.PreferencesGroup(title="General")
        page.add(group)

        # reopen last
        self.reopen = Adw.SwitchRow(title="Reopen last workspace on launch")
        self.reopen.set_active(bool(self.config.get("reopen_last", True)))
        self.reopen.connect(
            "notify::active",
            lambda w, _p: self.config.set("reopen_last", w.get_active()))
        group.add(self.reopen)

        # backend selector (no toolbar style in GTK4)
        self.backend = Adw.ComboRow(title="UI backend",
                                    subtitle="Takes effect after restart")
        self.backend.set_model(Gtk.StringList.new([b[1] for b in _BACKENDS]))
        current = self.config.ui_backend
        self.backend.set_selected(0 if current == "gtk3" else 1)
        self.backend.connect("notify::selected", self._on_backend)
        group.add(self.backend)

    def _on_backend(self, row, _p) -> None:
        self.config.ui_backend = _BACKENDS[row.get_selected()][0]

    def _on_change_data_folder(self, *_a) -> None:
        dlg = Gtk.FileDialog(title="Choose the data folder")
        dlg.set_initial_folder(Gio.File.new_for_path(self.config.data_folder))
        dlg.select_folder(self, None, self._on_data_folder_chosen)

    def _on_data_folder_chosen(self, dlg, result) -> None:
        try:
            folder = dlg.select_folder_finish(result)
        except Exception:
            return
        self.config.data_folder = folder.get_path()
        self.data_row.set_subtitle(self.config.data_folder)
        # re-point the open workspace at the new data folder
        if self.window.workspace:
            self.window.open_workspace(self.window.workspace.root)
