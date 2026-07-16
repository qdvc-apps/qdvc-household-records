"""Install the win.* Gio.SimpleActions for the GTK4 window."""
from __future__ import annotations

from gi.repository import Gio


def install_actions(window) -> None:
    specs = {
        "open_workspace": window.action_open_workspace,
        "new_workspace": window.action_new_workspace,
        "quit": lambda: window.app.quit(),
        "preferences": window.action_preferences,
        "validate": window.action_validate,
        "about": window.action_about,
        "reload": window.action_reload,
        "tab_home": lambda: window.select_view("home"),
        "tab_organiser": lambda: window.select_view("organiser"),
        "tab_setup": lambda: window.select_view("setup"),
    }
    window._win_actions = {}
    for name, cb in specs.items():
        act = Gio.SimpleAction.new(name, None)
        act.connect("activate", lambda _a, _p, c=cb: c())
        window.add_action(act)
        window._win_actions[name] = act


def set_action_enabled(window, name: str, enabled: bool) -> None:
    act = getattr(window, "_win_actions", {}).get(name)
    if act is not None:
        act.set_enabled(enabled)
