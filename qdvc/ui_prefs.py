"""Toolkit-independent UI helpers shared by both front-ends."""
from __future__ import annotations

import datetime as _dt

# Shared shortcut table. Each entry: (action, accel, label, scope)
# scope: "both" | "gtk3" | "gtk4"
SHORTCUTS: list[tuple[str, str, str, str]] = [
    ("open_workspace", "<Primary>o", "Open workspace", "both"),
    ("new_workspace", "<Primary>n", "New workspace", "both"),
    ("quit", "<Primary>q", "Quit", "both"),
    ("preferences", "<Primary>comma", "Preferences", "both"),
    ("tab_home", "<Alt>1", "Home tab", "both"),
    ("tab_organiser", "<Alt>2", "Organiser tab", "both"),
    ("tab_setup", "<Alt>3", "Setup tab", "both"),
    ("rename", "F2", "Rename", "gtk3"),
]

# Icon names offered when creating a zoneblock (freedesktop themed names).
ZONEBLOCK_ICONS: list[tuple[str, str]] = [
    ("folder-symbolic", "Folder"),
    ("emblem-documents-symbolic", "Documents"),
    ("accessories-calculator-symbolic", "Bank / Money"),
    ("mail-send-receive-symbolic", "Payslips"),
    ("weather-clear-symbolic", "Electricity / Power"),
    ("go-home-symbolic", "Rent / Home"),
    ("system-file-manager-symbolic", "Insurance"),
    ("x-office-spreadsheet-symbolic", "Statements"),
]


def freshness_label(state: bool | None) -> str:
    if state is True:
        return "Records are fresh"
    if state is False:
        return "Records are stale"
    return "Not periodic"


def format_date(value: str) -> str:
    if not value:
        return "—"
    try:
        return _dt.date.fromisoformat(str(value)).strftime("%d %b %Y")
    except ValueError:
        return str(value)


def parse_iso_date(value: str) -> _dt.date | None:
    """Parse an ISO 'YYYY-MM-DD' string, or return None."""
    if not value:
        return None
    try:
        return _dt.date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def date_to_iso(year: int, month: int, day: int) -> str:
    """Build an ISO date string from calendar components (month is 1-based)."""
    return _dt.date(year, month, day).isoformat()


def iso_ymd(value: str) -> tuple[int, int, int] | None:
    """Return (year, month, day) from an ISO string, or None. Month is 1-based."""
    d = parse_iso_date(value)
    return (d.year, d.month, d.day) if d else None


def format_validation_report(problems: dict[str, list[str]]) -> str:
    titles = {
        "orphan_accounts": "Accounts whose zone no longer exists",
        "outside_folders": "Account folders outside the data folder",
        "missing_folders": "Account folders that no longer exist",
        "missing_files": "Catalogued files no longer in their folder",
    }
    lines: list[str] = []
    total = 0
    for key, title in titles.items():
        items = problems.get(key, [])
        total += len(items)
        if items:
            lines.append(f"{title} ({len(items)}):")
            lines.extend(f"  • {it}" for it in items)
            lines.append("")
    if total == 0:
        return "No problems found. The workspace is consistent."
    return "\n".join(lines).strip()
