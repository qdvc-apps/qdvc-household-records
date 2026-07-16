"""id / slug / key helpers (pure)."""
from __future__ import annotations

import re
import uuid

_slug_re = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Hyphenated slug (kept for compatibility)."""
    s = _slug_re.sub("-", (text or "").strip().lower()).strip("-")
    return s or "item"


def snake(text: str) -> str:
    """snake_case slug, e.g. 'Bank of Atlantis' -> 'bank_of_atlantis'."""
    s = _slug_re.sub("_", (text or "").strip().lower()).strip("_")
    return s or "item"


def _dedupe(base: str, taken: set[str]) -> str:
    """Return `base`, or base_2, base_3, … if already taken."""
    if base not in taken:
        return base
    n = 2
    while f"{base}_{n}" in taken:
        n += 1
    return f"{base}_{n}"


def person_id(name: str, taken: set[str] | None = None) -> str:
    """Slugified snake_case person id, e.g. 'Freja' -> 'freja'."""
    base = snake(name)
    return _dedupe(base, taken or set())


def zoneblock_id(name: str, taken: set[str] | None = None) -> str:
    """Slugified snake_case zoneblock id, e.g. 'Bank Statements' -> 'bank_statements'."""
    base = snake(name)
    return _dedupe(base, taken or set())


def account_id(person_id_or_shared: str, name: str,
               taken: set[str] | None = None) -> str:
    """Account id combining owner id + snake_case account name.

    e.g. person 'freja' + 'Bank of Atlantis' -> 'freja_bank_of_atlantis'.
    Shared accounts use the 'shared' prefix -> 'shared_powerplant_atlantica'.
    """
    base = f"{person_id_or_shared}_{snake(name)}"
    return _dedupe(base, taken or set())


def new_id(prefix: str = "") -> str:
    """Random id (still used for documents, which have no natural name key)."""
    token = uuid.uuid4().hex[:12]
    return f"{prefix}-{token}" if prefix else token


def zone_key(zoneblock_id: str, person_id: str | None) -> str:
    """Stable key identifying a derived zone."""
    return f"{zoneblock_id}::{person_id or 'shared'}"


def account_filename(account_id: str) -> str:
    return f"{account_id}.yml"
