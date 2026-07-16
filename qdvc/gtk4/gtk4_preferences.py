"""GTK4 Adw.PreferencesWindow (live-apply + backend selector)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

_BACKENDS = [("gtk3", "GTK 3 (classic)"), ("gtk4", "GTK 4 / libadwaita")]


class PreferencesWindow(Adw.PreferencesWindow):
    def __init__(self, window) -> None:
        super().__init__(transient_for=window, modal=True)
        self.config = window.config
        self.set_title("Preferences")

        page = Adw.PreferencesPage()
        self.add(page)
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
