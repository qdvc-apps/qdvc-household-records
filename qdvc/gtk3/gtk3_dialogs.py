"""GTK3 shared editor dialogs (person, zoneblock, account, date picker)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from ..models import SCOPE_BOTH, SCOPE_INDIVIDUAL, SCOPE_SHARED  # noqa: E402
from ..ui_prefs import ZONEBLOCK_ICONS, date_to_iso, iso_ymd  # noqa: E402

SCOPES = [(SCOPE_INDIVIDUAL, "Individual"), (SCOPE_SHARED, "Shared"),
          (SCOPE_BOTH, "Both")]


def _dialog(parent, title: str) -> Gtk.Dialog:
    dlg = Gtk.Dialog(title=title, transient_for=parent, modal=True)
    dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Save", Gtk.ResponseType.OK)
    dlg.set_default_response(Gtk.ResponseType.OK)
    return dlg


def person_dialog(parent, name: str) -> str | None:
    """Return the entered name, or None if cancelled."""
    dlg = _dialog(parent, "Person" if name else "Add person")
    box = dlg.get_content_area(); box.set_border_width(10); box.set_spacing(6)
    box.pack_start(Gtk.Label(label="Name", xalign=0.0), False, False, 0)
    entry = Gtk.Entry(); entry.set_text(name or ""); entry.set_activates_default(True)
    box.pack_start(entry, False, False, 0)
    dlg.show_all()
    result = entry.get_text().strip() if dlg.run() == Gtk.ResponseType.OK else None
    dlg.destroy()
    return result or None


def zoneblock_dialog(parent, name: str, scope: str, icon: str):
    """Return dict(name, scope, icon) or None if cancelled."""
    dlg = _dialog(parent, "Zoneblock" if name else "Add zoneblock")
    grid = Gtk.Grid(row_spacing=6, column_spacing=6, border_width=10)
    dlg.get_content_area().pack_start(grid, True, True, 0)
    grid.attach(Gtk.Label(label="Name", xalign=0.0), 0, 0, 1, 1)
    name_e = Gtk.Entry(); name_e.set_text(name or ""); name_e.set_activates_default(True)
    grid.attach(name_e, 1, 0, 1, 1)
    grid.attach(Gtk.Label(label="Scope", xalign=0.0), 0, 1, 1, 1)
    scope_c = Gtk.ComboBoxText()
    for sid, label in SCOPES:
        scope_c.append(sid, label)
    scope_c.set_active_id(scope if scope in dict(SCOPES) else SCOPE_BOTH)
    grid.attach(scope_c, 1, 1, 1, 1)
    grid.attach(Gtk.Label(label="Icon", xalign=0.0), 0, 2, 1, 1)
    icon_c = Gtk.ComboBoxText()
    for iname, label in ZONEBLOCK_ICONS:
        icon_c.append(iname, label)
    icon_c.set_active_id(icon if icon in dict(ZONEBLOCK_ICONS) else ZONEBLOCK_ICONS[0][0])
    grid.attach(icon_c, 1, 2, 1, 1)
    dlg.show_all()
    result = None
    if dlg.run() == Gtk.ResponseType.OK and name_e.get_text().strip():
        result = {"name": name_e.get_text().strip(),
                  "scope": scope_c.get_active_id(),
                  "icon": icon_c.get_active_id()}
    dlg.destroy()
    return result


def account_settings_dialog(parent, account):
    """Return dict(periodic, cycle_days, notes) or None if cancelled."""
    dlg = _dialog(parent, f"Settings — {account.name}")
    grid = Gtk.Grid(row_spacing=6, column_spacing=6, border_width=10)
    dlg.get_content_area().pack_start(grid, True, True, 0)
    periodic = Gtk.CheckButton(label="Periodic")
    periodic.set_active(account.periodic)
    grid.attach(periodic, 0, 0, 2, 1)
    grid.attach(Gtk.Label(label="Cycle (days)", xalign=0.0), 0, 1, 1, 1)
    cycle = Gtk.SpinButton.new_with_range(0, 3650, 1)
    cycle.set_value(account.cycle_days)
    grid.attach(cycle, 1, 1, 1, 1)
    grid.attach(Gtk.Label(label="Notes", xalign=0.0), 0, 2, 1, 1)
    notes = Gtk.Entry(); notes.set_text(account.notes or "")
    grid.attach(notes, 1, 2, 1, 1)
    dlg.show_all()
    result = None
    if dlg.run() == Gtk.ResponseType.OK:
        result = {"periodic": periodic.get_active(),
                  "cycle_days": int(cycle.get_value()),
                  "notes": notes.get_text()}
    dlg.destroy()
    return result


def date_dialog(parent, iso_value: str):
    """Pick a date from a calendar. Returns {'iso': 'YYYY-MM-DD' or ''} or None."""
    dlg = _dialog(parent, "Date issued")
    box = dlg.get_content_area(); box.set_border_width(10); box.set_spacing(6)
    calendar = Gtk.Calendar()
    ymd = iso_ymd(iso_value)
    if ymd:
        y, m, d = ymd
        calendar.select_month(m - 1, y)  # GtkCalendar months are 0-based
        calendar.select_day(d)
    box.pack_start(calendar, True, True, 0)
    clear = Gtk.CheckButton(label="No date")
    clear.set_active(not iso_value)
    box.pack_start(clear, False, False, 0)
    dlg.show_all()
    result = None
    if dlg.run() == Gtk.ResponseType.OK:
        if clear.get_active():
            result = {"iso": ""}
        else:
            y, m0, d = calendar.get_date()  # (year, month 0-based, day)
            result = {"iso": date_to_iso(y, m0 + 1, d)}
    dlg.destroy()
    return result
