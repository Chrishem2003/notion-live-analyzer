"""Tests for Phase 139 authorization-history decision continuity."""
from __future__ import annotations

from copy import deepcopy

import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_phase137 import (
    authorize_authorization_history_registry_decision,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_phase139 import (
    build_authorization_history_registry_decision_continuity,
    validate_authorization_history_registry_decision_snapshot,
    reconcile_authorization_history_registry_decision_history,
    validate_authorization_history_registry_decision_history_reconciliation,
)


def _lifecycle() -> dict:
    item = {
        "policy_version": "phase136-v1",
        "monitor_fingerprint": "monitor-139",
        "review_fingerprint": "review-139",
        "review_outcome": "ACKNOWLEDGED",
        "lifecycle_state": "ACKNOWLEDGED",
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


def _decision() -> dict:
    return authorize_authorization_history_registry_decision(
        _lifecycle(),
        actor_id="coordinator-139",
        role="coordinator",
        decision="AUTHORIZE_PRESERVATION",
        decided_at="2026-10-04T12:05:00+00:00",
        rationale="Preserve the authorization-history evidence under human governance.",
    )


def _snapshot(sequence: int = 1, previous: str | None = None) -> dict:
    return build_authorization_history_registry_decision_continuity(
        [_decision()],
        captured_at=f"2026-10-04T12:{10 + sequence:02d}:00+00:00",
        sequence=sequence,
        previous_snapshot_fingerprint=previous,
    )


def test_continuity_snapshot_builds_and_validates() -> None:
    snapshot = _snapshot()
    assert snapshot["sequence"] == 1
    assert snapshot["previous_snapshot_fingerprint"] is None
    assert validate_authorization_history_registry_decision_snapshot(snapshot) == snapshot


def test_two_snapshots_bind_predecessor() -> None:
    first = _snapshot()
    second = _snapshot(2, first["snapshot_fingerprint"])
    result = reconcile_authorization_history_registry_decision_history([first, second])
    assert result["state"] == "HISTORY_READY"
    assert result["findings"] == []
    assert validate_authorization_history_registry_decision_history_reconciliation(result) == result


def test_history_must_start_at_one() -> None:
    result = reconcile_authorization_history_registry_decision_history([_snapshot(2)])
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "HISTORY_MUST_START_AT_ONE" for x in result["findings"])


def test_sequence_gap_and_predecessor_mismatch() -> None:
    first = _snapshot()
    third = _snapshot(3, "wrong-predecessor")
    result = reconcile_authorization_history_registry_decision_history([first, third])
    codes = {x["code"] for x in result["findings"]}
    assert "SEQUENCE_GAP" in codes
    assert "PREDECESSOR_MISMATCH" in codes


def test_tampered_snapshot_is_rejected() -> None:
    snapshot = _snapshot()
    tampered = deepcopy(snapshot)
    tampered["decision_count"] = 99
    with pytest.raises(ValueError):
        validate_authorization_history_registry_decision_snapshot(tampered)


def test_duplicate_decision_identity_is_rejected() -> None:
    with pytest.raises(ValueError, match="DUPLICATE_DECISION_IDENTITY"):
        build_authorization_history_registry_decision_continuity(
            [_decision(), _decision()],
            captured_at="2026-10-04T12:20:00+00:00",
            sequence=1,
        )


def test_deterministic_snapshot_fingerprint() -> None:
    first = _snapshot()
    second = _snapshot()
    assert first["snapshot_fingerprint"] == second["snapshot_fingerprint"]
