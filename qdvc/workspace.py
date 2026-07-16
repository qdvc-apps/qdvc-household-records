"""Workspace model — files are the database.

Layout on disk (all YAML, human-readable, diffable):

    <workspace>/
        household.yml          people + zoneblocks (Setup-tab config)
        accounts/
            <account_id>.yml   one file per account (incl. its documents)

Every document path stored in an account is RELATIVE to the workspace
folder; absolute paths and paths outside the workspace are rejected.
"""
from __future__ import annotations

import datetime as _dt
import os
from typing import Iterable

import yaml

from . import naming
from .models import (
    SCOPE_BOTH,
    SCOPE_INDIVIDUAL,
    SCOPE_SHARED,
    VALID_SCOPES,
    Account,
    Document,
    Person,
    Zone,
    ZoneBlock,
)

HOUSEHOLD_FILE = "household.yml"
ACCOUNTS_DIR = "accounts"


def _atomic_write_yaml(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True)
    os.replace(tmp, path)


def _parse_date(value: str) -> _dt.date | None:
    if not value:
        return None
    try:
        return _dt.date.fromisoformat(str(value).strip())
    except ValueError:
        return None


class PathOutsideWorkspaceError(ValueError):
    """Raised when a file to import is not inside the workspace folder."""


class Workspace:
    """In-memory aggregate over the on-disk files."""

    def __init__(self, root: str) -> None:
        self.root = os.path.abspath(root)
        self.people: list[Person] = []
        self.zoneblocks: list[ZoneBlock] = []
        self.accounts: list[Account] = []

    # ---- lifecycle ---------------------------------------------------
    @classmethod
    def create(cls, root: str) -> "Workspace":
        ws = cls(root)
        os.makedirs(os.path.join(ws.root, ACCOUNTS_DIR), exist_ok=True)
        if not os.path.exists(ws._household_path()):
            ws.save_household()
        return ws

    @classmethod
    def load(cls, root: str) -> "Workspace":
        ws = cls(root)
        ws.reload()
        return ws

    def reload(self) -> None:
        self._load_household()
        self._load_accounts()

    # ---- paths -------------------------------------------------------
    def _household_path(self) -> str:
        return os.path.join(self.root, HOUSEHOLD_FILE)

    def _accounts_dir(self) -> str:
        return os.path.join(self.root, ACCOUNTS_DIR)

    def _account_path(self, account_id: str) -> str:
        return os.path.join(self._accounts_dir(), naming.account_filename(account_id))

    # ---- household (people + zoneblocks) -----------------------------
    def _load_household(self) -> None:
        self.people = []
        self.zoneblocks = []
        try:
            with open(self._household_path(), "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except FileNotFoundError:
            return
        for p in data.get("people", []) or []:
            self.people.append(Person(id=p["id"], name=p.get("name", "")))
        for z in data.get("zoneblocks", []) or []:
            scope = z.get("scope", SCOPE_BOTH)
            if scope not in VALID_SCOPES:
                scope = SCOPE_BOTH
            self.zoneblocks.append(
                ZoneBlock(
                    id=z["id"],
                    name=z.get("name", ""),
                    scope=scope,
                    icon=z.get("icon", "folder-symbolic"),
                )
            )

    def save_household(self) -> None:
        data = {
            "people": [{"id": p.id, "name": p.name} for p in self.people],
            "zoneblocks": [
                {"id": z.id, "name": z.name, "scope": z.scope, "icon": z.icon}
                for z in self.zoneblocks
            ],
        }
        _atomic_write_yaml(self._household_path(), data)

    # ---- accounts ----------------------------------------------------
    def _load_accounts(self) -> None:
        self.accounts = []
        adir = self._accounts_dir()
        if not os.path.isdir(adir):
            return
        for name in sorted(os.listdir(adir)):
            if not name.endswith(".yml"):
                continue
            try:
                with open(os.path.join(adir, name), "r", encoding="utf-8") as fh:
                    data = yaml.safe_load(fh) or {}
            except Exception:
                continue
            docs = [
                Document(
                    id=d.get("id") or naming.new_id("doc"),
                    path=d.get("path", ""),
                    statement_number=str(d.get("statement_number", "")),
                    date_issued=str(d.get("date_issued", "")),
                    notes=d.get("notes", ""),
                )
                for d in (data.get("documents") or [])
            ]
            self.accounts.append(
                Account(
                    id=data.get("id") or os.path.splitext(name)[0],
                    zone_key=data.get("zone_key", ""),
                    name=data.get("name", ""),
                    periodic=bool(data.get("periodic", False)),
                    cycle_days=int(data.get("cycle_days", 0) or 0),
                    notes=data.get("notes", ""),
                    documents=docs,
                )
            )

    def save_account(self, account: Account) -> None:
        data = {
            "id": account.id,
            "zone_key": account.zone_key,
            "name": account.name,
            "periodic": account.periodic,
            "cycle_days": account.cycle_days,
            "notes": account.notes,
            "documents": [
                {
                    "id": d.id,
                    "path": d.path,
                    "statement_number": d.statement_number,
                    "date_issued": d.date_issued,
                    "notes": d.notes,
                }
                for d in account.documents
            ],
        }
        _atomic_write_yaml(self._account_path(account.id), data)

    def delete_account(self, account: Account) -> None:
        self.accounts = [a for a in self.accounts if a.id != account.id]
        try:
            os.remove(self._account_path(account.id))
        except FileNotFoundError:
            pass

    # ---- mutation API ------------------------------------------------
    def add_person(self, name: str) -> Person:
        person = Person(id=naming.new_id("person"), name=name.strip())
        self.people.append(person)
        self.save_household()
        return person

    def remove_person(self, person_id: str) -> None:
        self.people = [p for p in self.people if p.id != person_id]
        self.save_household()

    def add_zoneblock(self, name: str, scope: str, icon: str) -> ZoneBlock:
        if scope not in VALID_SCOPES:
            scope = SCOPE_BOTH
        zb = ZoneBlock(id=naming.new_id("zb"), name=name.strip(),
                       scope=scope, icon=icon or "folder-symbolic")
        self.zoneblocks.append(zb)
        self.save_household()
        return zb

    def remove_zoneblock(self, zoneblock_id: str) -> None:
        self.zoneblocks = [z for z in self.zoneblocks if z.id != zoneblock_id]
        self.save_household()

    def add_account(self, zone_key: str, name: str, periodic: bool = False,
                    cycle_days: int = 0, notes: str = "") -> Account:
        acc = Account(
            id=naming.new_id("acc"),
            zone_key=zone_key,
            name=name.strip(),
            periodic=periodic,
            cycle_days=int(cycle_days or 0),
            notes=notes,
        )
        self.accounts.append(acc)
        self.save_account(acc)
        return acc

    def add_document(self, account: Account, absolute_path: str,
                     statement_number: str = "", date_issued: str = "",
                     notes: str = "") -> Document:
        """Add a filesystem file to an account as a relative-path document.

        Raises PathOutsideWorkspaceError if the file is not inside the
        workspace data folder.
        """
        rel = self.relativise(absolute_path)  # raises if outside
        doc = Document(
            id=naming.new_id("doc"),
            path=rel,
            statement_number=statement_number,
            date_issued=date_issued,
            notes=notes,
        )
        account.documents.append(doc)
        self.save_account(account)
        return doc

    def remove_document(self, account: Account, document_id: str) -> None:
        account.documents = [d for d in account.documents if d.id != document_id]
        self.save_account(account)

    # ---- relative-path enforcement -----------------------------------
    def relativise(self, absolute_path: str) -> str:
        """Return a path relative to the workspace root, or raise.

        Enforces the spec rule: a document MUST be inside the data folder.
        """
        abs_path = os.path.abspath(absolute_path)
        root = self.root
        try:
            common = os.path.commonpath([abs_path, root])
        except ValueError:
            raise PathOutsideWorkspaceError(abs_path)
        if common != root:
            raise PathOutsideWorkspaceError(abs_path)
        return os.path.relpath(abs_path, root)

    def absolutise(self, relative_path: str) -> str:
        return os.path.join(self.root, relative_path)

    def is_inside(self, absolute_path: str) -> bool:
        try:
            self.relativise(absolute_path)
            return True
        except PathOutsideWorkspaceError:
            return False

    # ---- derivation: zones -------------------------------------------
    def zones(self) -> list[Zone]:
        """Derive Pane-1 zones from people x zoneblocks."""
        out: list[Zone] = []
        for zb in self.zoneblocks:
            if zb.scope in (SCOPE_INDIVIDUAL, SCOPE_BOTH):
                for p in self.people:
                    out.append(Zone(
                        key=naming.zone_key(zb.id, p.id),
                        label=f"{p.name} {zb.name}",
                        icon=zb.icon,
                        zoneblock_id=zb.id,
                        person_id=p.id,
                    ))
            if zb.scope in (SCOPE_SHARED, SCOPE_BOTH):
                out.append(Zone(
                    key=naming.zone_key(zb.id, None),
                    label=f"Shared {zb.name}",
                    icon=zb.icon,
                    zoneblock_id=zb.id,
                    person_id=None,
                ))
        return out

    def accounts_for_zone(self, zone_key: str) -> list[Account]:
        return [a for a in self.accounts if a.zone_key == zone_key]

    def account_by_id(self, account_id: str) -> Account | None:
        for a in self.accounts:
            if a.id == account_id:
                return a
        return None

    def zone_by_key(self, zone_key: str) -> Zone | None:
        for z in self.zones():
            if z.key == zone_key:
                return z
        return None

    # ---- freshness ---------------------------------------------------
    def newest_issue_date(self, account: Account) -> _dt.date | None:
        dates = [d for d in (_parse_date(x.date_issued) for x in account.documents)
                 if d is not None]
        return max(dates) if dates else None

    def is_fresh(self, account: Account, today: _dt.date | None = None) -> bool | None:
        """Return True (fresh), False (stale), or None (not applicable).

        Fresh iff (today - cycle_days) is chronologically prior to the newest
        date_issued in the account. Non-periodic or unconfigured => None.
        """
        if not account.periodic or account.cycle_days <= 0:
            return None
        today = today or _dt.date.today()
        newest = self.newest_issue_date(account)
        if newest is None:
            return False
        threshold = today - _dt.timedelta(days=account.cycle_days)
        return threshold < newest

    def fresh_and_stale(self, today: _dt.date | None = None
                        ) -> tuple[list[Account], list[Account]]:
        fresh, stale = [], []
        for a in self.accounts:
            state = self.is_fresh(a, today)
            if state is True:
                fresh.append(a)
            elif state is False:
                stale.append(a)
        return fresh, stale

    # ---- validation --------------------------------------------------
    def validate(self) -> dict[str, list[str]]:
        problems: dict[str, list[str]] = {
            "orphan_accounts": [],
            "missing_files": [],
            "outside_files": [],
        }
        valid_keys = {z.key for z in self.zones()}
        for a in self.accounts:
            if a.zone_key not in valid_keys:
                problems["orphan_accounts"].append(f"{a.name} ({a.zone_key})")
            for d in a.documents:
                abs_path = self.absolutise(d.path)
                if os.path.isabs(d.path) or not self.is_inside(abs_path):
                    problems["outside_files"].append(f"{a.name}: {d.path}")
                elif not os.path.exists(abs_path):
                    problems["missing_files"].append(f"{a.name}: {d.path}")
        return problems
