"""GTK4 Setup view — data folder, people, and zoneblocks."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ..models import SCOPE_BOTH, SCOPE_INDIVIDUAL, SCOPE_SHARED  # noqa: E402
from ..ui_prefs import ZONEBLOCK_ICONS  # noqa: E402

_SCOPES = [(SCOPE_INDIVIDUAL, "Individual"), (SCOPE_SHARED, "Shared"),
           (SCOPE_BOTH, "Both")]


class SetupView(Gtk.ScrolledWindow):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        clamp = Adw.Clamp()
        self.set_child(clamp)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(16); box.set_margin_bottom(16)
        box.set_margin_start(12); box.set_margin_end(12)
        clamp.set_child(box)

        # data folder (app-wide PDF store, shared across workspaces)
        data_group = Adw.PreferencesGroup(
            title="Data folder",
            description="Shared across all workspaces. Every PDF must live "
                        "inside this folder; document paths are stored relative "
                        "to it.")
        self.data_row = Adw.ActionRow(title="Folder", subtitle="")
        dbtn = Gtk.Button(label="Change…")
        dbtn.set_valign(Gtk.Align.CENTER)
        dbtn.connect("clicked", self._on_change_data_folder)
        self.data_row.add_suffix(dbtn)
        data_group.add(self.data_row)
        box.append(data_group)

        # current workspace folder (info only)
        folder_group = Adw.PreferencesGroup(title="Current workspace folder")
        self.folder_row = Adw.ActionRow(title="Folder", subtitle="(no workspace open)")
        btn = Gtk.Button(label="Open / Change…")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda *_: self.window.action_open_workspace())
        self.folder_row.add_suffix(btn)
        folder_group.add(self.folder_row)
        box.append(folder_group)

        # people
        self.people_group = Adw.PreferencesGroup(title="People in the household")
        self.person_entry = Adw.EntryRow(title="Add a person (press Enter)")
        self.person_entry.connect("entry-activated", self._on_add_person)
        self.people_group.add(self.person_entry)
        box.append(self.people_group)

        # zoneblocks
        self.zb_group = Adw.PreferencesGroup(title="Zoneblocks")
        self.zb_name = Adw.EntryRow(title="Name (e.g. Bank Statements)")
        self.zb_scope = Adw.ComboRow(title="Scope")
        self.zb_scope.set_model(Gtk.StringList.new([s[1] for s in _SCOPES]))
        self.zb_scope.set_selected(2)
        self.zb_icon = Adw.ComboRow(title="Icon")
        self.zb_icon.set_model(Gtk.StringList.new([i[1] for i in ZONEBLOCK_ICONS]))
        add_zb = Adw.ActionRow(title="Add zoneblock")
        add_btn = Gtk.Button(label="Add"); add_btn.set_valign(Gtk.Align.CENTER)
        add_btn.connect("clicked", self._on_add_zoneblock)
        add_zb.add_suffix(add_btn)
        for r in (self.zb_name, self.zb_scope, self.zb_icon, add_zb):
            self.zb_group.add(r)
        box.append(self.zb_group)

        self._people_rows: list = []
        self._zb_rows: list = []

    def _on_change_data_folder(self, *_a) -> None:
        from gi.repository import Gio
        dlg = Gtk.FileDialog(title="Choose the data folder")
        dlg.set_initial_folder(
            Gio.File.new_for_path(self.window.config.data_folder))
        dlg.select_folder(self.window, None, self._on_data_folder_chosen)

    def _on_data_folder_chosen(self, dlg, result) -> None:
        try:
            folder = dlg.select_folder_finish(result)
        except Exception:
            return
        self.window.config.data_folder = folder.get_path()
        if self.window.workspace:
            self.window.open_workspace(self.window.workspace.root)
        else:
            self.refresh()

    def _on_add_person(self, entry) -> None:
        ws = self.window.workspace
        name = entry.get_text().strip()
        if ws and name:
            ws.add_person(name)
            entry.set_text("")
            self.window.refresh_all()

    def _on_add_zoneblock(self, *_a) -> None:
        ws = self.window.workspace
        name = self.zb_name.get_text().strip()
        if ws and name:
            scope = _SCOPES[self.zb_scope.get_selected()][0]
            icon = ZONEBLOCK_ICONS[self.zb_icon.get_selected()][0]
            ws.add_zoneblock(name, scope, icon)
            self.zb_name.set_text("")
            self.window.refresh_all()

    def _remove_person(self, person_id: str) -> None:
        ws = self.window.workspace
        if ws:
            ws.remove_person(person_id)
            self.window.refresh_all()

    def _remove_zoneblock(self, zb_id: str) -> None:
        ws = self.window.workspace
        if ws:
            ws.remove_zoneblock(zb_id)
            self.window.refresh_all()

    def refresh(self) -> None:
        ws = self.window.workspace
        self.data_row.set_subtitle(self.window.config.data_folder)
        self.folder_row.set_subtitle(ws.root if ws else "(no workspace open)")
        for r in self._people_rows:
            self.people_group.remove(r)
        for r in self._zb_rows:
            self.zb_group.remove(r)
        self._people_rows.clear()
        self._zb_rows.clear()
        if not ws:
            return
        for p in ws.people:
            row = Adw.ActionRow(title=p.name)
            btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", lambda _b, pid=p.id: self._remove_person(pid))
            row.add_suffix(btn)
            self.people_group.add(row)
            self._people_rows.append(row)
        scope_labels = dict(_SCOPES)
        for z in ws.zoneblocks:
            row = Adw.ActionRow(title=z.name,
                                subtitle=scope_labels.get(z.scope, z.scope))
            row.add_prefix(Gtk.Image.new_from_icon_name(z.icon))
            btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", lambda _b, zid=z.id: self._remove_zoneblock(zid))
            row.add_suffix(btn)
            self.zb_group.add(row)
            self._zb_rows.append(row)
