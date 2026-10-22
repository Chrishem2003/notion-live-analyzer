import pytest
from nema_agora.audit_ledger import AuditLedger
from nema_agora.governance_decision_ledger import GovernanceDecisionLedger

def test_records_evaluation_decision_and_is_idempotent(tmp_path):
    path=tmp_path/"audit.sqlite"
    service=GovernanceDecisionLedger(str(path))
    first=service.record(decision_kind="evaluation_completed",actor_id="reviewer-1",role="reviewer",
        artifact_id="RUN-1",status="COMPLETED",decision="APPROVE",reason_code="EVAL_COMPLETE")
    second=service.record(decision_kind="evaluation_completed",actor_id="reviewer-1",role="reviewer",
        artifact_id="RUN-1",status="COMPLETED",decision="APPROVE",reason_code="EVAL_COMPLETE")
    assert first["recorded"] is True
    assert second["duplicate"] is True
    assert len(AuditLedger(path).list_entries()) == 1

def test_review_and_lifecycle_are_allowlisted(tmp_path):
    s=GovernanceDecisionLedger(str(tmp_path/"audit.sqlite"))
    s.record(decision_kind="review_decision",actor_id="r",role="reviewer",artifact_id="REV-1",
            status="COMPLETED",decision="APPROVE",reason_code="HUMAN_REVIEW")
    s.record(decision_kind="lifecycle_decision",actor_id="c",role="coordinator",artifact_id="LCD-1",
            status="COMPLETED",decision="DEFER",reason_code="HUMAN_GOVERNANCE")
    assert len(s.ledger.list_entries()) == 2
    assert s.ledger.verify()["valid"] is True

def test_rejects_unknown_decision_kind(tmp_path):
    s=GovernanceDecisionLedger(str(tmp_path/"audit.sqlite"))
    with pytest.raises(ValueError):
        s.record(decision_kind="invented",actor_id="r",role="reviewer",artifact_id="X",
                 status="COMPLETED",decision="APPROVE",reason_code="X")

def test_conflicting_identity_fails_closed(tmp_path):
    s=GovernanceDecisionLedger(str(tmp_path/"audit.sqlite"))
    s.record(decision_kind="review_decision",actor_id="r",role="reviewer",artifact_id="REV-1",
             status="COMPLETED",decision="APPROVE",reason_code="A")
    with pytest.raises(ValueError, match="EVENT_ID_CONFLICT"):
        s.record(decision_kind="review_decision",actor_id="r",role="reviewer",artifact_id="REV-1",
                 status="REJECTED",decision="REJECT",reason_code="B")

def test_access_denial_is_metadata_only(tmp_path):
    s=GovernanceDecisionLedger(str(tmp_path/"audit.sqlite"))
    result=s.record(decision_kind="access_denied",actor_id="system",role="admin",artifact_id="PERMISSION",
                    status="REJECTED",decision="REJECT",reason_code="DENIED")
    assert result["recorded"] is True
    assert s.ledger.verify()["valid"] is True
