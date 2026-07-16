"""GTK3 Setup tab — data folder, people, and zoneblocks."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from ..models import SCOPE_BOTH, SCOPE_INDIVIDUAL, SCOPE_SHARED  # noqa: E402
from ..ui_prefs import ZONEBLOCK_ICONS  # noqa: E402

_SCOPES = [(SCOPE_INDIVIDUAL, "Individual"), (SCOPE_SHARED, "Shared"),
           (SCOPE_BOTH, "Both")]


class SetupTab(Gtk.Box):
    def __init__(self, window) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.window = window
        self.set_border_width(10)

        # ---- data folder --------------------------------------------
        folder_frame = Gtk.Frame(label="Workspace data folder")
        fbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
                       border_width=8)
        self.folder_label = Gtk.Label(label="(no workspace open)", xalign=0.0)
        self.folder_label.set_selectable(True)
        btn = Gtk.Button(label="Open / Change…")
        btn.connect("clicked", lambda *_: self.window.action_open_workspace())
        fbox.pack_start(self.folder_label, True, True, 0)
        fbox.pack_start(btn, False, False, 0)
        folder_frame.add(fbox)
        self.pack_start(folder_frame, False, False, 0)

        columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.pack_start(columns, True, True, 0)
        columns.pack_start(self._build_people(), True, True, 0)
        columns.pack_start(self._build_zoneblocks(), True, True, 0)

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
        box.pack_start(self._scrolled(self.people_view), True, True, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.person_entry = Gtk.Entry()
        self.person_entry.set_placeholder_text("e.g. Freja")
        self.person_entry.connect("activate", self._on_add_person)
        add = Gtk.Button(label="Add"); add.connect("clicked", self._on_add_person)
        rem = Gtk.Button(label="Remove"); rem.connect("clicked", self._on_remove_person)
        row.pack_start(self.person_entry, True, True, 0)
        row.pack_start(add, False, False, 0)
        row.pack_start(rem, False, False, 0)
        box.pack_start(row, False, False, 0)
        return frame

    def _on_add_person(self, *_a) -> None:
        ws = self.window.workspace
        name = self.person_entry.get_text().strip()
        if ws and name:
            ws.add_person(name)
            self.person_entry.set_text("")
            self.window.refresh_all()

    def _on_remove_person(self, *_a) -> None:
        ws = self.window.workspace
        model, it = self.people_view.get_selection().get_selected()
        if ws and it:
            ws.remove_person(model[it][1])
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
        box.pack_start(self._scrolled(self.zb_view), True, True, 0)

        # add form
        form = Gtk.Grid(row_spacing=4, column_spacing=6)
        form.attach(Gtk.Label(label="Name", xalign=0.0), 0, 0, 1, 1)
        self.zb_name = Gtk.Entry()
        self.zb_name.set_placeholder_text("e.g. Bank Statements")
        form.attach(self.zb_name, 1, 0, 1, 1)

        form.attach(Gtk.Label(label="Scope", xalign=0.0), 0, 1, 1, 1)
        self.zb_scope = Gtk.ComboBoxText()
        for sid, label in _SCOPES:
            self.zb_scope.append(sid, label)
        self.zb_scope.set_active_id(SCOPE_BOTH)
        form.attach(self.zb_scope, 1, 1, 1, 1)

        form.attach(Gtk.Label(label="Icon", xalign=0.0), 0, 2, 1, 1)
        self.zb_icon = Gtk.ComboBoxText()
        for name, label in ZONEBLOCK_ICONS:
            self.zb_icon.append(name, label)
        self.zb_icon.set_active_id(ZONEBLOCK_ICONS[0][0])
        form.attach(self.zb_icon, 1, 2, 1, 1)
        box.pack_start(form, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        add = Gtk.Button(label="Add zoneblock")
        add.connect("clicked", self._on_add_zoneblock)
        rem = Gtk.Button(label="Remove")
        rem.connect("clicked", self._on_remove_zoneblock)
        row.pack_start(add, True, True, 0)
        row.pack_start(rem, False, False, 0)
        box.pack_start(row, False, False, 0)
        return frame

    def _on_add_zoneblock(self, *_a) -> None:
        ws = self.window.workspace
        name = self.zb_name.get_text().strip()
        if ws and name:
            ws.add_zoneblock(name, self.zb_scope.get_active_id(),
                             self.zb_icon.get_active_id())
            self.zb_name.set_text("")
            self.window.refresh_all()

    def _on_remove_zoneblock(self, *_a) -> None:
        ws = self.window.workspace
        model, it = self.zb_view.get_selection().get_selected()
        if ws and it:
            ws.remove_zoneblock(model[it][3])
            self.window.refresh_all()

    # ---- helpers -----------------------------------------------------
    @staticmethod
    def _scrolled(child) -> Gtk.ScrolledWindow:
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_min_content_height(160)
        sw.add(child)
        return sw

    def refresh(self) -> None:
        ws = self.window.workspace
        self.folder_label.set_text(ws.root if ws else "(no workspace open)")
        self.people_store.clear()
        self.zb_store.clear()
        if not ws:
            return
        for p in ws.people:
            self.people_store.append([p.name, p.id])
        scope_labels = dict(_SCOPES)
        for z in ws.zoneblocks:
            self.zb_store.append(
                [z.icon, z.name, scope_labels.get(z.scope, z.scope), z.id])
