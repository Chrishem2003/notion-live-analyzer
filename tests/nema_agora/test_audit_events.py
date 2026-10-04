import pytest

from nema_agora.audit_ledger import AuditLedger
from nema_agora.audit_events import AuditEventCapture


def test_allowlisted_event_is_recorded_and_ledger_verifies(tmp_path):
    ledger = AuditLedger(tmp_path / "events.db")
    capture = AuditEventCapture(ledger)
    result = capture.record(
        event_id="eval-001",
        event_type="EVALUATION_COMPLETED",
        actor_id="reviewer-7",
        payload={"artifact_id": "EVAL-1", "artifact_hash": "a" * 64,
                 "status": "COMPLETED", "counts": {"accepted": 4}},
    )
    assert result["recorded"] is True
    assert result["duplicate"] is False
    assert ledger.verify()["valid"] is True


def test_retry_is_idempotent(tmp_path):
    capture = AuditEventCapture(AuditLedger(tmp_path / "events.db"))
    kwargs = dict(event_id="review-001", event_type="REVIEW_DECISION_RECORDED",
                  actor_id="reviewer-7", payload={"decision": "HUMAN_REVIEW_REQUIRED"})
    first = capture.record(**kwargs)
    second = capture.record(**kwargs)
    assert first["recorded"] is True
    assert second["duplicate"] is True
    assert len(capture.ledger.list_entries()) == 1


def test_unknown_event_type_is_rejected(tmp_path):
    capture = AuditEventCapture(AuditLedger(tmp_path / "events.db"))
    with pytest.raises(ValueError, match="not allowlisted"):
        capture.record(event_id="x", event_type="DELETE_EVIDENCE", actor_id="admin", payload={})


def test_unapproved_or_sensitive_payload_keys_are_rejected(tmp_path):
    capture = AuditEventCapture(AuditLedger(tmp_path / "events.db"))
    with pytest.raises(ValueError, match="Unsupported audit metadata key"):
        capture.record(event_id="x", event_type="EVALUATION_COMPLETED", actor_id="admin",
                       payload={"observation_text": "private narrative"})
    with pytest.raises(ValueError, match="Unsupported audit metadata key"):
        capture.record(event_id="x2", event_type="EVALUATION_COMPLETED", actor_id="admin",
                       payload={"password": "do-not-log"})


def test_reused_event_id_with_changed_payload_is_conflict(tmp_path):
    capture = AuditEventCapture(AuditLedger(tmp_path / "events.db"))
    capture.record(event_id="eval-001", event_type="EVALUATION_COMPLETED",
                   actor_id="reviewer", payload={"status": "COMPLETED"})
    with pytest.raises(ValueError, match="EVENT_ID_CONFLICT"):
        capture.record(event_id="eval-001", event_type="EVALUATION_COMPLETED",
                       actor_id="reviewer", payload={"status": "FAILED"})


def test_actor_cannot_be_blank(tmp_path):
    capture = AuditEventCapture(AuditLedger(tmp_path / "events.db"))
    with pytest.raises(ValueError, match="Authenticated actor ID"):
        capture.record(event_id="x", event_type="EVALUATION_COMPLETED", actor_id=" ", payload={})
