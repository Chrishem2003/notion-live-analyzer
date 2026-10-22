from __future__ import annotations

import json
import sqlite3

import pytest

from modules.governed_automation_runtime import (
    AutomationAuthorizationError,
    AutomationConflictError,
    GovernedAutomationRuntime,
    WorkflowSpec,
)


def _validator(inputs):
    if set(inputs) != {"value"} or not isinstance(inputs["value"], int) or isinstance(inputs["value"], bool):
        raise ValueError("value must be an integer")


@pytest.fixture
def runtime(tmp_path):
    engine = GovernedAutomationRuntime(
        tmp_path / "automation" / "jobs.sqlite3",
        authorize=lambda actor, workflow: actor == "operator-1" and workflow.startswith("test."),
    )
    yield engine
    engine.close()


def test_executes_allowlisted_workflow_and_writes_audit(runtime):
    runtime.register(WorkflowSpec("test.double", lambda data: {"result": data["value"] * 2}, _validator))
    result = runtime.execute(
        "test.double", {"value": 21}, actor="operator-1", idempotency_key="job-001"
    )
    assert result["status"] == "succeeded"
    assert result["output"] == {"result": 42}
    assert result["attempts"] == 1
    audit = runtime.list_audit(result["job_id"], actor="operator-1")
    assert [event["event_type"] for event in audit] == ["job_started", "job_succeeded"]


def test_missing_authorizer_and_denied_actor_fail_closed(tmp_path):
    no_auth = GovernedAutomationRuntime(":memory:", authorize=None)
    no_auth.register(WorkflowSpec("test.noop", lambda data: {}, lambda data: None))
    with pytest.raises(AutomationAuthorizationError):
        no_auth.execute("test.noop", {}, actor="operator", idempotency_key="a")
    no_auth.close()

    denied = GovernedAutomationRuntime(":memory:", authorize=lambda actor, workflow: False)
    denied.register(WorkflowSpec("test.noop", lambda data: {}, lambda data: None))
    with pytest.raises(AutomationAuthorizationError):
        denied.execute("test.noop", {}, actor="operator", idempotency_key="b")
    denied.close()


def test_duplicate_idempotency_key_replays_without_running_twice(runtime):
    calls = []
    runtime.register(WorkflowSpec("test.count", lambda data: calls.append(data["value"]) or {"ok": True}, _validator))
    first = runtime.execute("test.count", {"value": 1}, actor="operator-1", idempotency_key="same")
    second = runtime.execute("test.count", {"value": 1}, actor="operator-1", idempotency_key="same")
    assert first["job_id"] == second["job_id"]
    assert second["replayed"] is True
    assert len(calls) == 1


def test_reusing_idempotency_key_for_different_inputs_conflicts(runtime):
    runtime.register(WorkflowSpec("test.echo", lambda data: data, _validator))
    runtime.execute("test.echo", {"value": 1}, actor="operator-1", idempotency_key="same")
    with pytest.raises(AutomationConflictError, match="different workflow inputs"):
        runtime.execute("test.echo", {"value": 2}, actor="operator-1", idempotency_key="same")


def test_non_idempotent_workflow_cannot_configure_retries():
    with pytest.raises(ValueError, match="Non-idempotent"):
        WorkflowSpec("test.unsafe", lambda data: {}, lambda data: None, idempotent=False, max_attempts=2)


def test_idempotent_workflow_retries_and_clears_transient_error(runtime):
    calls = []
    def flaky(data):
        calls.append(data)
        if len(calls) == 1:
            raise RuntimeError("sensitive exception detail should not be stored")
        return {"ok": True}

    runtime.register(WorkflowSpec("test.flaky", flaky, _validator, idempotent=True, max_attempts=2))
    result = runtime.execute("test.flaky", {"value": 4}, actor="operator-1", idempotency_key="retry")
    assert result["status"] == "succeeded"
    assert result["attempts"] == 2
    assert result["error_code"] is None
    assert len(calls) == 2
    assert "sensitive exception detail" not in json.dumps(result)


def test_failed_workflow_stores_only_exception_type(runtime):
    def fail(data):
        raise RuntimeError("secret-token-should-not-leak")
    runtime.register(WorkflowSpec("test.fail", fail, _validator))
    result = runtime.execute("test.fail", {"value": 3}, actor="operator-1", idempotency_key="fail")
    assert result["status"] == "failed"
    assert result["error_code"] == "RuntimeError"
    assert "secret-token-should-not-leak" not in json.dumps(result)


def test_invalid_input_never_creates_a_job(runtime):
    runtime.register(WorkflowSpec("test.validate", lambda data: data, _validator))
    with pytest.raises(ValueError, match="value must be an integer"):
        runtime.execute("test.validate", {"value": True}, actor="operator-1", idempotency_key="bad")
    assert runtime._db.execute("SELECT COUNT(*) FROM automation_jobs").fetchone()[0] == 0


def test_output_bound_is_enforced_and_failure_is_recorded(runtime):
    runtime.register(WorkflowSpec("test.large", lambda data: {"text": "x" * 270_000}, _validator))
    result = runtime.execute("test.large", {"value": 1}, actor="operator-1", idempotency_key="large")
    assert result["status"] == "failed"
    assert result["error_code"] == "ValueError"
    assert len(runtime.list_audit(result["job_id"], actor="operator-1")) == 2


def test_audit_events_are_append_only(runtime):
    runtime.register(WorkflowSpec("test.echo", lambda data: data, _validator))
    result = runtime.execute("test.echo", {"value": 7}, actor="operator-1", idempotency_key="audit")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        runtime._db.execute("DELETE FROM automation_audit WHERE job_id=?", (result["job_id"],))


def test_job_and_audit_survive_reopening_database(tmp_path):
    path = tmp_path / "state" / "jobs.sqlite3"
    first = GovernedAutomationRuntime(path, authorize=lambda actor, workflow: actor == "operator-1")
    first.register(WorkflowSpec("test.echo", lambda data: data, _validator))
    result = first.execute("test.echo", {"value": 9}, actor="operator-1", idempotency_key="persist")
    job_id = result["job_id"]
    first.close()

    second = GovernedAutomationRuntime(path, authorize=lambda actor, workflow: actor == "operator-1")
    try:
        recovered = second.get_job(job_id, actor="operator-1")
        assert recovered["status"] == "succeeded"
        assert recovered["output"] == {"value": 9}
        assert len(second.list_audit(job_id, actor="operator-1")) == 2
    finally:
        second.close()


def _insert_stuck_job(runtime, *, job_id="stuck-job", key="stuck-key"):
    import hashlib
    from datetime import datetime, timezone

    inputs = json.dumps({"value": 5}, sort_keys=True, separators=(",", ":"))
    now = datetime.now(timezone.utc).isoformat()
    runtime._db.execute(
        """INSERT INTO automation_jobs
        (job_id,idempotency_key,workflow_name,input_hash,input_json,status,actor,attempts,created_at,updated_at)
        VALUES (?,?,?,?,?,'running',?,0,?,?)""",
        (job_id, key, "test.stuck", hashlib.sha256(inputs.encode()).hexdigest(), inputs,
         "operator-1", now, now),
    )
    runtime._audit(job_id, "job_started", {
        "job_id": job_id, "workflow_name": "test.stuck", "actor": "operator-1",
        "input_hash": hashlib.sha256(inputs.encode()).hexdigest(), "status": "running",
    }, now)


def test_manual_recovery_requires_explicit_no_side_effect_confirmation(runtime):
    _insert_stuck_job(runtime)
    with pytest.raises(ValueError, match="confirm that no side effect"):
        runtime.resolve_stuck_job_as_failed(
            "stuck-job", actor="operator-1", reason="checked logs", resolution="unknown"
        )
    assert runtime.get_job("stuck-job", actor="operator-1")["status"] == "running"


def test_manual_recovery_is_authorized_audited_and_blocks_blind_replay(runtime):
    _insert_stuck_job(runtime)
    calls = []
    runtime.register(WorkflowSpec("test.stuck", lambda data: calls.append(data) or {"ok": True}, _validator))
    resolved = runtime.resolve_stuck_job_as_failed(
        "stuck-job", actor="operator-1", reason="Checked provider logs and confirmed no request was accepted.",
        resolution="confirmed_no_side_effect",
    )
    assert resolved["status"] == "failed"
    assert resolved["error_code"] == "ManualRecoveryConfirmedNoSideEffect"
    events = runtime.list_audit("stuck-job", actor="operator-1")
    assert events[-1]["event_type"] == "job_manually_reconciled_failed"
    assert events[-1]["resolution"] == "confirmed_no_side_effect"
    assert "confirmed no request was accepted" in events[-1]["reason"]

    replay = runtime.execute(
        "test.stuck", {"value": 5}, actor="operator-1", idempotency_key="stuck-key"
    )
    assert replay["status"] == "failed"
    assert replay["replayed"] is True
    assert calls == []


def test_manual_recovery_rejects_unauthorized_actor_and_terminal_jobs(runtime):
    _insert_stuck_job(runtime)
    with pytest.raises(AutomationAuthorizationError):
        runtime.resolve_stuck_job_as_failed(
            "stuck-job", actor="intruder", reason="attempt", resolution="confirmed_no_side_effect"
        )
    runtime.resolve_stuck_job_as_failed(
        "stuck-job", actor="operator-1", reason="verified no side effect", resolution="confirmed_no_side_effect"
    )
    with pytest.raises(AutomationConflictError, match="Only a running job"):
        runtime.resolve_stuck_job_as_failed(
            "stuck-job", actor="operator-1", reason="second attempt", resolution="confirmed_no_side_effect"
        )


def test_manual_recovery_redacts_credential_like_text_from_audit(runtime):
    _insert_stuck_job(runtime)
    runtime.resolve_stuck_job_as_failed(
        "stuck-job", actor="operator-1",
        reason="Checked logs token=secret-value Bearer abcdefghijklmnop",
        resolution="confirmed_no_side_effect",
    )
    audit_text = json.dumps(runtime.list_audit("stuck-job", actor="operator-1"))
    assert "secret-value" not in audit_text
    assert "abcdefghijklmnop" not in audit_text
    assert "[REDACTED]" in audit_text
