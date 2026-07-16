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


def _days_ago_phrase(value: str, today: _dt.date | None = None) -> str:
    """Human phrase for how long ago a date was: '15d ago', 'today', 'in 3d'."""
    d = parse_iso_date(value)
    if d is None:
        return ""
    today = today or _dt.date.today()
    delta = (today - d).days
    if delta > 0:
        return f"{delta}d ago"
    if delta == 0:
        return "today"
    return f"in {-delta}d"


def document_label(doc, today: _dt.date | None = None) -> str:
    """Single-line label for a document in Pane 3 — never the filename.

    Combines the catalogue's statement number and date issued:
      * neither set           -> "(not tagged yet)"
      * date only             -> "13 May 2026 (15d ago)"
      * statement only        -> "Statement 53"
      * both                  -> "No. 53 (13 May 2026, 15d ago)"
    A trailing "  (missing)" marker is appended when the file is absent.
    """
    stmt = (doc.statement_number or "").strip()
    date_iso = (doc.date_issued or "").strip()
    has_date = parse_iso_date(date_iso) is not None
    when = format_date(date_iso) if has_date else ""
    ago = _days_ago_phrase(date_iso, today) if has_date else ""

    if not stmt and not has_date:
        label = "(not tagged yet)"
    elif has_date and not stmt:
        label = f"{when} ({ago})" if ago else when
    elif stmt and not has_date:
        label = f"Statement {stmt}"
    else:  # both
        inner = f"{when}, {ago}" if ago else when
        label = f"No. {stmt} ({inner})"

    if getattr(doc, "present", True) is False:
        label += "  (missing)"
    return label


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
