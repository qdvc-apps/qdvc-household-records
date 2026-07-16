"""GTK4 Home view — welcome page listing fresh and stale accounts."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from .. import APP_NAME  # noqa: E402


class HomeView(Gtk.ScrolledWindow):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        clamp = Adw.Clamp()
        self.set_child(clamp)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(18); box.set_margin_bottom(18)
        box.set_margin_start(12); box.set_margin_end(12)
        clamp.set_child(box)

        title = Gtk.Label(xalign=0.0)
        title.set_markup(f"<big><b>Welcome to {APP_NAME}</b></big>")
        box.append(title)
        self.intro = Gtk.Label(xalign=0.0, wrap=True)
        box.append(self.intro)

        self.fresh_group = Adw.PreferencesGroup(title="Records are fresh")
        self.stale_group = Adw.PreferencesGroup(title="Records are stale")
        box.append(self.fresh_group)
        box.append(self.stale_group)
        self._fresh_rows: list = []
        self._stale_rows: list = []

    def _account_row(self, account) -> Adw.ActionRow:
        ws = self.window.workspace
        zone = ws.zone_by_key(account.zone_key)
        row = Adw.ActionRow(title=account.name,
                            subtitle=zone.label if zone else account.zone_key)
        btn = Gtk.Button(label="Open in Organiser")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked",
                    lambda _b, aid=account.id: self.window.jump_to_account(aid))
        row.add_suffix(btn)
        return row

    def refresh(self) -> None:
        ws = self.window.workspace
        for r in self._fresh_rows:
            self.fresh_group.remove(r)
        for r in self._stale_rows:
            self.stale_group.remove(r)
        self._fresh_rows.clear(); self._stale_rows.clear()
        if not ws:
            self.intro.set_text("Open or create a workspace to begin organising "
                                "your household documents.")
            return
        self.intro.set_text("Periodic accounts grouped by whether their records "
                            "are up to date.")
        fresh, stale = ws.fresh_and_stale()
        for a in fresh:
            row = self._account_row(a)
            self.fresh_group.add(row); self._fresh_rows.append(row)
        for a in stale:
            row = self._account_row(a)
            self.stale_group.add(row); self._stale_rows.append(row)
        if not fresh:
            row = Adw.ActionRow(title="No fresh accounts.")
            self.fresh_group.add(row); self._fresh_rows.append(row)
        if not stale:
            row = Adw.ActionRow(title="No stale accounts.")
            self.stale_group.add(row); self._stale_rows.append(row)
