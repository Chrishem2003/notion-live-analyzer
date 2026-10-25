"""HTTP contract tests for the feature-gated durable platform job API.

All ledger and Celery interactions are mocked; no external service is contacted.
"""
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("PLATFORM_API_KEY", "test-platform-key")
    monkeypatch.setenv("PLATFORM_JOB_LEDGER_ENABLED", "false")
    monkeypatch.delenv("PLATFORM_JOB_ACTOR_SCOPE", raising=False)
    import api_server
    api_server = importlib.reload(api_server)
    api_server.API_KEY = "test-platform-key"
    return api_server, TestClient(api_server.app)


def headers():
    return {"X-API-Key": "test-platform-key"}


def test_platform_jobs_are_disabled_by_default(api, monkeypatch):
    _, client = api
    monkeypatch.setenv("PLATFORM_JOB_LEDGER_ENABLED", "false")
    response = client.post(
        "/api/v1/platform-jobs",
        headers={**headers(), "Idempotency-Key": "disabled-test"},
        json={"job_type": "platform.synthetic.validate", "payload": {"safe": True}},
    )
    assert response.status_code == 503
    assert "disabled" in response.json()["detail"].lower()


def test_platform_job_endpoint_requires_api_key(api):
    _, client = api
    response = client.post(
        "/api/v1/platform-jobs",
        headers={"Idempotency-Key": "missing-auth"},
        json={"job_type": "platform.synthetic.validate", "payload": {}},
    )
    assert response.status_code in (401, 403)


@pytest.mark.parametrize("body", [
    {"job_type": "notion.write_real_record", "payload": {}},
    {"job_type": "platform.synthetic.validate", "payload": [], "max_attempts": 3},
    {"job_type": "platform.synthetic.validate", "payload": {}, "max_attempts": 0},
    {"job_type": "platform.synthetic.validate", "payload": {"bad": float("nan")}},
])
def test_platform_job_request_rejects_unsupported_or_invalid_payload(api, monkeypatch, body):
    _, client = api
    monkeypatch.setenv("PLATFORM_JOB_LEDGER_ENABLED", "true")
    response = client.post(
        "/api/v1/platform-jobs",
        headers={**headers(), "Idempotency-Key": "invalid-test"},
        json=body,
    )
    assert response.status_code == 422


def test_enqueue_requires_idempotency_key(api, monkeypatch):
    _, client = api
    monkeypatch.setenv("PLATFORM_JOB_LEDGER_ENABLED", "true")
    response = client.post(
        "/api/v1/platform-jobs",
        headers=headers(),
        json={"job_type": "platform.synthetic.validate", "payload": {}},
    )
    assert response.status_code == 400


def test_enqueue_uses_server_actor_scope_and_dispatches_synthetic_task(api, monkeypatch):
    api_server, client = api
    monkeypatch.setenv("PLATFORM_JOB_LEDGER_ENABLED", "true")
    monkeypatch.setenv("PLATFORM_JOB_ACTOR_SCOPE", "service:api-test")
    captured = {}
    dispatches = []

    class FakeLedger:
        def __init__(self):
            self.closed = False

        def enqueue(self, **kwargs):
            captured.update(kwargs)
            return {
                "job_id": "00000000-0000-0000-0000-000000000123",
                "status": "queued",
                "created": True,
            }

        def close(self):
            self.closed = True

    import modules.platform_job_ledger as ledger_module
    fake_ledger = FakeLedger()
    monkeypatch.setattr(ledger_module, "PlatformJobLedger", lambda: fake_ledger)
    monkeypatch.setattr(
        api_server.celery_app, "send_task",
        lambda name: dispatches.append(name),
    )

    response = client.post(
        "/api/v1/platform-jobs",
        headers={**headers(), "Idempotency-Key": "api-test-1"},
        json={"job_type": "platform.synthetic.validate", "payload": {"synthetic": True}},
    )

    assert response.status_code == 202
    assert response.json()["job_id"] == "00000000-0000-0000-0000-000000000123"
    assert captured["actor_scope"] == "service:api-test"
    assert captured["idempotency_key"] == "api-test-1"
    assert captured["job_type"] == "platform.synthetic.validate"
    assert dispatches == ["tasks.process_platform_ledger_job"]
    assert fake_ledger.closed


def test_enqueue_never_accepts_actor_scope_from_request_body(api, monkeypatch):
    _, client = api
    monkeypatch.setenv("PLATFORM_JOB_LEDGER_ENABLED", "true")
    monkeypatch.delenv("PLATFORM_JOB_ACTOR_SCOPE", raising=False)
    response = client.post(
        "/api/v1/platform-jobs",
        headers={**headers(), "Idempotency-Key": "actor-scope-test"},
        json={
            "job_type": "platform.synthetic.validate",
            "payload": {},
            "actor_scope": "attacker:chosen-scope",
        },
    )
    assert response.status_code == 503
    assert "actor scope" in response.json()["detail"].lower()

def test_metrics_endpoint_is_feature_gated_and_authenticated(api, monkeypatch):
    _, client = api
    disabled = client.get("/api/v1/platform-jobs/metrics", headers=headers())
    assert disabled.status_code == 503
    assert "disabled" in disabled.json()["detail"].lower()

    monkeypatch.setenv("PLATFORM_JOB_LEDGER_ENABLED", "true")
    unauthenticated = client.get("/api/v1/platform-jobs/metrics")
    assert unauthenticated.status_code in (401, 403)


def test_metrics_endpoint_returns_only_aggregate_counts_and_closes_ledger(api, monkeypatch):
    api_server, client = api
    monkeypatch.setenv("PLATFORM_JOB_LEDGER_ENABLED", "true")
    expected = {
        "total": 2, "queued": 1, "running": 0, "succeeded": 1,
        "failed": 0, "needs_review": 0, "expired_leases": 0,
        "oldest_queued_age_seconds": 4, "created_last_24h": 2,
        "finished_last_24h": 1, "sampled_at": "2026-10-23T12:00:00Z",
    }
    state = {"closed": False}

    class FakeLedger:
        def get_metrics(self):
            return expected

        def close(self):
            state["closed"] = True

    import modules.platform_job_ledger as ledger_module
    monkeypatch.setattr(ledger_module, "PlatformJobLedger", FakeLedger)

    response = client.get("/api/v1/platform-jobs/metrics", headers=headers())
    assert response.status_code == 200
    assert response.json() == expected
    assert not ({"job_id", "actor_scope", "payload", "lease_token", "error"} & set(response.json()))
    assert state["closed"]


def test_metrics_endpoint_fails_closed_when_ledger_is_unavailable(api, monkeypatch):
    _, client = api
    monkeypatch.setenv("PLATFORM_JOB_LEDGER_ENABLED", "true")
    import modules.platform_job_ledger as ledger_module

    class BrokenLedger:
        def __init__(self):
            self.closed = False

        def get_metrics(self):
            raise ledger_module.PlatformLedgerUnavailable("safe failure")

        def close(self):
            self.closed = True

    instance = BrokenLedger()
    monkeypatch.setattr(ledger_module, "PlatformJobLedger", lambda: instance)
    response = client.get("/api/v1/platform-jobs/metrics", headers=headers())
    assert response.status_code == 503
    assert response.json()["detail"] == "safe failure"
    assert instance.closed

def test_status_requires_server_actor_scope_before_opening_database(api, monkeypatch):
    _, client = api
    monkeypatch.setenv("PLATFORM_JOB_LEDGER_ENABLED", "true")
    monkeypatch.delenv("PLATFORM_JOB_ACTOR_SCOPE", raising=False)

    import modules.platform_job_ledger as ledger_module

    def forbidden_database_init():
        raise AssertionError("database client must not be initialized without actor scope")

    monkeypatch.setattr(ledger_module, "PlatformJobLedger", forbidden_database_init)
    response = client.get(
        "/api/v1/platform-jobs/00000000-0000-0000-0000-000000000123",
        headers=headers(),
    )
    assert response.status_code == 503
    assert "actor scope" in response.json()["detail"].lower()

