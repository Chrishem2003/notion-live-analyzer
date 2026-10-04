import sqlite3,pytest
from nema_agora.decision_receipt import validate_receipt,DecisionReceiptRegistry
def _d(): return {"decision_id":"DEC-1","decision":"APPROVE","reviewer_actor_id":"r2"}
def _p(): return {"decision_status":"NOT_DECIDED","current_snapshot":{"r":"1"}}
def test_valid_receipt_is_not_decision_execution():
 o=validate_receipt(decision=_d(),prepared_package=_p(),current_snapshot={"r":"1"},actor_id="r2")
 assert o["state"]=="READY_FOR_RECEIPT"
 assert o["receipt"]["decision_id"]=="DEC-1"
def test_stale_or_actor_mismatch_fails_closed():
 o=validate_receipt(decision=_d(),prepared_package=_p(),current_snapshot={"r":"2"},actor_id="r3")
 assert o["state"]=="CONTROL_REQUIRED"; assert "SNAPSHOT_MISMATCH" in o["failures"]; assert "ACTOR_MISMATCH" in o["failures"]
def test_registry_is_append_only():
 db=sqlite3.connect(":memory:"); reg=DecisionReceiptRegistry(db)
 r={"decision_id":"DEC-1","decision":"APPROVE","actor_id":"r2","current_snapshot":{"r":"1"}}
 reg.register(receipt=r,created_at="2026-10-04T12:00:00Z")
 with pytest.raises(sqlite3.IntegrityError): db.execute("DELETE FROM decision_receipts")
