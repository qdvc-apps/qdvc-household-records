"""Domain records (pure dataclasses, no GTK)."""
from __future__ import annotations

from dataclasses import dataclass, field


# ---- Setup-tab configuration -----------------------------------------

@dataclass
class Person:
    """A member of the household."""
    id: str
    name: str


# A zoneblock's applicability.
SCOPE_INDIVIDUAL = "individual"
SCOPE_SHARED = "shared"
SCOPE_BOTH = "both"
VALID_SCOPES = (SCOPE_INDIVIDUAL, SCOPE_SHARED, SCOPE_BOTH)


@dataclass
class ZoneBlock:
    """A category of document (e.g. Bank Statements) plus how it applies.

    scope:
        individual -> one zone per person
        shared     -> a single "Shared <name>" zone
        both       -> per-person zones AND a shared zone
    icon: a freedesktop themed icon name shown in Pane 1.
    """
    id: str
    name: str
    scope: str = SCOPE_BOTH
    icon: str = "folder-symbolic"


# ---- Derived (not stored directly) -----------------------------------

@dataclass
class Zone:
    """A derived row in Pane 1: (zoneblock x person) or (zoneblock x shared).

    `key` is the stable identifier used to attach accounts on disk.
    `person_id` is None for shared zones.
    """
    key: str
    label: str
    icon: str
    zoneblock_id: str
    person_id: str | None  # None => shared


# ---- Business records (stored in the workspace) ----------------------

@dataclass
class Document:
    """A catalogued file inside an account.

    `path` is ALWAYS relative to the workspace data folder.
    """
    id: str
    path: str
    statement_number: str = ""
    date_issued: str = ""      # ISO "YYYY-MM-DD" or ""
    notes: str = ""


@dataclass
class Account:
    """An account within a zone (e.g. Bank of Atlantis)."""
    id: str
    zone_key: str
    name: str
    periodic: bool = False
    cycle_days: int = 0
    notes: str = ""
    documents: list[Document] = field(default_factory=list)
