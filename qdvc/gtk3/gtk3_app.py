"""GTK3 Gtk.Application bootstrap."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from .. import APP_ID, APP_SHORT  # noqa: E402
from ..config import Config  # noqa: E402

GLib.set_prgname(f"qdvc-{APP_SHORT}")

# Themed freedesktop icon; overridable here.
ICON_NAME = "folder-documents"


class HouseholdApp(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.config = Config()
        self.window = None
        self._pending_open: str | None = None

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        icon = self.config.get("custom_icon") or ICON_NAME
        Gtk.Window.set_default_icon_name(ICON_NAME)
        if isinstance(icon, str) and icon and icon != ICON_NAME:
            try:
                Gtk.Window.set_default_icon_from_file(icon)
            except Exception:
                Gtk.Window.set_default_icon_name(ICON_NAME)

    def _ensure_window(self):
        from .gtk3_main_window import MainWindow
        if self.window is None:
            self.window = MainWindow(self)
        return self.window

    def do_activate(self) -> None:
        win = self._ensure_window()
        if self._pending_open:
            win.open_workspace(self._pending_open)
            self._pending_open = None
        elif self.config.get("reopen_last", True):
            last = self.config.get("last_workspace")
            if last:
                win.open_workspace(last)
        win.present()

    def do_open(self, files, n_files, hint) -> None:
        if files:
            self._pending_open = files[0].get_path()
        self.do_activate()


def main(argv: list[str]) -> int:
    app = HouseholdApp()
    return app.run(argv)
