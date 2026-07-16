"""Workspace model — files are the database.

Layout on disk (all YAML, human-readable, diffable):

    <workspace>/
        household.yml          people + zoneblocks (Setup-tab config)
        accounts/
            <account_id>.yml   one file per account

Each account points at a FOLDER inside the app-wide data folder (stored as a
path relative to the data folder). The PDFs directly inside that folder ARE the
account's documents — discovered read-only at load time. The app NEVER creates,
moves, or modifies anything in the data folder; it only reads it and records
tags in the workspace YAML, keyed by filename.
"""
from __future__ import annotations

import datetime as _dt
import os

import yaml

from . import naming
from .models import (
    SCOPE_BOTH,
    SCOPE_INDIVIDUAL,
    SCOPE_SHARED,
    VALID_SCOPES,
    Account,
    Catalogue,
    Document,
    Person,
    Zone,
    ZoneBlock,
)

HOUSEHOLD_FILE = "household.yml"
ACCOUNTS_DIR = "accounts"
PDF_EXTS = (".pdf",)


def _atomic_write_yaml(path: str, data) -> None:
    """Write YAML atomically. Only ever used for WORKSPACE files."""
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


class PathOutsideDataFolderError(ValueError):
    """Raised when a chosen folder is not inside the app-wide data folder."""


# Backwards-compatible alias.
PathOutsideWorkspaceError = PathOutsideDataFolderError


class FolderScan:
    """Result of reading an account's folder (read-only)."""

    def __init__(self, documents: list[Document], has_subfolders: bool,
                 exists: bool) -> None:
        self.documents = documents
        self.has_subfolders = has_subfolders
        self.exists = exists


class Workspace:
    """In-memory aggregate over the on-disk files.

    `root` is this workspace's own folder (its YAML lives here).
    `data_folder` is the app-wide, read-only store of PDFs shared across ALL
    workspaces; each account's folder is stored relative to it.
    """

    def __init__(self, root: str, data_folder: str | None = None) -> None:
        self.root = os.path.abspath(root)
        self.data_folder = os.path.abspath(data_folder) if data_folder else self.root
        self.people: list[Person] = []
        self.zoneblocks: list[ZoneBlock] = []
        self.accounts: list[Account] = []

    # ---- lifecycle ---------------------------------------------------
    @classmethod
    def create(cls, root: str, data_folder: str | None = None) -> "Workspace":
        ws = cls(root, data_folder)
        # Only the WORKSPACE is created here; the data folder is never written.
        os.makedirs(os.path.join(ws.root, ACCOUNTS_DIR), exist_ok=True)
        if not os.path.exists(ws._household_path()):
            ws.save_household()
        return ws

    @classmethod
    def load(cls, root: str, data_folder: str | None = None) -> "Workspace":
        ws = cls(root, data_folder)
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
            catalogues: dict[str, Catalogue] = {}
            for entry in (data.get("catalogues") or []):
                fname = entry.get("filename")
                if not fname:
                    continue
                catalogues[fname] = Catalogue(
                    statement_number=str(entry.get("statement_number", "")),
                    date_issued=str(entry.get("date_issued", "")),
                    notes=entry.get("notes", ""),
                )
            self.accounts.append(
                Account(
                    id=data.get("id") or os.path.splitext(name)[0],
                    zone_key=data.get("zone_key", ""),
                    name=data.get("name", ""),
                    folder=data.get("folder", "") or "",
                    periodic=bool(data.get("periodic", False)),
                    cycle_days=int(data.get("cycle_days", 0) or 0),
                    notes=data.get("notes", ""),
                    catalogues=catalogues,
                )
            )

    def save_account(self, account: Account) -> None:
        data = {
            "id": account.id,
            "zone_key": account.zone_key,
            "name": account.name,
            "folder": account.folder,
            "periodic": account.periodic,
            "cycle_days": account.cycle_days,
            "notes": account.notes,
            "catalogues": [
                {
                    "filename": fname,
                    "statement_number": cat.statement_number,
                    "date_issued": cat.date_issued,
                    "notes": cat.notes,
                }
                for fname, cat in sorted(account.catalogues.items())
                if not cat.is_empty()
            ],
        }
        _atomic_write_yaml(self._account_path(account.id), data)

    def delete_account(self, account: Account) -> None:
        """Remove the account's WORKSPACE YAML. The data folder is untouched."""
        self.accounts = [a for a in self.accounts if a.id != account.id]
        try:
            os.remove(self._account_path(account.id))
        except FileNotFoundError:
            pass

    # ---- mutation API (people / zoneblocks) --------------------------
    def add_person(self, name: str) -> Person:
        taken = {p.id for p in self.people}
        person = Person(id=naming.person_id(name, taken), name=name.strip())
        self.people.append(person)
        self.save_household()
        return person

    def remove_person(self, person_id: str) -> None:
        self.people = [p for p in self.people if p.id != person_id]
        self.save_household()

    def update_person(self, person_id: str, name: str) -> None:
        for p in self.people:
            if p.id == person_id:
                p.name = name.strip()
                break
        self.save_household()

    def add_zoneblock(self, name: str, scope: str, icon: str) -> ZoneBlock:
        if scope not in VALID_SCOPES:
            scope = SCOPE_BOTH
        taken = {z.id for z in self.zoneblocks}
        zb = ZoneBlock(id=naming.zoneblock_id(name, taken), name=name.strip(),
                       scope=scope, icon=icon or "folder-symbolic")
        self.zoneblocks.append(zb)
        self.save_household()
        return zb

    def remove_zoneblock(self, zoneblock_id: str) -> None:
        self.zoneblocks = [z for z in self.zoneblocks if z.id != zoneblock_id]
        self.save_household()

    def update_zoneblock(self, zoneblock_id: str, name: str, scope: str,
                         icon: str) -> None:
        if scope not in VALID_SCOPES:
            scope = SCOPE_BOTH
        for z in self.zoneblocks:
            if z.id == zoneblock_id:
                z.name = name.strip()
                z.scope = scope
                z.icon = icon or "folder-symbolic"
                break
        self.save_household()

    # ---- mutation API (accounts) -------------------------------------
    @staticmethod
    def _owner_of_zone_key(zone_key: str) -> str:
        """Extract the owner segment ('freja' or 'shared') from a zone key."""
        return zone_key.split("::", 1)[-1] if "::" in zone_key else "shared"

    def add_account(self, zone_key: str, name: str, periodic: bool = False,
                    cycle_days: int = 0, notes: str = "") -> Account:
        owner = self._owner_of_zone_key(zone_key)
        taken = {a.id for a in self.accounts}
        acc = Account(
            id=naming.account_id(owner, name, taken),
            zone_key=zone_key,
            name=name.strip(),
            periodic=periodic,
            cycle_days=int(cycle_days or 0),
            notes=notes,
        )
        self.accounts.append(acc)
        self.save_account(acc)
        return acc

    def update_account_settings(self, account: Account, periodic: bool,
                                cycle_days: int, notes: str) -> None:
        account.periodic = bool(periodic)
        account.cycle_days = int(cycle_days or 0)
        account.notes = notes
        self.save_account(account)

    def set_account_folder(self, account: Account, absolute_path: str) -> None:
        """Point an account at a folder inside the data folder (read-only).

        Stores the folder relative to the data folder. Raises
        PathOutsideDataFolderError if the folder is not inside it. Nothing on
        disk is created or modified.
        """
        account.folder = self.relativise(absolute_path)  # raises if outside
        self.save_account(account)

    def clear_account_folder(self, account: Account) -> None:
        account.folder = ""
        self.save_account(account)

    # ---- catalogue tags ----------------------------------------------
    def set_catalogue(self, account: Account, filename: str,
                      statement_number: str, date_issued: str,
                      notes: str) -> None:
        """Set (or clear) the catalogue tags for a filename within an account."""
        cat = Catalogue(statement_number=statement_number,
                        date_issued=date_issued.strip(), notes=notes)
        if cat.is_empty():
            account.catalogues.pop(filename, None)
        else:
            account.catalogues[filename] = cat
        self.save_account(account)

    # ---- read-only folder discovery ----------------------------------
    def scan_account(self, account: Account) -> FolderScan:
        """Read an account's folder and return its documents (read-only).

        Documents are the top-level PDFs in the folder, merged with any stored
        catalogue tags. Catalogue entries whose file is absent are appended as
        missing documents (present=False) so their tags are still visible.
        """
        docs: list[Document] = []
        has_subfolders = False
        exists = False
        seen: set[str] = set()

        if account.folder:
            abs_folder = self.absolutise(account.folder)
            if os.path.isdir(abs_folder):
                exists = True
                try:
                    entries = sorted(os.listdir(abs_folder))
                except OSError:
                    entries = []
                for name in entries:
                    full = os.path.join(abs_folder, name)
                    if os.path.isdir(full):
                        has_subfolders = True
                        continue
                    if os.path.splitext(name)[1].lower() in PDF_EXTS:
                        cat = account.catalogues.get(name, Catalogue())
                        docs.append(Document(
                            filename=name,
                            statement_number=cat.statement_number,
                            date_issued=cat.date_issued,
                            notes=cat.notes,
                            present=True,
                        ))
                        seen.add(name)

        # catalogued-but-missing files
        for fname, cat in sorted(account.catalogues.items()):
            if fname not in seen:
                docs.append(Document(
                    filename=fname,
                    statement_number=cat.statement_number,
                    date_issued=cat.date_issued,
                    notes=cat.notes,
                    present=False,
                ))
        return FolderScan(docs, has_subfolders, exists)

    def document_path(self, account: Account, filename: str) -> str:
        """Absolute path of a document file (for opening)."""
        return self.absolutise(os.path.join(account.folder, filename))

    # ---- relative-path enforcement (against the DATA FOLDER) ---------
    def relativise(self, absolute_path: str) -> str:
        abs_path = os.path.abspath(absolute_path)
        base = self.data_folder
        try:
            common = os.path.commonpath([abs_path, base])
        except ValueError:
            raise PathOutsideDataFolderError(abs_path)
        if common != base:
            raise PathOutsideDataFolderError(abs_path)
        return os.path.relpath(abs_path, base)

    def absolutise(self, relative_path: str) -> str:
        return os.path.join(self.data_folder, relative_path)

    def is_inside(self, absolute_path: str) -> bool:
        try:
            self.relativise(absolute_path)
            return True
        except PathOutsideDataFolderError:
            return False

    # ---- derivation: zones -------------------------------------------
    def zones(self) -> list[Zone]:
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
        """Newest date_issued among the account's PRESENT documents."""
        scan = self.scan_account(account)
        dates = [d for d in (_parse_date(x.date_issued) for x in scan.documents)
                 if d is not None]
        return max(dates) if dates else None

    def is_fresh(self, account: Account, today: _dt.date | None = None) -> bool | None:
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
            "missing_folders": [],
            "outside_folders": [],
            "missing_files": [],
        }
        valid_keys = {z.key for z in self.zones()}
        for a in self.accounts:
            if a.zone_key not in valid_keys:
                problems["orphan_accounts"].append(f"{a.name} ({a.zone_key})")
            if a.folder:
                abs_folder = self.absolutise(a.folder)
                if os.path.isabs(a.folder) or not self.is_inside(abs_folder):
                    problems["outside_folders"].append(f"{a.name}: {a.folder}")
                elif not os.path.isdir(abs_folder):
                    problems["missing_folders"].append(f"{a.name}: {a.folder}")
            scan = self.scan_account(a)
            for d in scan.documents:
                if not d.present:
                    problems["missing_files"].append(f"{a.name}: {d.filename}")
        return problems
