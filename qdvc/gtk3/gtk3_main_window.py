"""GTK3 MainWindow: menubar + toolbar + notebook content + statusbar."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from .. import APP_NAME  # noqa: E402
from ..workspace import Workspace  # noqa: E402
from .gtk3_home_tab import HomeTab  # noqa: E402
from .gtk3_organiser_tab import OrganiserTab  # noqa: E402
from .gtk3_setup_tab import SetupTab  # noqa: E402
from .gtk3_shortcuts import install_shortcuts  # noqa: E402


def menu_item(label: str, icon: str | None = None) -> Gtk.MenuItem:
    """Build a menu item with optional icon (no ImageMenuItem)."""
    item = Gtk.MenuItem()
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    if icon:
        box.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU),
                       False, False, 0)
    box.pack_start(Gtk.Label(label=label, xalign=0.0), True, True, 0)
    item.add(box)
    return item


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app) -> None:
        super().__init__(application=app, title=APP_NAME)
        self.app = app
        self.config = app.config
        self.workspace: Workspace | None = None

        from .gtk3_app import ICON_NAME
        self.set_icon_name(ICON_NAME)
        w, h = self.config.get("window", [1000, 680])
        self.set_default_size(int(w), int(h))
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("delete-event", self._on_delete)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)

        self.accel_group = Gtk.AccelGroup()
        self.add_accel_group(self.accel_group)

        self._toolbar_buttons: list[Gtk.ToolButton] = []
        root.pack_start(self._build_menubar(), False, False, 0)
        self.toolbar = self._build_toolbar()
        root.pack_start(self.toolbar, False, False, 0)

        self.notebook = Gtk.Notebook()
        root.pack_start(self.notebook, True, True, 0)

        self.organiser_tab = OrganiserTab(self)
        self.home_tab = HomeTab(self)
        self.setup_tab = SetupTab(self)

        self.notebook.append_page(self.home_tab, Gtk.Label(label="Home"))
        self.notebook.append_page(self.organiser_tab, Gtk.Label(label="Organiser"))
        self.notebook.append_page(self.setup_tab, Gtk.Label(label="Setup"))
        self.notebook.connect("switch-page", self._on_tab_switch)

        self.statusbar = Gtk.Statusbar()
        self._status_ctx = self.statusbar.get_context_id("main")
        root.pack_start(self.statusbar, False, False, 0)

        install_shortcuts(self)
        self.apply_toolbar_style()
        self._update_actions_sensitivity()
        self.show_all()
        self.set_status("No workspace open.")

    # ---- menubar / toolbar ------------------------------------------
    def _build_menubar(self) -> Gtk.MenuBar:
        bar = Gtk.MenuBar()

        file_menu = Gtk.Menu()
        mi = menu_item("New Workspace…", "document-new"); mi.connect("activate", lambda *_: self.action_new_workspace()); file_menu.append(mi)
        mi = menu_item("Open Workspace…", "document-open"); mi.connect("activate", lambda *_: self.action_open_workspace()); file_menu.append(mi)
        file_menu.append(Gtk.SeparatorMenuItem())
        mi = menu_item("Quit", "application-exit"); mi.connect("activate", lambda *_: self.app.quit()); file_menu.append(mi)
        top = Gtk.MenuItem(label="File"); top.set_submenu(file_menu); bar.append(top)

        edit_menu = Gtk.Menu()
        mi = menu_item("Preferences", "preferences-system"); mi.connect("activate", lambda *_: self.action_preferences()); edit_menu.append(mi)
        top = Gtk.MenuItem(label="Edit"); top.set_submenu(edit_menu); bar.append(top)

        view_menu = Gtk.Menu()
        for idx, name in enumerate(("Home", "Organiser", "Setup")):
            mi = menu_item(name)
            mi.connect("activate", lambda _w, i=idx: self.notebook.set_current_page(i))
            view_menu.append(mi)
        top = Gtk.MenuItem(label="View"); top.set_submenu(view_menu); bar.append(top)

        tools_menu = Gtk.Menu()
        mi = menu_item("Validate Workspace", "dialog-warning"); mi.connect("activate", lambda *_: self.action_validate()); tools_menu.append(mi)
        top = Gtk.MenuItem(label="Tools"); top.set_submenu(tools_menu); bar.append(top)

        help_menu = Gtk.Menu()
        mi = menu_item("About", "help-about"); mi.connect("activate", lambda *_: self.action_about()); help_menu.append(mi)
        top = Gtk.MenuItem(label="Help"); top.set_submenu(help_menu); bar.append(top)
        return bar

    def _build_toolbar(self) -> Gtk.Toolbar:
        tb = Gtk.Toolbar()
        specs = [
            ("document-open", "Open", self.action_open_workspace),
            ("view-refresh", "Reload", self.action_reload),
            ("dialog-warning", "Validate", self.action_validate),
        ]
        for icon, label, cb in specs:
            btn = Gtk.ToolButton(icon_name=icon, label=label)
            btn.connect("clicked", lambda _w, c=cb: c())
            tb.insert(btn, -1)
            self._toolbar_buttons.append(btn)
        return tb

    def apply_toolbar_style(self) -> None:
        style = self.config.toolbar_style
        self.toolbar.set_style(Gtk.ToolbarStyle.BOTH if style == "both"
                               else Gtk.ToolbarStyle.BOTH_HORIZ)

    # ---- status ------------------------------------------------------
    def set_status(self, text: str) -> None:
        self.statusbar.pop(self._status_ctx)
        self.statusbar.push(self._status_ctx, text)

    # ---- workspace lifecycle ----------------------------------------
    def action_new_workspace(self) -> None:
        dlg = Gtk.FileChooserDialog(
            title="Choose a folder for the new workspace", parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Create Here", Gtk.ResponseType.OK)
        if dlg.run() == Gtk.ResponseType.OK:
            path = dlg.get_filename()
            dlg.destroy()
            Workspace.create(path, self.config.data_folder)
            self.open_workspace(path)
        else:
            dlg.destroy()

    def action_open_workspace(self) -> None:
        dlg = Gtk.FileChooserDialog(
            title="Open workspace folder", parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Open", Gtk.ResponseType.OK)
        if dlg.run() == Gtk.ResponseType.OK:
            path = dlg.get_filename()
            dlg.destroy()
            self.open_workspace(path)
        else:
            dlg.destroy()

    def open_workspace(self, path: str) -> None:
        try:
            self.workspace = Workspace.load(path, self.config.data_folder)
        except Exception as exc:
            self._error(f"Could not open workspace:\n{exc}")
            return
        self.config.push_recent(path)
        self.set_title(f"{APP_NAME} — {path}")
        self.refresh_all()
        self._update_actions_sensitivity()
        self.set_status(f"Workspace: {path}")

    def action_reload(self) -> None:
        if self.workspace:
            self.workspace.reload()
            self.refresh_all()
            self.set_status("Workspace reloaded.")

    def refresh_all(self) -> None:
        self.setup_tab.refresh()
        self.organiser_tab.refresh()
        self.home_tab.refresh()

    # ---- navigation from Home ---------------------------------------
    def jump_to_account(self, account_id: str) -> None:
        self.notebook.set_current_page(1)  # Organiser
        self.organiser_tab.select_account_by_id(account_id)

    # ---- tools -------------------------------------------------------
    def action_validate(self) -> None:
        if not self.workspace:
            return
        from ..ui_prefs import format_validation_report
        report = format_validation_report(self.workspace.validate())
        self._info("Validation report", report)

    def action_preferences(self) -> None:
        from .gtk3_preferences import PreferencesDialog
        PreferencesDialog(self).run_and_apply()

    def action_about(self) -> None:
        from .. import __version__
        about = Gtk.AboutDialog(transient_for=self, modal=True)
        about.set_program_name(APP_NAME)
        about.set_version(__version__)
        about.set_comments("Organise a household folder of PDF documents.")
        about.run()
        about.destroy()

    # ---- sensitivity -------------------------------------------------
    def _update_actions_sensitivity(self) -> None:
        has_ws = self.workspace is not None
        # Reload + Validate are workspace-scoped (indices 1, 2).
        for btn in self._toolbar_buttons[1:]:
            btn.set_sensitive(has_ws)

    def _on_tab_switch(self, _nb, _page, _num) -> None:
        self._update_actions_sensitivity()

    # ---- helpers -----------------------------------------------------
    def _error(self, text: str) -> None:
        dlg = Gtk.MessageDialog(transient_for=self, modal=True,
                                message_type=Gtk.MessageType.ERROR,
                                buttons=Gtk.ButtonsType.CLOSE, text=text)
        dlg.run(); dlg.destroy()

    def _info(self, title: str, text: str) -> None:
        dlg = Gtk.MessageDialog(transient_for=self, modal=True,
                                message_type=Gtk.MessageType.INFO,
                                buttons=Gtk.ButtonsType.CLOSE, text=title)
        dlg.format_secondary_text(text)
        dlg.run(); dlg.destroy()

    def _on_delete(self, *_a) -> bool:
        alloc = self.get_allocation()
        self.config.set("window", [alloc.width, alloc.height])
        return False
