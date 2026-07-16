"""GTK4 main window: Adw.ViewStack + header bar + primary menu."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

from .. import APP_NAME  # noqa: E402
from ..workspace import Workspace  # noqa: E402
from .gtk4_actions import install_actions, set_action_enabled  # noqa: E402
from .gtk4_home_view import HomeView  # noqa: E402
from .gtk4_organiser_view import OrganiserView  # noqa: E402
from .gtk4_setup_view import SetupView  # noqa: E402


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app) -> None:
        super().__init__(application=app, title=APP_NAME)
        self.app = app
        self.config = app.config
        self.workspace: Workspace | None = None

        from .gtk4_app import ICON_NAME
        self.set_icon_name(ICON_NAME)
        w, h = self.config.get("window", [1000, 680])
        self.set_default_size(int(w), int(h))
        self.connect("close-request", self._on_close)

        install_actions(self)

        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        self.stack = Adw.ViewStack()
        self.organiser_view = OrganiserView(self)
        self.home_view = HomeView(self)
        self.setup_view = SetupView(self)
        self.stack.add_titled(self.home_view, "home", "Home").set_icon_name("go-home-symbolic")
        self.stack.add_titled(self.organiser_view, "organiser", "Organiser").set_icon_name("view-list-symbolic")
        self.stack.add_titled(self.setup_view, "setup", "Setup").set_icon_name("emblem-system-symbolic")

        header = Adw.HeaderBar()
        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)

        open_btn = Gtk.Button.new_from_icon_name("document-open-symbolic")
        open_btn.set_tooltip_text("Open workspace")
        open_btn.set_action_name("win.open_workspace")
        header.pack_start(open_btn)

        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_btn.set_primary(True)
        menu_btn.set_menu_model(self._build_menu())
        header.pack_end(menu_btn)

        toolbar_view.add_top_bar(header)
        toolbar_view.set_content(self.stack)

        self._update_actions_sensitivity()

    def _build_menu(self) -> Gio.Menu:
        menu = Gio.Menu()
        ws_section = Gio.Menu()
        ws_section.append("New Workspace", "win.new_workspace")
        ws_section.append("Reload", "win.reload")
        ws_section.append("Validate Workspace", "win.validate")
        menu.append_section(None, ws_section)
        end = Gio.Menu()
        end.append("Preferences", "win.preferences")
        end.append("Keyboard Shortcuts", "win.shortcuts")
        end.append("About", "win.about")
        menu.append_section(None, end)
        self._install_shortcuts_action()
        return menu

    def _install_shortcuts_action(self) -> None:
        if getattr(self, "_shortcuts_installed", False):
            return
        act = Gio.SimpleAction.new("shortcuts", None)
        act.connect("activate", lambda *_: self._show_shortcuts())
        self.add_action(act)
        self._shortcuts_installed = True

    def _show_shortcuts(self) -> None:
        from .gtk4_shortcuts import build_shortcuts_window
        build_shortcuts_window(self).present()

    def select_view(self, name: str) -> None:
        self.stack.set_visible_child_name(name)

    # ---- workspace lifecycle ----------------------------------------
    def action_new_workspace(self) -> None:
        dlg = Gtk.FileDialog(title="Choose a folder for the new workspace")
        dlg.select_folder(self, None, self._on_new_folder)

    def _on_new_folder(self, dlg, result) -> None:
        try:
            folder = dlg.select_folder_finish(result)
        except Exception:
            return
        path = folder.get_path()
        Workspace.create(path, self.config.data_folder)
        self.open_workspace(path)

    def action_open_workspace(self) -> None:
        dlg = Gtk.FileDialog(title="Open workspace folder")
        dlg.select_folder(self, None, self._on_open_folder)

    def _on_open_folder(self, dlg, result) -> None:
        try:
            folder = dlg.select_folder_finish(result)
        except Exception:
            return
        self.open_workspace(folder.get_path())

    def open_workspace(self, path: str) -> None:
        try:
            self.workspace = Workspace.load(path, self.config.data_folder)
        except Exception as exc:
            self._error(f"Could not open workspace: {exc}")
            return
        self.config.push_recent(path)
        self.set_title(f"{APP_NAME} — {path}")
        self.refresh_all()
        self._update_actions_sensitivity()

    def action_reload(self) -> None:
        if self.workspace:
            self.workspace.reload()
            self.refresh_all()

    def refresh_all(self) -> None:
        self.setup_view.refresh()
        self.organiser_view.refresh()
        self.home_view.refresh()

    def jump_to_account(self, account_id: str) -> None:
        self.select_view("organiser")
        self.organiser_view.select_account_by_id(account_id)

    def action_validate(self) -> None:
        if not self.workspace:
            return
        from ..ui_prefs import format_validation_report
        report = format_validation_report(self.workspace.validate())
        self._message("Validation report", report)

    def action_preferences(self) -> None:
        from .gtk4_preferences import PreferencesWindow
        PreferencesWindow(self).present()

    def action_about(self) -> None:
        from .. import __version__
        about = Adw.AboutWindow(
            transient_for=self, application_name=APP_NAME, version=__version__,
            comments="Organise a household folder of PDF documents.")
        about.present()

    def _update_actions_sensitivity(self) -> None:
        has_ws = self.workspace is not None
        for name in ("reload", "validate"):
            set_action_enabled(self, name, has_ws)

    # ---- dialogs -----------------------------------------------------
    def _error(self, text: str) -> None:
        self._message("Error", text)

    def _message(self, title: str, text: str) -> None:
        dlg = Adw.MessageDialog(transient_for=self, heading=title, body=text)
        dlg.add_response("ok", "OK")
        dlg.present()

    def _on_close(self, *_a) -> bool:
        self.config.set("window", [self.get_width(), self.get_height()])
        return False
