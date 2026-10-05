from datetime import datetime, timezone, timedelta
from nema_agora.attestation_lifecycle import (
    AttestationLifecycleRegistry, evaluate_lifecycle, ACTIVE, EXPIRED, REJECTED_STATE,
    REVOKED, SUPERSEDED, PENDING_REVIEW, CONTROL_REQUIRED_STATE, APPROVE, REJECT, REVOKE, SUPERSEDE,
)

def _att(aid="ATT-1", actor="u1", state="ATTESTED"):
    return {"attestation_id": aid, "actor_id": actor, "role": "coordinator",
            "attestation_state": state, "effective_state": state,
            "reconciliation_fingerprint": "r", "evidence_registry_fingerprint": "e",
            "provenance_fingerprint": "p"}

def _base(**kw):
    base = dict(reconciliation_fingerprint="r", evidence_registry_fingerprint="e",
                 provenance_fingerprint="p", integrity_valid=True, provenance_complete=True)
    base.update(kw)
    return base

def test_pending_until_human_lifecycle_decision():
    result = evaluate_lifecycle([_att()], [], **_base(), now="2026-01-01T00:00:00+00:00")
    assert result["overall_state"] == PENDING_REVIEW
    assert result["items"][0]["lifecycle_state"] == PENDING_REVIEW

def test_approve_requires_second_person_and_becomes_active(tmp_path):
    path = tmp_path / "db.sqlite"
    reg = AttestationLifecycleRegistry(path)
    att = _att(actor="attester")
    try:
        reg.decide(attestation_id="ATT-1", decision=APPROVE, actor_id="attester",
                   role="coordinator", attester_actor_id="attester", rationale="Approve exact reviewed snapshot.")
    except ValueError:
        pass
    else:
        assert False, "same actor must not perform second-person approval"
    row = reg.decide(attestation_id="ATT-1", decision=APPROVE, actor_id="reviewer-2",
                     role="coordinator", attester_actor_id="attester", rationale="Second-person review completed.",
                     expires_at="2026-01-02T00:00:00+00:00")
    assert row["decision"] == APPROVE
    result = evaluate_lifecycle([att], reg.list(), **_base(), now="2026-01-01T12:00:00+00:00")
    assert result["overall_state"] == ACTIVE

def test_lifecycle_rejects_same_actor_and_invalid_roles(tmp_path):
    reg = AttestationLifecycleRegistry(tmp_path / "db.sqlite")
    try:
        reg.decide(attestation_id="ATT-1", decision=APPROVE, actor_id="x", role="reviewer",
                   rationale="No.")
    except PermissionError:
        pass
    else:
        assert False
    try:
        reg.decide(attestation_id="ATT-1", decision=APPROVE, actor_id="x", role="coordinator", attester_actor_id="attester",
                   rationale="No.")
    except ValueError:
        pass
    else:
        assert False

def test_expiration_is_deterministic():
    decision = {"decision_id":"D1","attestation_id":"ATT-1","decision":APPROVE,
                "actor_id":"u2","role":"coordinator","rationale":"Approved.",
                "decided_at":"2026-01-01T00:00:00+00:00","expires_at":"2026-01-02T00:00:00+00:00"}
    before = evaluate_lifecycle([_att()], [decision], **_base(), now="2026-01-01T23:59:59+00:00")
    after = evaluate_lifecycle([_att()], [decision], **_base(), now="2026-01-02T00:00:00+00:00")
    assert before["items"][0]["lifecycle_state"] == ACTIVE
    assert after["items"][0]["lifecycle_state"] == EXPIRED

def test_reject_revoke_and_supersede_are_explicit_states():
    for decision, expected in ((REJECT, REJECTED_STATE), (REVOKE, REVOKED), (SUPERSEDE, SUPERSEDED)):
        row = {"decision_id":"D-"+decision,"attestation_id":"ATT-1","decision":decision,
               "actor_id":"u2","role":"coordinator","rationale":"Explicit governance decision.",
               "decided_at":"2026-01-01T00:00:00+00:00"}
        if decision == SUPERSEDE:
            row["superseding_attestation_id"] = "ATT-2"
        result = evaluate_lifecycle([_att()], [row], **_base(), now="2026-01-02T00:00:00+00:00")
        assert result["items"][0]["lifecycle_state"] == expected

def test_stale_snapshot_fails_closed():
    result = evaluate_lifecycle([_att()], [], **_base(evidence_registry_fingerprint="changed"))
    assert result["items"][0]["lifecycle_state"] == "STALE"
    assert result["overall_state"] == PENDING_REVIEW

def test_integrity_failure_is_control_required():
    result = evaluate_lifecycle([_att()], [], **_base(integrity_valid=False))
    assert result["overall_state"] == CONTROL_REQUIRED_STATE

def test_multiple_active_attestations_conflict():
    decisions = [
        {"decision_id":"D1","attestation_id":"ATT-1","decision":APPROVE,"actor_id":"u2","role":"coordinator","rationale":"Approved.","decided_at":"2026-01-01T00:00:00+00:00","expires_at":"2027-01-01T00:00:00+00:00"},
        {"decision_id":"D2","attestation_id":"ATT-2","decision":APPROVE,"actor_id":"u3","role":"coordinator","rationale":"Approved.","decided_at":"2026-01-01T00:01:00+00:00","expires_at":"2027-01-01T00:00:00+00:00"},
    ]
    result = evaluate_lifecycle([_att("ATT-1","u1"), _att("ATT-2","u2")], decisions, **_base(), now="2026-01-02T00:00:00+00:00")
    assert result["overall_state"] == CONTROL_REQUIRED_STATE
    assert result["conflict_count"] == 1
