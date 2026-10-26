"""Tests for Phase 140 persistent authorization-history decision registry."""
from __future__ import annotations

from copy import deepcopy

import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_phase137 import (
    authorize_authorization_history_registry_decision,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_phase139 import (
    build_authorization_history_registry_decision_continuity,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_registry_phase140 import (
    AuthorizationHistoryRegistryDecisionHistoryRegistry,
)


def _lifecycle() -> dict:
    item = {
        "policy_version": "phase136-v1",
        "monitor_fingerprint": "monitor-140",
        "review_fingerprint": "review-140",
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
        actor_id="coordinator-140",
        role="coordinator",
        decision="AUTHORIZE_PRESERVATION",
        decided_at="2026-10-04T12:05:00+00:00",
        rationale="Preserve authorization-history evidence without execution.",
    )


def _snapshot(sequence: int = 1, previous: str | None = None) -> dict:
    return build_authorization_history_registry_decision_continuity(
        [_decision()],
        captured_at=f"2026-10-04T12:{10 + sequence:02d}:00+00:00",
        sequence=sequence,
        previous_snapshot_fingerprint=previous,
    )


def test_append_list_count_and_reconcile(tmp_path) -> None:
    registry = AuthorizationHistoryRegistryDecisionHistoryRegistry(tmp_path / "phase140.sqlite")
    first = _snapshot()
    second = _snapshot(2, first["snapshot_fingerprint"])
    stored_first = registry.append(first)
    stored_second = registry.append(second)
    assert stored_first["registry_policy_version"] == "phase140-v1"
    assert stored_second["sequence"] == 2
    assert registry.count() == 2
    assert [x["sequence"] for x in registry.list()] == [1, 2]
    assert registry.reconcile_history()["state"] == "HISTORY_READY"


def test_first_sequence_is_required(tmp_path) -> None:
    registry = AuthorizationHistoryRegistryDecisionHistoryRegistry(tmp_path / "phase140.sqlite")
    with pytest.raises(ValueError, match="FIRST_SNAPSHOT_SEQUENCE_REQUIRED"):
        registry.append(_snapshot(2))


def test_exact_next_sequence_and_predecessor_are_required(tmp_path) -> None:
    registry = AuthorizationHistoryRegistryDecisionHistoryRegistry(tmp_path / "phase140.sqlite")
    first = _snapshot()
    registry.append(first)
    with pytest.raises(ValueError, match="SNAPSHOT_SEQUENCE_NOT_NEXT"):
        registry.append(_snapshot(3, first["snapshot_fingerprint"]))
    with pytest.raises(ValueError, match="SNAPSHOT_PREDECESSOR_MISMATCH"):
        registry.append(_snapshot(2, "wrong-predecessor"))


def test_duplicate_snapshot_conflicts(tmp_path) -> None:
    registry = AuthorizationHistoryRegistryDecisionHistoryRegistry(tmp_path / "phase140.sqlite")
    first = _snapshot()
    registry.append(first)
    with pytest.raises(ValueError, match="SNAPSHOT_HISTORY_CONFLICT"):
        registry.append(deepcopy(first))


def test_update_and_delete_are_blocked(tmp_path) -> None:
    registry = AuthorizationHistoryRegistryDecisionHistoryRegistry(tmp_path / "phase140.sqlite")
    registry.append(_snapshot())
    import sqlite3
    with sqlite3.connect(registry.database_path) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "UPDATE authorization_history_registry_decision_history SET captured_at='tampered'"
            )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM authorization_history_registry_decision_history")


def test_invalid_list_limits_are_rejected(tmp_path) -> None:
    registry = AuthorizationHistoryRegistryDecisionHistoryRegistry(tmp_path / "phase140.sqlite")
    for limit in (0, 501, True, "5"):
        with pytest.raises(ValueError, match="INVALID_LIMIT"):
            registry.list(limit)
