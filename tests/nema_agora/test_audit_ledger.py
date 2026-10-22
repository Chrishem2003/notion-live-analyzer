import sqlite3
import pytest
from nema_agora.audit_ledger import AuditLedger

def test_ledger_appends_and_verifies_chain(tmp_path):
    ledger=AuditLedger(tmp_path/"ledger.db")
    ledger.append(entry_id="E1",actor_id="reviewer",event_type="REVIEW",payload={"decision":"checked"},occurred_at="2026-01-01T00:00:00Z")
    ledger.append(entry_id="E2",actor_id="coordinator",event_type="APPROVAL",payload={"ok":True},occurred_at="2026-01-02T00:00:00Z")
    result=ledger.verify()
    assert result["valid"] is True and result["entries"]==2

def test_ledger_blocks_duplicate_entry_ids(tmp_path):
    ledger=AuditLedger(tmp_path/"ledger.db")
    ledger.append(entry_id="E1",actor_id="r",event_type="REVIEW",payload={})
    with pytest.raises(sqlite3.IntegrityError):
        ledger.append(entry_id="E1",actor_id="r",event_type="REVIEW",payload={})

def test_ledger_sqlite_triggers_reject_update_and_delete(tmp_path):
    path=tmp_path/"ledger.db"; ledger=AuditLedger(path)
    ledger.append(entry_id="E1",actor_id="r",event_type="REVIEW",payload={})
    with sqlite3.connect(path) as db:
        with pytest.raises(sqlite3.IntegrityError): db.execute("UPDATE audit_ledger SET actor_id='x' WHERE entry_id='E1'")
        with pytest.raises(sqlite3.IntegrityError): db.execute("DELETE FROM audit_ledger WHERE entry_id='E1'")

def test_ledger_verification_detects_tampering(tmp_path):
    path=tmp_path/"ledger.db"; ledger=AuditLedger(path)
    ledger.append(entry_id="E1",actor_id="r",event_type="REVIEW",payload={"v":1})
    with sqlite3.connect(path) as db: db.execute("DROP TRIGGER audit_ledger_no_update")
    with sqlite3.connect(path) as db: db.execute("UPDATE audit_ledger SET payload_json='{}' WHERE entry_id='E1'")
    result=ledger.verify()
    assert result["valid"] is False
    assert any("ENTRY_HASH_MISMATCH" in error for error in result["errors"])

def test_checkpoint_records_verified_head(tmp_path):
    ledger=AuditLedger(tmp_path/"ledger.db")
    ledger.append(entry_id="E1",actor_id="r",event_type="REVIEW",payload={})
    checkpoint=ledger.create_checkpoint(checkpoint_id="CP1",actor_id="admin")
    assert checkpoint["sequence"]==1
    assert ledger.list_checkpoints()[0]["checkpoint_id"]=="CP1"
