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


# ---- Business records ------------------------------------------------

@dataclass
class Catalogue:
    """Per-file catalogue tags, stored in the account YAML keyed by filename."""
    statement_number: str = ""
    date_issued: str = ""      # ISO "YYYY-MM-DD" or ""
    notes: str = ""

    def is_empty(self) -> bool:
        return not (self.statement_number or self.date_issued or self.notes)


@dataclass
class Document:
    """A document belonging to an account.

    Documents are DISCOVERED by reading the account's folder (top-level PDFs);
    the app never creates or modifies them. Catalogue tags are stored in the
    account YAML keyed by `filename`.

    `filename` is the base name of the file within the account folder.
    `present` is True when the file currently exists in the folder; a catalogue
    entry whose file has disappeared is surfaced as a missing document
    (present=False) with its tags retained.
    """
    filename: str
    statement_number: str = ""
    date_issued: str = ""      # ISO "YYYY-MM-DD" or ""
    notes: str = ""
    present: bool = True


@dataclass
class Account:
    """An account within a zone (e.g. Bank of Atlantis).

    `folder` is a path RELATIVE to the data folder; the PDFs directly inside it
    are the account's documents. `catalogues` holds per-filename tags.
    """
    id: str
    zone_key: str
    name: str
    folder: str = ""           # relative to the data folder ("" => not set)
    periodic: bool = False
    cycle_days: int = 0
    notes: str = ""
    catalogues: dict[str, Catalogue] = field(default_factory=dict)
