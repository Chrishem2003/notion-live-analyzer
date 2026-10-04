"""Tests for Phase 138 lifecycle/decision reconciliation."""
from __future__ import annotations

from copy import deepcopy

import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_phase137 import (
    authorize_authorization_history_registry_decision,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_reconciliation_phase138 import (
    reconcile_authorization_history_registry_decisions,
    validate_authorization_history_registry_decision_reconciliation,
)


def _lifecycle(state: str) -> dict:
    outcome = {
        "ACKNOWLEDGED": "ACKNOWLEDGED",
        "DEFERRED": "REVIEW_AUTHORIZATION_HISTORY_REGISTRY",
        "ESCALATED": "ESCALATED",
    }[state]
    item = {
        "policy_version": "phase136-v1",
        "monitor_fingerprint": "monitor-138",
        "review_fingerprint": "review-138",
        "review_outcome": outcome,
        "lifecycle_state": state,
        "evaluated_at": "2026-10-04T12:00:00+00:00",
        "human_governed": True,
        "automatic_repair_performed": False,
        "decision_executed": False,
        "execution_gate_closed": True,
        "execution_permitted": False,
        "execution_performed": False,
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
        "emergency_action": None,
    }
    return dict(item, lifecycle_fingerprint=fingerprint(item))


def _decision(lifecycle: dict, choice: str = "AUTHORIZE_PRESERVATION") -> dict:
    return authorize_authorization_history_registry_decision(
        lifecycle,
        actor_id="coordinator-138",
        role="coordinator",
        decision=choice,
        decided_at="2026-10-04T12:10:00+00:00",
        rationale="Record a human-governed authorization without executing it.",
    )


def test_reconciled_valid_pair() -> None:
    lifecycle = _lifecycle("ACKNOWLEDGED")
    decision = _decision(lifecycle)
    result = reconcile_authorization_history_registry_decisions([lifecycle], [decision], expected_decision_count=1)
    assert result["state"] == "RECONCILED"
    assert result["findings"] == []
    assert validate_authorization_history_registry_decision_reconciliation(result) == result


def test_unreviewed_lifecycle_requires_control() -> None:
    result = reconcile_authorization_history_registry_decisions([_lifecycle("ACKNOWLEDGED")], [])
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "UNAUTHORIZED_LIFECYCLE" for x in result["findings"])


def test_orphan_decision_requires_control() -> None:
    lifecycle = _lifecycle("ACKNOWLEDGED")
    decision = _decision(lifecycle)
    orphan = deepcopy(decision)
    orphan["lifecycle_fingerprint"] = "missing-lifecycle"
    result = reconcile_authorization_history_registry_decisions([], [orphan])
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "ORPHAN_DECISION" for x in result["findings"])


def test_multiple_decisions_are_detected() -> None:
    lifecycle = _lifecycle("ACKNOWLEDGED")
    first = _decision(lifecycle)
    second = authorize_authorization_history_registry_decision(
        lifecycle,
        actor_id="admin-138",
        role="admin",
        decision="AUTHORIZE_PRESERVATION",
        decided_at="2026-10-04T12:11:00+00:00",
        rationale="Second authorization must be detected as duplicate lifecycle authorization.",
    )
    result = reconcile_authorization_history_registry_decisions([lifecycle], [first, second])
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "MULTIPLE_DECISIONS_FOR_LIFECYCLE" for x in result["findings"])


def test_binding_mismatch_is_detected() -> None:
    lifecycle = _lifecycle("ACKNOWLEDGED")
    decision = _decision(lifecycle)
    tampered = deepcopy(decision)
    tampered["review_fingerprint"] = "other-review"
    # Re-sign the decision so validation succeeds and reconciliation reaches binding checks.
    tampered["decision_fingerprint"] = fingerprint({k: v for k, v in tampered.items() if k != "decision_fingerprint"})
    result = reconcile_authorization_history_registry_decisions([lifecycle], [tampered])
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "REVIEW_BINDING_MISMATCH" for x in result["findings"])


def test_execution_gate_tampering_is_detected() -> None:
    lifecycle = _lifecycle("ACKNOWLEDGED")
    decision = _decision(lifecycle)
    tampered = deepcopy(decision)
    tampered["execution_performed"] = True
    result = reconcile_authorization_history_registry_decisions([lifecycle], [tampered])
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "INVALID_DECISION" for x in result["findings"])


def test_decision_count_mismatch_is_detected() -> None:
    lifecycle = _lifecycle("ACKNOWLEDGED")
    decision = _decision(lifecycle)
    result = reconcile_authorization_history_registry_decisions(
        [lifecycle], [decision], expected_decision_count=2
    )
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "DECISION_COUNT_MISMATCH" for x in result["findings"])


def test_deterministic_reconciliation() -> None:
    lifecycle = _lifecycle("ACKNOWLEDGED")
    decision = _decision(lifecycle)
    first = reconcile_authorization_history_registry_decisions([lifecycle], [decision])
    second = reconcile_authorization_history_registry_decisions([lifecycle], [decision])
    assert first["reconciliation_fingerprint"] == second["reconciliation_fingerprint"]
