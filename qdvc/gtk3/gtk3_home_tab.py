"""GTK3 Home tab — welcome view listing fresh and stale accounts."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from .. import APP_NAME  # noqa: E402


class HomeTab(Gtk.Box):
    def __init__(self, window) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.window = window
        self.set_border_width(14)

        heading = Gtk.Label(xalign=0.0)
        heading.set_markup(f"<big><b>Welcome to {APP_NAME}</b></big>")
        self.pack_start(heading, False, False, 0)

        self.intro = Gtk.Label(xalign=0.0)
        self.intro.set_line_wrap(True)
        self.pack_start(self.intro, False, False, 0)

        columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.pack_start(columns, True, True, 0)

        self.fresh_box = self._section("Records are fresh")
        self.stale_box = self._section("Records are stale")
        columns.pack_start(self.fresh_box["frame"], True, True, 0)
        columns.pack_start(self.stale_box["frame"], True, True, 0)

    def _section(self, title: str) -> dict:
        frame = Gtk.Frame(label=title)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        sw.add(listbox)
        frame.add(sw)
        return {"frame": frame, "listbox": listbox}

    def _clear(self, listbox: Gtk.ListBox) -> None:
        for child in listbox.get_children():
            listbox.remove(child)

    def _add_row(self, listbox: Gtk.ListBox, account) -> None:
        from html import escape
        ws = self.window.workspace
        zone = ws.zone_by_key(account.zone_key)
        subtitle = zone.label if zone else account.zone_key
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
                       border_width=6)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        name = Gtk.Label(xalign=0.0)
        name.set_markup(f"<b>{escape(account.name)}</b>")
        sub = Gtk.Label(label=subtitle, xalign=0.0)
        sub.get_style_context().add_class("dim-label")
        text.pack_start(name, False, False, 0)
        text.pack_start(sub, False, False, 0)
        hbox.pack_start(text, True, True, 0)
        btn = Gtk.Button(label="Open in Organiser")
        btn.connect("clicked",
                    lambda _w, aid=account.id: self.window.jump_to_account(aid))
        hbox.pack_start(btn, False, False, 0)
        row.add(hbox)
        listbox.add(row)

    def refresh(self) -> None:
        ws = self.window.workspace
        self._clear(self.fresh_box["listbox"])
        self._clear(self.stale_box["listbox"])
        if not ws:
            self.intro.set_text("Open or create a workspace from the File menu "
                                "to begin organising your household documents.")
            self.show_all()
            return
        self.intro.set_text("Periodic accounts are listed below by whether their "
                            "records are up to date.")
        fresh, stale = ws.fresh_and_stale()
        for a in fresh:
            self._add_row(self.fresh_box["listbox"], a)
        for a in stale:
            self._add_row(self.stale_box["listbox"], a)
        if not fresh:
            self._placeholder(self.fresh_box["listbox"], "No fresh accounts.")
        if not stale:
            self._placeholder(self.stale_box["listbox"], "No stale accounts.")
        self.show_all()

    def _placeholder(self, listbox: Gtk.ListBox, text: str) -> None:
        row = Gtk.ListBoxRow()
        lbl = Gtk.Label(label=text, xalign=0.0); lbl.set_border_width(8)
        lbl.get_style_context().add_class("dim-label")
        row.add(lbl)
        listbox.add(row)
