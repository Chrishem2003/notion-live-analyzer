import tempfile
from nema_agora.api_governance_drift_recovery_authorization_history import build_authorization_continuity
from nema_agora.api_governance_drift_recovery_authorization_registry import RecoveryAuthorizationHistoryRegistry
from nema_agora.api_governance_drift_recovery_authorization_retention_monitor import build_authorization_retention_monitor

def _decision():
    from nema_agora.api_governance_drift_recovery_review_ledger import review_recovery_recommendation
    from nema_agora.api_governance_drift_recovery_review_lifecycle import evaluate_recovery_review
    from nema_agora.api_governance_drift_recovery_decision_ledger import authorize_recovery_decision
    from nema_agora.api_governance_drift_reconciliation_monitor import build_history_integrity_monitor
    monitor = build_history_integrity_monitor([], expected_count=0, observed_at="2026-10-04T12:00:00+00:00")
    review = review_recovery_recommendation(monitor, actor_id="reviewer", role="coordinator", outcome="NO_ACTION_APPROVED", reviewed_at="2026-10-04T12:01:00+00:00")
    lifecycle = evaluate_recovery_review(review, evaluated_at="2026-10-04T12:02:00+00:00")
    return authorize_recovery_decision(lifecycle, actor_id="admin", role="admin", decision="AUTHORIZE_NO_ACTION", decided_at="2026-10-04T12:03:00+00:00")

def _snapshot(sequence, previous=None):
    return build_authorization_continuity([_decision()], captured_at="2026-10-04T12:04:00+00:00", sequence=sequence, previous_snapshot_fingerprint=previous)

def test_empty_history():
    result = build_authorization_retention_monitor([], expected_count=0, observed_at="2026-10-04T12:05:00+00:00")
    assert result["state"] == "NO_HISTORY"
    assert result["retention_recommendation"] == "REVIEW_RETENTION"
    assert result["automatic_repair_performed"] is False

def test_healthy_history_and_deterministic_fingerprint():
    first = _snapshot(1)
    records = [{"registry_policy_version": "phase116-v1", **first}]
    result = build_authorization_retention_monitor(records, expected_count=1, observed_at="2026-10-04T12:05:00+00:00")
    again = build_authorization_retention_monitor(records, expected_count=1, observed_at="2026-10-04T12:05:00+00:00")
    assert result["state"] == "RETENTION_HEALTHY"
    assert result["monitor_fingerprint"] == again["monitor_fingerprint"]

def test_sequence_gap():
    first = _snapshot(1)
    third = _snapshot(3, previous=first["snapshot_fingerprint"])
    result = build_authorization_retention_monitor(
        [{"registry_policy_version": "phase116-v1", **first}, {"registry_policy_version": "phase116-v1", **third}],
        expected_count=2, observed_at="2026-10-04T12:05:00+00:00")
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "SEQUENCE_GAP" for x in result["findings"])

def test_invalid_snapshot():
    result = build_authorization_retention_monitor(
        [{"registry_policy_version": "phase116-v1", "sequence": 1}],
        expected_count=1, observed_at="2026-10-04T12:05:00+00:00")
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "INVALID_SNAPSHOT" for x in result["findings"])

def test_count_and_registry_policy_mismatch():
    first = _snapshot(1)
    result = build_authorization_retention_monitor(
        [{"registry_policy_version": "wrong", **first}],
        expected_count=2, observed_at="2026-10-04T12:05:00+00:00")
    codes = {x["code"] for x in result["findings"]}
    assert result["state"] == "CONTROL_REQUIRED"
    assert "REGISTRY_COUNT_MISMATCH" in codes
    assert "REGISTRY_POLICY_MISMATCH" in codes

def test_execution_gate_violation():
    first = _snapshot(1)
    tampered = dict(first)
    tampered["decisions"] = [dict(first["decisions"][0], execution_performed=True)]
    result = build_authorization_retention_monitor(
        [{"registry_policy_version": "phase116-v1", **tampered}],
        expected_count=1, observed_at="2026-10-04T12:05:00+00:00")
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "INVALID_SNAPSHOT" for x in result["findings"])

def test_registry_monitor_is_read_only():
    with tempfile.TemporaryDirectory() as directory:
        registry = RecoveryAuthorizationHistoryRegistry(f"{directory}/history.db")
        result = build_authorization_retention_monitor(registry.list(), expected_count=0, observed_at="2026-10-04T12:05:00+00:00")
        assert result["state"] == "NO_HISTORY"
