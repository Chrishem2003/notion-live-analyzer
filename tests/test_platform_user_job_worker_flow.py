"""Cross-layer contract tests for user-scoped job submission and worker processing.

These tests exercise the actual user API and worker entry points against an
in-memory repository double. PostgreSQL lifecycle/concurrency behavior is
covered separately by the disposable-database integration workflow.
"""
from __future__ import annotations

from copy import deepcopy

from platform_jobs import user_api, worker


class InMemoryJobRepository:
    """Small repository double shared by the API and worker in one test."""

    rows: dict[str, dict] = {}
    closed = 0

    def __init__(self):
        pass

    @classmethod
    def reset(cls):
        cls.rows = {}
        cls.closed = 0

    def reserve_user_quota(self, *, tenant_id, idempotency_key, limit=20, window_seconds=3600):
        return True

    def enqueue(self, *, idempotency_key, job_type, payload, max_attempts=3,
                tenant_id="platform-service", requested_by="trusted-service-api"):
        for row in self.rows.values():
            if row["tenant_id"] == tenant_id and row["idempotency_key"] == idempotency_key:
                return {key: row[key] for key in ("job_id", "status", "created_at")}
        job_id = f"job-{len(self.rows) + 1}"
        row = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "requested_by": requested_by,
            "idempotency_key": idempotency_key,
            "job_type": job_type,
            "payload": deepcopy(payload),
            "status": "queued",
            "attempt_count": 1,
            "max_attempts": max_attempts,
            "created_at": "2026-10-25T00:00:00Z",
        }
        self.rows[job_id] = row
        return {key: row[key] for key in ("job_id", "status", "created_at")}

    def claim(self, lease_seconds=120):
        for row in self.rows.values():
            if row["status"] == "queued":
                row["status"] = "running"
                return deepcopy(row)
        return None

    def finish(self, job_id, result):
        row = self.rows.get(job_id)
        if not row or row["status"] != "running":
            return False
        row["status"] = "completed"
        row["result_json"] = deepcopy(result)
        return True

    def fail(self, job_id, error_code, retry_delay_seconds=30):
        row = self.rows.get(job_id)
        if not row or row["status"] != "running":
            return False
        row["error_code"] = error_code
        row["status"] = "queued" if row["attempt_count"] < row["max_attempts"] else "failed"
        return True

    def close(self):
        type(self).closed += 1


def setup_function():
    InMemoryJobRepository.reset()


def test_user_submission_flows_through_worker_and_persists_result(monkeypatch):
    monkeypatch.setenv("PLATFORM_JOB_WORKER_ENABLED", "true")
    owner = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setattr(user_api, "SupabaseJobRepository", InMemoryJobRepository)
    monkeypatch.setattr(worker, "SupabaseJobRepository", InMemoryJobRepository)
    monkeypatch.setattr(
        worker, "_execute",
        lambda job: {"answer": f"processed: {job['payload']['prompt']}", "provider": "test"},
    )

    submitted = user_api.create_user_job(
        user_api.UserJobCreateRequest(prompt="analyze my data", strategy="direct"),
        idempotency_key="flow-test-1",
        user={"id": owner, "email": "user@example.com"},
    )
    assert submitted["status"] == "queued"
    job_id = submitted["job_id"]
    assert InMemoryJobRepository.rows[job_id]["tenant_id"] == owner

    outcome = worker.run_once()

    assert outcome == "succeeded"
    stored = InMemoryJobRepository.rows[job_id]
    assert stored["status"] == "completed"
    assert stored["result_json"]["answer"] == "processed: analyze my data"
    assert InMemoryJobRepository.closed == 2


def test_worker_failure_is_recorded_without_exposing_exception_text(monkeypatch):
    monkeypatch.setenv("PLATFORM_JOB_WORKER_ENABLED", "true")
    owner = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setattr(user_api, "SupabaseJobRepository", InMemoryJobRepository)
    monkeypatch.setattr(worker, "SupabaseJobRepository", InMemoryJobRepository)

    submitted = user_api.create_user_job(
        user_api.UserJobCreateRequest(prompt="trigger a controlled failure", max_attempts=1),
        idempotency_key="flow-test-failure",
        user={"id": owner, "email": "user@example.com"},
    )
    job_id = submitted["job_id"]

    def fail_execution(_job):
        raise RuntimeError("sensitive provider response must not be stored")

    monkeypatch.setattr(worker, "_execute", fail_execution)
    outcome = worker.run_once()

    assert outcome == "failed"
    stored = InMemoryJobRepository.rows[job_id]
    assert stored["status"] == "failed"
    assert stored["error_code"] == "RuntimeError"
    assert "sensitive provider response" not in str(stored)
