"""Display-free model tests (no GTK needed)."""
import datetime
import os
import tempfile

from qdvc.models import SCOPE_BOTH, SCOPE_INDIVIDUAL, SCOPE_SHARED
from qdvc.workspace import PathOutsideWorkspaceError, Workspace


def build():
    d = tempfile.mkdtemp()
    ws = Workspace.create(d)
    ws.add_person("Freja")
    ws.add_person("Ludvig")
    ws.add_zoneblock("Bank Statements", SCOPE_BOTH, "accessories-calculator-symbolic")
    ws.add_zoneblock("Payslips", SCOPE_INDIVIDUAL, "mail-send-receive-symbolic")
    ws.add_zoneblock("Electricity", SCOPE_SHARED, "weather-clear-symbolic")
    return d, ws


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
    d, ws = build()
    zk = next(z.key for z in ws.zones() if z.label == "Freja Bank Statements")
    acc = ws.add_account(zk, "Bank of Atlantis", periodic=True, cycle_days=30)
    assert ws.is_fresh(acc) is False  # no documents
    fp = os.path.join(d, "s.pdf")
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
    d, ws = build()
    zk = next(z.key for z in ws.zones() if z.label == "Shared Electricity")
    acc = ws.add_account(zk, "Powerplant Atlantica")
    fp = os.path.join(d, "bill.pdf")
    open(fp, "w").write("x")
    doc = ws.add_document(acc, fp)
    assert doc.path == "bill.pdf"
    assert not os.path.isabs(doc.path)
    outside = tempfile.mktemp(suffix=".pdf")
    open(outside, "w").write("y")
    try:
        ws.add_document(acc, outside)
        assert False, "expected PathOutsideWorkspaceError"
    except PathOutsideWorkspaceError:
        pass


def test_reload_roundtrip():
    d, ws = build()
    zk = ws.zones()[0].key
    ws.add_account(zk, "Test Account")
    ws2 = Workspace.load(d)
    assert len(ws2.people) == 2
    assert len(ws2.zoneblocks) == 3
    assert len(ws2.accounts) == 1


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    print("ALL MODEL TESTS PASSED")
