"""GTK3 shortcut wiring, driven by the shared SHORTCUTS table."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from ..ui_prefs import SHORTCUTS  # noqa: E402


def install_shortcuts(window) -> None:
    ag = window.accel_group

    handlers = {
        "open_workspace": window.action_open_workspace,
        "new_workspace": window.action_new_workspace,
        "quit": window.app.quit,
        "preferences": window.action_preferences,
        "tab_home": lambda: window.notebook.set_current_page(0),
        "tab_organiser": lambda: window.notebook.set_current_page(1),
        "tab_setup": lambda: window.notebook.set_current_page(2),
    }

    for action, accel, _label, scope in SHORTCUTS:
        if scope == "gtk4":
            continue
        cb = handlers.get(action)
        if cb is None:
            continue
        key, mods = Gtk.accelerator_parse(accel)
        if key == 0:
            continue
        ag.connect(key, mods, Gtk.AccelFlags.VISIBLE,
                   lambda *_a, c=cb: (c(), True)[1])
