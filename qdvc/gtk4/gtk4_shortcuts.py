"""GTK4 keyboard-shortcuts window, built from the shared SHORTCUTS table."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from ..ui_prefs import SHORTCUTS  # noqa: E402


def build_shortcuts_window(parent) -> Gtk.ShortcutsWindow:
    win = Gtk.ShortcutsWindow(transient_for=parent, modal=True)
    section = Gtk.ShortcutsSection(visible=True)
    group = Gtk.ShortcutsGroup(title="General", visible=True)
    for _action, accel, label, scope in SHORTCUTS:
        if scope == "gtk3":
            continue
        sc = Gtk.ShortcutsShortcut(visible=True, title=label, accelerator=accel)
        group.add_shortcut(sc)
    section.add_group(group)
    win.add_section(section)
    return win
