"""Tests for Phase 137 authorization-history registry lifecycle decisions."""
from __future__ import annotations

from copy import deepcopy

import pytest

from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_phase137 import (
    authorize_authorization_history_registry_decision,
    validate_authorization_history_registry_decision,
)


def _lifecycle(state: str) -> dict:
    return {
        "policy_version": "phase136-v1",
        "monitor_fingerprint": "monitor-137",
        "review_fingerprint": "review-137",
        "review_outcome": {
            "ACKNOWLEDGED": "ACKNOWLEDGED",
            "DEFERRED": "REVIEW_AUTHORIZATION_HISTORY_REGISTRY",
            "ESCALATED": "ESCALATED",
        }[state],
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


def _valid_lifecycle(state: str) -> dict:
    from nema_agora.api_audit_binding import fingerprint

    item = _lifecycle(state)
    item["lifecycle_fingerprint"] = fingerprint(
        {k: v for k, v in item.items() if k != "lifecycle_fingerprint"}
    )
    return item


def test_acknowledged_authorizes_preservation() -> None:
    decision = authorize_authorization_history_registry_decision(
        _valid_lifecycle("ACKNOWLEDGED"),
        actor_id="coordinator-1",
        role="coordinator",
        decision="AUTHORIZE_PRESERVATION",
        decided_at="2026-10-04T12:05:00+00:00",
        rationale="Preserve the validated authorization-history evidence.",
    )
    assert decision["decision"] == "AUTHORIZE_PRESERVATION"
    assert decision["lifecycle_state"] == "ACKNOWLEDGED"
    assert decision["human_authorized"] is True
    assert decision["execution_gate_closed"] is True
    assert decision["execution_permitted"] is False
    assert decision["execution_performed"] is False
    assert validate_authorization_history_registry_decision(decision) == decision


@pytest.mark.parametrize(
    "decision",
    ["AUTHORIZE_AUTHORIZATION_HISTORY_REVIEW", "AUTHORIZE_PRESERVATION"],
)
def test_deferred_supports_review_or_preservation(decision: str) -> None:
    result = authorize_authorization_history_registry_decision(
        _valid_lifecycle("DEFERRED"),
        actor_id="admin-1",
        role="admin",
        decision=decision,
        decided_at="2026-10-04T12:06:00+00:00",
        rationale="Human review is required before any evidence handling decision.",
    )
    assert result["lifecycle_state"] == "DEFERRED"
    assert result["decision"] == decision


def test_escalated_requires_escalation_authorization() -> None:
    result = authorize_authorization_history_registry_decision(
        _valid_lifecycle("ESCALATED"),
        actor_id="admin-2",
        role="admin",
        decision="AUTHORIZE_ESCALATION",
        decided_at="2026-10-04T12:07:00+00:00",
        rationale="Escalate the lifecycle state for human governance.",
    )
    assert result["decision"] == "AUTHORIZE_ESCALATION"


def test_invalid_state_decision_pair_is_blocked() -> None:
    with pytest.raises(ValueError, match="DECISION_LIFECYCLE_STATE_MISMATCH"):
        authorize_authorization_history_registry_decision(
            _valid_lifecycle("ACKNOWLEDGED"),
            actor_id="coordinator-1",
            role="coordinator",
            decision="AUTHORIZE_AUTHORIZATION_HISTORY_REVIEW",
            decided_at="2026-10-04T12:08:00+00:00",
            rationale="This must not be authorized from an acknowledged state.",
        )


def test_execution_boundary_tampering_is_rejected() -> None:
    decision = authorize_authorization_history_registry_decision(
        _valid_lifecycle("ACKNOWLEDGED"),
        actor_id="coordinator-1",
        role="coordinator",
        decision="AUTHORIZE_PRESERVATION",
        decided_at="2026-10-04T12:09:00+00:00",
        rationale="Preserve evidence only; execution remains closed.",
    )
    tampered = deepcopy(decision)
    tampered["execution_performed"] = True
    with pytest.raises(ValueError, match="INVALID_EXECUTION_BOUNDARY|DECISION_FINGERPRINT_MISMATCH|EXECUTION_MUST_REMAIN_FORBIDDEN"):
        validate_authorization_history_registry_decision(tampered)


def test_fingerprint_is_deterministic() -> None:
    kwargs = {
        "actor_id": "coordinator-1",
        "role": "coordinator",
        "decision": "AUTHORIZE_PRESERVATION",
        "decided_at": "2026-10-04T12:10:00+00:00",
        "rationale": "Keep the authorization-history record preserved.",
    }
    first = authorize_authorization_history_registry_decision(_valid_lifecycle("ACKNOWLEDGED"), **kwargs)
    second = authorize_authorization_history_registry_decision(_valid_lifecycle("ACKNOWLEDGED"), **kwargs)
    assert first["decision_fingerprint"] == second["decision_fingerprint"]
