import json
import sqlite3

import pytest

from nema_agora.audit_ledger import AuditLedger, GENESIS_HASH
from nema_agora.audit_recovery import (
    CHECKPOINT_SCHEMA, compare_backup_to_checkpoint, export_checkpoint,
    verify_entries_against_checkpoint, verify_ledger_against_checkpoint,
)


def populated_ledger(tmp_path, name="ledger.db"):
    ledger = AuditLedger(tmp_path / name)
    ledger.append(entry_id="E1", actor_id="reviewer", event_type="REVIEW", payload={"v": 1},
                  occurred_at="2026-01-01T00:00:00Z")
    ledger.append(entry_id="E2", actor_id="coordinator", event_type="APPROVAL_REVIEW", payload={"v": 2},
                  occurred_at="2026-01-02T00:00:00Z")
    return ledger


def test_exported_checkpoint_verifies_matching_ledger(tmp_path):
    ledger = populated_ledger(tmp_path)
    checkpoint = ledger.create_checkpoint(checkpoint_id="CP1", actor_id="admin")
    exported = export_checkpoint(checkpoint)
    result = verify_ledger_against_checkpoint(ledger, exported)
    assert exported["schema"] == CHECKPOINT_SCHEMA
    assert result["valid"] is True
    assert result["checkpoint_hash_matches"] is True


def test_tampering_before_checkpoint_is_detected(tmp_path):
    ledger = populated_ledger(tmp_path)
    checkpoint = export_checkpoint(ledger.create_checkpoint(checkpoint_id="CP1", actor_id="admin"))
    path = ledger.database_path
    with sqlite3.connect(path) as db:
        db.execute("DROP TRIGGER audit_ledger_no_update")
        db.execute("UPDATE audit_ledger SET payload_json='{}' WHERE sequence=1")
    result = verify_ledger_against_checkpoint(ledger, checkpoint)
    assert result["valid"] is False
    assert "ENTRY_HASH_MISMATCH:1" in result["errors"]


def test_truncated_ledger_is_detected_against_checkpoint(tmp_path):
    ledger = populated_ledger(tmp_path)
    checkpoint = export_checkpoint(ledger.create_checkpoint(checkpoint_id="CP1", actor_id="admin"))
    entries = ledger.list_entries()
    result = verify_entries_against_checkpoint(entries[:1], checkpoint)
    assert result["valid"] is False
    assert "CHECKPOINT_AHEAD_OF_LEDGER" in result["errors"]


def test_backup_comparison_is_read_only_and_does_not_modify_backup(tmp_path):
    source = populated_ledger(tmp_path, "source.db")
    backup = populated_ledger(tmp_path, "backup.db")
    checkpoint = export_checkpoint(source.create_checkpoint(checkpoint_id="CP1", actor_id="admin"))
    before = backup.list_entries()
    result = compare_backup_to_checkpoint(backup.list_entries(), checkpoint)
    after = backup.list_entries()
    assert result["valid"] is True
    assert before == after


def test_invalid_checkpoint_rejected():
    with pytest.raises(ValueError):
        verify_entries_against_checkpoint([], {"checkpoint_id": "CP", "sequence": -1,
            "entry_hash": GENESIS_HASH, "created_at": "now", "actor_id": "admin"})


def test_checkpoint_hash_mismatch_detected():
    entries = [{
        "sequence": 1, "entry_id": "E1", "actor_id": "r", "event_type": "REVIEW",
        "occurred_at": "2026-01-01T00:00:00Z", "payload": {}, "previous_hash": GENESIS_HASH,
        "policy_version": "phase34-v1", "entry_hash": "a" * 64,
    }]
    checkpoint = {"checkpoint_id": "CP", "sequence": 1, "entry_hash": "b" * 64,
                  "created_at": "now", "actor_id": "admin"}
    result = verify_entries_against_checkpoint(entries, checkpoint)
    assert result["valid"] is False
    assert "CHECKPOINT_HASH_MISMATCH" in result["errors"]
