"""Display-free model tests (no GTK needed)."""
import datetime
import os
import tempfile

from qdvc.models import SCOPE_BOTH, SCOPE_INDIVIDUAL, SCOPE_SHARED
from qdvc.workspace import PathOutsideWorkspaceError, Workspace


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


def test_slug_ids():
    _d, ws = build()
    assert {p.id for p in ws.people} == {"freja", "ludvig"}
    ids = {z.id for z in ws.zoneblocks}
    assert "bank_statements" in ids and "payslips" in ids
    # duplicate person name gets deduped
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
    # the YAML file is named after the id
    assert os.path.exists(os.path.join(ws.root, "accounts",
                                       "freja_bank_of_atlantis.yml"))


def test_zone_derivation():
    _d, ws = build()
    labels = {z.label for z in ws.zones()}
    assert "Freja Bank Statements" in labels
    assert "Shared Bank Statements" in labels
    assert "Ludvig Payslips" in labels
    assert "Shared Payslips" not in labels
    assert "Shared Electricity" in labels
    assert "Freja Electricity" not in labels


def test_freshness():
    _d, ws = build()
    zk = next(z.key for z in ws.zones() if z.label == "Freja Bank Statements")
    acc = ws.add_account(zk, "Bank of Atlantis", periodic=True, cycle_days=30)
    assert ws.is_fresh(acc) is False  # no documents
    fp = os.path.join(ws.data_folder, "s.pdf")  # inside the DATA folder
    open(fp, "w").write("x")
    recent = (datetime.date.today() - datetime.timedelta(days=5)).isoformat()
    ws.add_document(acc, fp, date_issued=recent)
    assert ws.is_fresh(acc) is True
    acc.documents[0].date_issued = (
        datetime.date.today() - datetime.timedelta(days=90)).isoformat()
    ws.save_account(acc)
    assert ws.is_fresh(acc) is False
    acc.periodic = False
    assert ws.is_fresh(acc) is None


def test_relative_path_enforcement():
    _d, ws = build()
    zk = next(z.key for z in ws.zones() if z.label == "Shared Electricity")
    acc = ws.add_account(zk, "Powerplant Atlantica")
    # a file inside the data folder is accepted and stored relative to it
    fp = os.path.join(ws.data_folder, "bill.pdf")
    open(fp, "w").write("x")
    doc = ws.add_document(acc, fp)
    assert doc.path == "bill.pdf"
    assert not os.path.isabs(doc.path)
    # a file inside the WORKSPACE (but not the data folder) is rejected
    inside_ws = os.path.join(ws.root, "stray.pdf")
    open(inside_ws, "w").write("y")
    try:
        ws.add_document(acc, inside_ws)
        assert False, "expected PathOutsideDataFolderError"
    except PathOutsideWorkspaceError:  # alias of PathOutsideDataFolderError
        pass


def test_import_document_copies_into_data_folder():
    _d, ws = build()
    zk = next(z.key for z in ws.zones() if z.label == "Shared Electricity")
    acc = ws.add_account(zk, "Powerplant Atlantica")
    # a source file OUTSIDE the data folder
    src_dir = tempfile.mkdtemp()
    src = os.path.join(src_dir, "invoice.pdf")
    open(src, "w").write("data")
    doc = ws.import_document(acc, src, statement_number="A1")
    # stored relative to the data folder, under the account id
    assert doc.path == os.path.join(acc.id, "invoice.pdf")
    assert os.path.exists(os.path.join(ws.data_folder, doc.path))
    assert doc.statement_number == "A1"
    # importing a second file with the same name does not clobber the first
    src2 = os.path.join(src_dir, "invoice.pdf")  # same basename
    doc2 = ws.import_document(acc, src2)
    assert doc2.path == os.path.join(acc.id, "invoice_2.pdf")
    assert os.path.exists(os.path.join(ws.data_folder, doc2.path))


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


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    print("ALL MODEL TESTS PASSED")
