"""GTK4 shared editor dialogs (person, zoneblock, account, date picker).

Each dialog is built fresh, edits a scratch copy, and invokes a callback with
the collected values on OK. Building on demand avoids live property-binding
crashes (e.g. SpinRow notify::value re-entrancy).
"""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ..models import SCOPE_BOTH, SCOPE_INDIVIDUAL, SCOPE_SHARED  # noqa: E402
from ..ui_prefs import ZONEBLOCK_ICONS, date_to_iso, iso_ymd  # noqa: E402

SCOPES = [(SCOPE_INDIVIDUAL, "Individual"), (SCOPE_SHARED, "Shared"),
          (SCOPE_BOTH, "Both")]


def _run(dialog: Adw.MessageDialog, on_ok, collect) -> None:
    def _resp(dlg, response):
        if response == "ok":
            on_ok(collect())
        dlg.destroy()
    dialog.connect("response", _resp)
    dialog.present()


def person_dialog(parent, name: str, on_ok) -> None:
    dlg = Adw.MessageDialog(transient_for=parent,
                            heading="Person" if name else "Add person")
    entry = Adw.EntryRow(title="Name")
    entry.set_text(name or "")
    group = Adw.PreferencesGroup()
    group.add(entry)
    dlg.set_extra_child(group)
    dlg.add_response("cancel", "Cancel")
    dlg.add_response("ok", "Save")
    dlg.set_default_response("ok")
    _run(dlg, on_ok, lambda: {"name": entry.get_text().strip()})


def zoneblock_dialog(parent, name: str, scope: str, icon: str, on_ok) -> None:
    dlg = Adw.MessageDialog(transient_for=parent,
                            heading="Zoneblock" if name else "Add zoneblock")
    group = Adw.PreferencesGroup()
    name_row = Adw.EntryRow(title="Name")
    name_row.set_text(name or "")
    scope_row = Adw.ComboRow(title="Scope")
    scope_row.set_model(Gtk.StringList.new([s[1] for s in SCOPES]))
    scope_row.set_selected(next((i for i, s in enumerate(SCOPES)
                                 if s[0] == scope), 2))
    icon_row = Adw.ComboRow(title="Icon")
    icon_row.set_model(Gtk.StringList.new([i[1] for i in ZONEBLOCK_ICONS]))
    icon_row.set_selected(next((i for i, ic in enumerate(ZONEBLOCK_ICONS)
                                if ic[0] == icon), 0))
    for r in (name_row, scope_row, icon_row):
        group.add(r)
    dlg.set_extra_child(group)
    dlg.add_response("cancel", "Cancel")
    dlg.add_response("ok", "Save")
    dlg.set_default_response("ok")
    _run(dlg, on_ok, lambda: {
        "name": name_row.get_text().strip(),
        "scope": SCOPES[scope_row.get_selected()][0],
        "icon": ZONEBLOCK_ICONS[icon_row.get_selected()][0],
    })


def account_settings_dialog(parent, account, on_ok) -> None:
    """Edit an account's periodic/cycle/notes settings in a popup."""
    dlg = Adw.MessageDialog(transient_for=parent,
                            heading=f"Settings — {account.name}")
    group = Adw.PreferencesGroup()
    periodic = Adw.SwitchRow(title="Periodic")
    periodic.set_active(account.periodic)
    cycle = Adw.SpinRow(title="Cycle (days)",
                        adjustment=Gtk.Adjustment(
                            lower=0, upper=3650, step_increment=1,
                            value=float(account.cycle_days)))
    notes = Adw.EntryRow(title="Notes")
    notes.set_text(account.notes or "")
    for r in (periodic, cycle, notes):
        group.add(r)
    dlg.set_extra_child(group)
    dlg.add_response("cancel", "Cancel")
    dlg.add_response("ok", "Save")
    dlg.set_default_response("ok")
    _run(dlg, on_ok, lambda: {
        "periodic": periodic.get_active(),
        "cycle_days": int(cycle.get_value()),
        "notes": notes.get_text(),
    })


def catalogue_date_dialog(parent, iso_value: str, on_ok) -> None:
    """Pick a date issued from a calendar; returns ISO 'YYYY-MM-DD' or ''."""
    dlg = Adw.MessageDialog(transient_for=parent, heading="Date issued")
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    calendar = Gtk.Calendar()
    ymd = iso_ymd(iso_value)
    if ymd:
        from gi.repository import GLib
        y, m, d = ymd
        calendar.select_day(GLib.DateTime.new_local(y, m, d, 0, 0, 0))
    box.append(calendar)
    clear_btn = Gtk.CheckButton(label="No date")
    clear_btn.set_active(not iso_value)
    box.append(clear_btn)
    dlg.set_extra_child(box)
    dlg.add_response("cancel", "Cancel")
    dlg.add_response("ok", "Set")
    dlg.set_default_response("ok")

    def collect():
        if clear_btn.get_active():
            return {"iso": ""}
        gd = calendar.get_date()
        # GLib.DateTime months are 1-based, matching date_to_iso
        return {"iso": date_to_iso(gd.get_year(), gd.get_month(),
                                   gd.get_day_of_month())}

    _run(dlg, on_ok, collect)
