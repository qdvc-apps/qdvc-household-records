"""GTK4 Setup view — people and zoneblocks as editable lists.

Each item shows an Edit and Delete button; each group ends with an "Add" row
that opens a popup dialog (reused for edit). The data folder lives in
Preferences, not here.
"""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from .gtk4_dialogs import SCOPES, person_dialog, zoneblock_dialog  # noqa: E402


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

        self.people_group = Adw.PreferencesGroup(
            title="People in the household")
        box.append(self.people_group)

        self.zb_group = Adw.PreferencesGroup(title="Zoneblocks")
        box.append(self.zb_group)

        self._people_rows: list = []
        self._zb_rows: list = []

    def _ws(self):
        return self.window.workspace

    # ---- row construction -------------------------------------------
    @staticmethod
    def _icon_button(icon: str, tooltip: str, cb) -> Gtk.Button:
        btn = Gtk.Button.new_from_icon_name(icon)
        btn.set_valign(Gtk.Align.CENTER)
        btn.set_tooltip_text(tooltip)
        btn.add_css_class("flat")
        btn.connect("clicked", cb)
        return btn

    def _item_row(self, title: str, subtitle: str, icon,
                  on_edit, on_delete) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title)
        if subtitle:
            row.set_subtitle(subtitle)
        if icon:
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
        row.add_suffix(self._icon_button("document-edit-symbolic", "Edit", on_edit))
        row.add_suffix(self._icon_button("user-trash-symbolic", "Delete", on_delete))
        return row

    def _add_row(self, label: str, cb) -> Adw.ActionRow:
        row = Adw.ActionRow(title=label)
        row.set_activatable(True)
        row.add_prefix(Gtk.Image.new_from_icon_name("list-add-symbolic"))
        row.connect("activated", lambda *_: cb())
        return row

    # ---- people ------------------------------------------------------
    def _on_add_person(self) -> None:
        if not self._ws():
            return
        person_dialog(self.window, "", lambda vals: self._create_person(vals))

    def _create_person(self, vals) -> None:
        if vals["name"]:
            self._ws().add_person(vals["name"])
            self.window.refresh_all()

    def _on_edit_person(self, person) -> None:
        person_dialog(self.window, person.name,
                      lambda vals: self._save_person(person.id, vals))

    def _save_person(self, pid, vals) -> None:
        if vals["name"]:
            self._ws().update_person(pid, vals["name"])
            self.window.refresh_all()

    def _on_delete_person(self, person) -> None:
        self._ws().remove_person(person.id)
        self.window.refresh_all()

    # ---- zoneblocks --------------------------------------------------
    def _on_add_zoneblock(self) -> None:
        if not self._ws():
            return
        zoneblock_dialog(self.window, "", "both", "",
                         lambda vals: self._create_zoneblock(vals))

    def _create_zoneblock(self, vals) -> None:
        if vals["name"]:
            self._ws().add_zoneblock(vals["name"], vals["scope"], vals["icon"])
            self.window.refresh_all()

    def _on_edit_zoneblock(self, zb) -> None:
        zoneblock_dialog(self.window, zb.name, zb.scope, zb.icon,
                         lambda vals: self._save_zoneblock(zb.id, vals))

    def _save_zoneblock(self, zid, vals) -> None:
        if vals["name"]:
            self._ws().update_zoneblock(zid, vals["name"], vals["scope"],
                                        vals["icon"])
            self.window.refresh_all()

    def _on_delete_zoneblock(self, zb) -> None:
        self._ws().remove_zoneblock(zb.id)
        self.window.refresh_all()

    # ---- refresh -----------------------------------------------------
    def refresh(self) -> None:
        for r in self._people_rows:
            self.people_group.remove(r)
        for r in self._zb_rows:
            self.zb_group.remove(r)
        self._people_rows.clear()
        self._zb_rows.clear()

        ws = self._ws()
        if not ws:
            placeholder = Adw.ActionRow(title="Open a workspace to configure it.")
            self.people_group.add(placeholder)
            self._people_rows.append(placeholder)
            return

        for p in ws.people:
            row = self._item_row(
                p.name, "", None,
                lambda _b, person=p: self._on_edit_person(person),
                lambda _b, person=p: self._on_delete_person(person))
            self.people_group.add(row)
            self._people_rows.append(row)
        add_p = self._add_row("Add person…", self._on_add_person)
        self.people_group.add(add_p)
        self._people_rows.append(add_p)

        scope_labels = dict(SCOPES)
        for z in ws.zoneblocks:
            row = self._item_row(
                z.name, scope_labels.get(z.scope, z.scope), z.icon,
                lambda _b, zb=z: self._on_edit_zoneblock(zb),
                lambda _b, zb=z: self._on_delete_zoneblock(zb))
            self.zb_group.add(row)
            self._zb_rows.append(row)
        add_z = self._add_row("Add zoneblock…", self._on_add_zoneblock)
        self.zb_group.add(add_z)
        self._zb_rows.append(add_z)
