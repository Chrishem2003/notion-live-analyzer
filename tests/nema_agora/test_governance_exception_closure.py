from nema_agora.governance_exception_closure import evaluate_closure
from nema_agora.governance_exception_resolution import GovernanceExceptionResolver


def _reconciliation(fp="fp-1"):
    return {
        "status": "CONTROL_REQUIRED",
        "reconciliation_fingerprint": fp,
        "exceptions": [{
            "code": "MISSING_AUDIT_EVENT",
            "severity": "CRITICAL",
            "decision_kind": "review_decision",
            "artifact_id": "REV-1",
            "detail": "missing",
        }],
    }


def test_unresolved_exception_remains_open():
    result = evaluate_closure(_reconciliation(), [])
    assert result["overall_status"] == "CONTROL_REQUIRED"
    assert result["results"][0]["closure_code"] == "NO_RESOLUTION"


def test_closeable_resolution_requires_evidence(tmp_path):
    path = tmp_path / "db.sqlite"
    resolver = GovernanceExceptionResolver(path)
    resolver.resolve(
        exception_code="MISSING_AUDIT_EVENT",
        decision_kind="review_decision",
        artifact_id="REV-1",
        actor_id="u1",
        role="reviewer",
        outcome="CORRECTED_AT_SOURCE",
        reason_code="SOURCE_RECHECKED",
        reconciliation_fingerprint="fp-1",
    )
    result = evaluate_closure(_reconciliation(), resolver.list_resolutions())
    assert result["results"][0]["status"] == "REVIEW_REQUIRED"
    assert result["results"][0]["closure_code"] == "MISSING_CLOSURE_EVIDENCE"


def test_closeable_resolution_with_hashed_evidence_closes(tmp_path):
    path = tmp_path / "db.sqlite"
    resolver = GovernanceExceptionResolver(path)
    resolver.resolve(
        exception_code="MISSING_AUDIT_EVENT",
        decision_kind="review_decision",
        artifact_id="REV-1",
        actor_id="u1",
        role="coordinator",
        outcome="FALSE_POSITIVE",
        reason_code="VERIFIED",
        reconciliation_fingerprint="fp-1",
    )
    evidence = {
        ("MISSING_AUDIT_EVENT", "review_decision", "REV-1"): {
            "evidence_id": "EVID-REV-1",
            "evidence_hash": "a" * 64,
        }
    }
    result = evaluate_closure(_reconciliation(), resolver.list_resolutions(), evidence_by_key=evidence)
    assert result["overall_status"] == "CLOSED"
    assert result["results"][0]["status"] == "CLOSED"


def test_acknowledged_and_escalated_do_not_close(tmp_path):
    for outcome, expected in [("ACKNOWLEDGED", "REVIEW_REQUIRED"), ("ESCALATED", "CONTROL_REQUIRED")]:
        path = tmp_path / f"{outcome}.sqlite"
        resolver = GovernanceExceptionResolver(path)
        resolver.resolve(
            exception_code="MISSING_AUDIT_EVENT",
            decision_kind="review_decision",
            artifact_id="REV-1",
            actor_id="u1",
            role="reviewer",
            outcome=outcome,
            reason_code="CHECKED",
            reconciliation_fingerprint="fp-1",
        )
        result = evaluate_closure(_reconciliation(), resolver.list_resolutions())
        assert result["results"][0]["status"] == expected


def test_stale_resolution_does_not_close_current_exception(tmp_path):
    path = tmp_path / "db.sqlite"
    resolver = GovernanceExceptionResolver(path)
    resolver.resolve(
        exception_code="MISSING_AUDIT_EVENT",
        decision_kind="review_decision",
        artifact_id="REV-1",
        actor_id="u1",
        role="reviewer",
        outcome="CORRECTED_AT_SOURCE",
        reason_code="OLD",
        reconciliation_fingerprint="old-fingerprint",
    )
    result = evaluate_closure(_reconciliation("new-fingerprint"), resolver.list_resolutions())
    assert result["results"][0]["closure_code"] == "NO_RESOLUTION"
