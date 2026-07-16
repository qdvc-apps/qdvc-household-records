"""Display-free model tests (no GTK needed)."""
import datetime
import os
import tempfile

from qdvc.models import SCOPE_BOTH, SCOPE_INDIVIDUAL, SCOPE_SHARED
from qdvc.workspace import PathOutsideDataFolderError, Workspace


def build():
    d = tempfile.mkdtemp()
    data = tempfile.mkdtemp()  # separate app-wide data folder
    ws = Workspace.create(d, data)
    ws.add_person("Freja")
    ws.add_person("Ludvig")
    ws.add_zoneblock("Bank Statements", SCOPE_BOTH, "accessories-calculator-symbolic")
    ws.add_zoneblock("Payslips", SCOPE_INDIVIDUAL, "mail-send-receive-symbolic")
    ws.add_zoneblock("Electricity", SCOPE_SHARED, "weather-clear-symbolic")
    return d, ws


def _make_pdf(folder, name, text="x"):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), "w") as fh:
        fh.write(text)


def test_slug_ids():
    _d, ws = build()
    assert {p.id for p in ws.people} == {"freja", "ludvig"}
    ids = {z.id for z in ws.zoneblocks}
    assert "bank_statements" in ids and "payslips" in ids
    p = ws.add_person("Freja")
    assert p.id == "freja_2"


def test_account_id_from_owner_and_name():
    _d, ws = build()
    zk_freja = next(z.key for z in ws.zones() if z.label == "Freja Bank Statements")
    acc = ws.add_account(zk_freja, "Bank of Atlantis")
    assert acc.id == "freja_bank_of_atlantis"
    zk_shared = next(z.key for z in ws.zones() if z.label == "Shared Electricity")
    sacc = ws.add_account(zk_shared, "Powerplant Atlantica")
    assert sacc.id == "shared_powerplant_atlantica"
    assert os.path.exists(os.path.join(ws.root, "accounts",
                                       "freja_bank_of_atlantis.yml"))


def test_folder_discovery_toplevel_and_subfolders():
    _d, ws = build()
    zk = next(z.key for z in ws.zones() if z.label == "Shared Electricity")
    acc = ws.add_account(zk, "Powerplant Atlantica")
    folder = os.path.join(ws.data_folder, "electricity")
    _make_pdf(folder, "jan.pdf")
    _make_pdf(folder, "feb.pdf")
    _make_pdf(folder, "notes.txt")          # ignored (not a PDF)
    os.makedirs(os.path.join(folder, "archive"), exist_ok=True)  # subfolder
    _make_pdf(os.path.join(folder, "archive"), "old.pdf")        # not discovered
    ws.set_account_folder(acc, folder)

    scan = ws.scan_account(acc)
    names = sorted(d.filename for d in scan.documents)
    assert names == ["feb.pdf", "jan.pdf"]   # top-level PDFs only
    assert scan.has_subfolders is True
    assert scan.exists is True


def test_folder_must_be_inside_data_folder():
    _d, ws = build()
    zk = next(z.key for z in ws.zones() if z.label == "Freja Payslips")
    acc = ws.add_account(zk, "Employer")
    outside = tempfile.mkdtemp()  # not inside the data folder
    try:
        ws.set_account_folder(acc, outside)
        assert False, "expected PathOutsideDataFolderError"
    except PathOutsideDataFolderError:
        pass


def test_catalogue_by_filename_and_missing():
    _d, ws = build()
    zk = next(z.key for z in ws.zones() if z.label == "Freja Bank Statements")
    acc = ws.add_account(zk, "Bank of Atlantis")
    folder = os.path.join(ws.data_folder, "freja_bank")
    _make_pdf(folder, "2026-01.pdf")
    ws.set_account_folder(acc, folder)
    ws.set_catalogue(acc, "2026-01.pdf", "001", "2026-01-31", "first")
    # reload from disk: tag persists, keyed by filename
    ws2 = Workspace.load(_d, ws.data_folder)
    acc2 = ws2.account_by_id(acc.id)
    scan = ws2.scan_account(acc2)
    doc = next(d for d in scan.documents if d.filename == "2026-01.pdf")
    assert doc.statement_number == "001" and doc.present is True
    # remove the file -> catalogued-but-missing, tags retained, present False
    os.remove(os.path.join(folder, "2026-01.pdf"))
    scan2 = ws2.scan_account(acc2)
    missing = next(d for d in scan2.documents if d.filename == "2026-01.pdf")
    assert missing.present is False and missing.date_issued == "2026-01-31"


def test_freshness_uses_discovered_docs():
    _d, ws = build()
    zk = next(z.key for z in ws.zones() if z.label == "Freja Bank Statements")
    acc = ws.add_account(zk, "Bank of Atlantis", periodic=True, cycle_days=30)
    folder = os.path.join(ws.data_folder, "freja_bank2")
    _make_pdf(folder, "s.pdf")
    ws.set_account_folder(acc, folder)
    assert ws.is_fresh(acc) is False  # no dated docs yet
    recent = (datetime.date.today() - datetime.timedelta(days=5)).isoformat()
    ws.set_catalogue(acc, "s.pdf", "", recent, "")
    assert ws.is_fresh(acc) is True
    old = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
    ws.set_catalogue(acc, "s.pdf", "", old, "")
    assert ws.is_fresh(acc) is False
    acc.periodic = False
    assert ws.is_fresh(acc) is None


def test_update_methods():
    _d, ws = build()
    ws.update_person("freja", "Freja Updated")
    assert next(p.name for p in ws.people if p.id == "freja") == "Freja Updated"
    ws.update_zoneblock("payslips", "Wages", SCOPE_SHARED, "go-home-symbolic")
    zb = next(z for z in ws.zoneblocks if z.id == "payslips")
    assert zb.name == "Wages" and zb.scope == SCOPE_SHARED
    zk = next(z.key for z in ws.zones() if z.person_id is None
              and z.zoneblock_id == "bank_statements")
    acc = ws.add_account(zk, "Shared Bank")
    ws.update_account_settings(acc, True, 45, "quarterly-ish")
    reloaded = Workspace.load(_d, ws.data_folder).account_by_id(acc.id)
    assert reloaded.periodic and reloaded.cycle_days == 45
    assert reloaded.notes == "quarterly-ish"


def test_app_never_writes_data_folder():
    d = tempfile.mkdtemp()
    data = os.path.join(tempfile.mkdtemp(), "readonly-data")  # does NOT exist
    ws = Workspace.create(d, data)          # must not create the data folder
    assert not os.path.exists(data)
    zk = ws.zones()[0].key if ws.zones() else None
    # set up minimal config so a zone exists
    ws.add_person("Freja")
    ws.add_zoneblock("Bank Statements", SCOPE_BOTH, "folder-symbolic")
    zk = next(z.key for z in ws.zones() if z.person_id is None)
    acc = ws.add_account(zk, "Bank")
    # pointing at a (missing) subpath must not create anything
    scan = ws.scan_account(acc)
    assert scan.documents == [] and not os.path.exists(data)


def test_reload_roundtrip():
    d, ws = build()
    data = ws.data_folder
    zk = ws.zones()[0].key
    ws.add_account(zk, "Test Account")
    ws2 = Workspace.load(d, data)
    assert len(ws2.people) == 2
    assert len(ws2.zoneblocks) == 3
    assert len(ws2.accounts) == 1
    assert ws2.data_folder == os.path.abspath(data)


def test_zone_derivation():
    _d, ws = build()
    labels = {z.label for z in ws.zones()}
    assert "Freja Bank Statements" in labels
    assert "Shared Bank Statements" in labels
    assert "Ludvig Payslips" in labels
    assert "Shared Payslips" not in labels
    assert "Shared Electricity" in labels
    assert "Freja Electricity" not in labels


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    print("ALL MODEL TESTS PASSED")
