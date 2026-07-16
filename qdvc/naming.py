"""id / slug / key helpers (pure)."""
from __future__ import annotations

import re
import uuid

_slug_re = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    s = _slug_re.sub("-", (text or "").strip().lower()).strip("-")
    return s or "item"


def new_id(prefix: str = "") -> str:
    token = uuid.uuid4().hex[:12]
    return f"{prefix}-{token}" if prefix else token


def zone_key(zoneblock_id: str, person_id: str | None) -> str:
    """Stable key identifying a derived zone."""
    return f"{zoneblock_id}::{person_id or 'shared'}"


def account_filename(account_id: str) -> str:
    return f"{account_id}.yml"
