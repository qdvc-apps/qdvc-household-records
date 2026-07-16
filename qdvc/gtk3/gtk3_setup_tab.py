"""GTK3 Setup tab — people and zoneblocks as editable lists.

Each item's edit/delete options appear in a right-click context menu; an "Add"
button below each list opens a popup dialog (reused for editing). The data
folder is configured in Preferences, not here.
"""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from .gtk3_dialogs import (  # noqa: E402
    SCOPES,
    account_settings_dialog,  # noqa: F401  (kept for symmetry / reuse)
    person_dialog,
    zoneblock_dialog,
)


class SetupTab(Gtk.Box):
    def __init__(self, window) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.window = window
        self.set_border_width(10)

        intro = Gtk.Label(
            label="Configure the people in your household and the zoneblocks. "
                  "Their combination produces the zones in the Organiser tab. "
                  "Right-click an item to edit or delete it.",
            xalign=0.0)
        intro.set_line_wrap(True)
        intro.get_style_context().add_class("dim-label")
        self.pack_start(intro, False, False, 0)

        columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.pack_start(columns, True, True, 0)
        columns.pack_start(self._build_people(), True, True, 0)
        columns.pack_start(self._build_zoneblocks(), True, True, 0)

    def _ws(self):
        return self.window.workspace

    # ---- people ------------------------------------------------------
    def _build_people(self) -> Gtk.Widget:
        frame = Gtk.Frame(label="People in the household")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4,
                      border_width=8)
        frame.add(box)
        self.people_store = Gtk.ListStore(str, str)  # name, id
        self.people_view = Gtk.TreeView(model=self.people_store)
        self.people_view.append_column(
            Gtk.TreeViewColumn("Name", Gtk.CellRendererText(), text=0))
        self.people_view.connect("button-press-event", self._on_person_click)
        box.pack_start(self._scrolled(self.people_view), True, True, 0)

        add = Gtk.Button(label="Add person…")
        add.connect("clicked", self._on_add_person)
        box.pack_start(add, False, False, 0)
        return frame

    def _on_add_person(self, *_a) -> None:
        ws = self._ws()
        if not ws:
            return
        name = person_dialog(self.window, "")
        if name:
            ws.add_person(name)
            self.window.refresh_all()

    def _on_person_click(self, treeview, event) -> bool:
        if event.button != 3:
            return False
        info = treeview.get_path_at_pos(int(event.x), int(event.y))
        if info is None:
            return False
        treeview.get_selection().select_path(info[0])
        model, it = treeview.get_selection().get_selected()
        if not it:
            return False
        pid, name = model[it][1], model[it][0]
        menu = Gtk.Menu()
        edit = Gtk.MenuItem(label="Edit…")
        edit.connect("activate", lambda *_: self._edit_person(pid, name))
        menu.append(edit)
        delete = Gtk.MenuItem(label="Delete")
        delete.connect("activate", lambda *_: self._delete_person(pid))
        menu.append(delete)
        menu.show_all()
        menu.popup_at_pointer(event)
        return True

    def _edit_person(self, pid, name) -> None:
        new = person_dialog(self.window, name)
        if new:
            self._ws().update_person(pid, new)
            self.window.refresh_all()

    def _delete_person(self, pid) -> None:
        self._ws().remove_person(pid)
        self.window.refresh_all()

    # ---- zoneblocks --------------------------------------------------
    def _build_zoneblocks(self) -> Gtk.Widget:
        frame = Gtk.Frame(label="Zoneblocks")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4,
                      border_width=8)
        frame.add(box)
        self.zb_store = Gtk.ListStore(str, str, str, str)  # icon, name, scope, id
        self.zb_view = Gtk.TreeView(model=self.zb_store)
        col = Gtk.TreeViewColumn("Zoneblock")
        icon = Gtk.CellRendererPixbuf(); col.pack_start(icon, False)
        col.add_attribute(icon, "icon-name", 0)
        text = Gtk.CellRendererText(); col.pack_start(text, True)
        col.add_attribute(text, "text", 1)
        self.zb_view.append_column(col)
        self.zb_view.append_column(
            Gtk.TreeViewColumn("Scope", Gtk.CellRendererText(), text=2))
        self.zb_view.connect("button-press-event", self._on_zb_click)
        box.pack_start(self._scrolled(self.zb_view), True, True, 0)

        add = Gtk.Button(label="Add zoneblock…")
        add.connect("clicked", self._on_add_zoneblock)
        box.pack_start(add, False, False, 0)
        return frame

    def _on_add_zoneblock(self, *_a) -> None:
        ws = self._ws()
        if not ws:
            return
        vals = zoneblock_dialog(self.window, "", "both", "")
        if vals:
            ws.add_zoneblock(vals["name"], vals["scope"], vals["icon"])
            self.window.refresh_all()

    def _on_zb_click(self, treeview, event) -> bool:
        if event.button != 3:
            return False
        info = treeview.get_path_at_pos(int(event.x), int(event.y))
        if info is None:
            return False
        treeview.get_selection().select_path(info[0])
        model, it = treeview.get_selection().get_selected()
        if not it:
            return False
        zid = model[it][3]
        menu = Gtk.Menu()
        edit = Gtk.MenuItem(label="Edit…")
        edit.connect("activate", lambda *_: self._edit_zoneblock(zid))
        menu.append(edit)
        delete = Gtk.MenuItem(label="Delete")
        delete.connect("activate", lambda *_: self._delete_zoneblock(zid))
        menu.append(delete)
        menu.show_all()
        menu.popup_at_pointer(event)
        return True

    def _edit_zoneblock(self, zid) -> None:
        ws = self._ws()
        zb = next((z for z in ws.zoneblocks if z.id == zid), None)
        if not zb:
            return
        vals = zoneblock_dialog(self.window, zb.name, zb.scope, zb.icon)
        if vals:
            ws.update_zoneblock(zid, vals["name"], vals["scope"], vals["icon"])
            self.window.refresh_all()

    def _delete_zoneblock(self, zid) -> None:
        self._ws().remove_zoneblock(zid)
        self.window.refresh_all()

    # ---- helpers -----------------------------------------------------
    @staticmethod
    def _scrolled(child) -> Gtk.ScrolledWindow:
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_min_content_height(200)
        sw.add(child)
        return sw

    def refresh(self) -> None:
        self.people_store.clear()
        self.zb_store.clear()
        ws = self._ws()
        if not ws:
            return
        for p in ws.people:
            self.people_store.append([p.name, p.id])
        scope_labels = dict(SCOPES)
        for z in ws.zoneblocks:
            self.zb_store.append(
                [z.icon, z.name, scope_labels.get(z.scope, z.scope), z.id])
