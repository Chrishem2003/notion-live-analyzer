from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest
import requests

from modules.platform_job_ledger import PlatformJobLedger, PlatformLedgerConflict, PlatformLedgerUnavailable


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses=None, error=None):
        self.headers = {}
        self.responses = list(responses or [])
        self.error = error
        self.calls = []
        self.closed = False

    def post(self, url, *, json, timeout):
        self.calls.append((url, json, timeout))
        if self.error:
            raise self.error
        return FakeResponse(self.responses.pop(0))

    def close(self):
        self.closed = True


def configure(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://demo-project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "synthetic-secret")


def test_requires_https_and_server_credential(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://demo-project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "synthetic-secret")
    with pytest.raises(PlatformLedgerUnavailable):
        PlatformJobLedger(session=FakeSession())
    monkeypatch.setenv("SUPABASE_URL", "https://demo-project.supabase.co")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(PlatformLedgerUnavailable):
        PlatformJobLedger(session=FakeSession())


@pytest.mark.parametrize("url", [
    "https://user:password@demo-project.supabase.co",
    "https://demo-project.supabase.co/rest/v1",
    "https://demo-project.supabase.co?apikey=should-not-be-here",
    "https://demo-project.supabase.co#fragment",
    "https://localhost",
    "https://demo-project.supabase.co:invalid",
])
def test_rejects_database_urls_with_credentials_or_non_root_components(monkeypatch, url):
    monkeypatch.setenv("SUPABASE_URL", url)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "synthetic-secret")
    with pytest.raises(PlatformLedgerUnavailable):
        PlatformJobLedger(session=FakeSession())


def test_enqueue_hashes_canonical_payload_and_sends_server_auth(monkeypatch):
    configure(monkeypatch)
    session = FakeSession([{
        "job_id": "00000000-0000-0000-0000-000000000001",
        "status": "queued", "created": True, "attempt_count": 0,
    }])
    ledger = PlatformJobLedger(session=session)
    result = ledger.enqueue(job_type="demo.validate", actor_scope="service:test",
                            idempotency_key="request-1", payload={"b": 2, "a": 1})
    sent = session.calls[0][1]
    expected = hashlib.sha256(json.dumps(
        {"job_type": "demo.validate", "max_attempts": 3, "payload": {"a": 1, "b": 2}},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()).hexdigest()
    assert sent["p_request_hash"] == expected
    assert result["status"] == "queued"
    assert session.headers["Authorization"] == "Bearer synthetic-secret"
    assert session.calls[0][2] == 5.0


def test_claim_and_finish_validate_contracts(monkeypatch):
    configure(monkeypatch)
    session = FakeSession([
        {"job_id": "job-1", "job_type": "demo.validate", "payload": {"safe": True},
         "attempt_count": 1, "max_attempts": 3, "lease_token": "lease-1"},
        {"job_id": "job-1", "status": "succeeded"},
    ])
    ledger = PlatformJobLedger(session=session)
    claimed = ledger.claim(worker_id="worker-test")
    assert claimed["lease_token"] == "lease-1"
    finished = ledger.finish(job_id="job-1", worker_id="worker-test", lease_token="lease-1",
                             status="succeeded", result={"checked": True})
    assert finished["status"] == "succeeded"
    assert session.calls[1][1]["p_status"] == "succeeded"


def test_status_is_actor_scoped_and_does_not_expose_payload_or_lease(monkeypatch):
    configure(monkeypatch)
    session = FakeSession([{
        "job_id": "job-1", "status": "succeeded", "attempt_count": 1,
        "max_attempts": 3, "result": {"checked": True}, "error": None,
    }])
    ledger = PlatformJobLedger(session=session)
    status = ledger.get_status(job_id="job-1", actor_scope="service:test")
    assert status["status"] == "succeeded"
    assert "payload" not in status and "lease_token" not in status
    assert session.calls[0][1] == {
        "p_job_id": "job-1", "p_actor_scope": "service:test"
    }


def test_status_rejects_unsafe_or_invalid_response(monkeypatch):
    configure(monkeypatch)
    ledger = PlatformJobLedger(session=FakeSession([{
        "job_id": "job-1", "status": "succeeded", "payload": {"secret": True}
    }]))
    with pytest.raises(PlatformLedgerUnavailable):
        ledger.get_status(job_id="job-1", actor_scope="service:test")


def test_claim_rejects_invalid_lease_before_network_call(monkeypatch):
    configure(monkeypatch)
    session = FakeSession([])
    ledger = PlatformJobLedger(session=session)
    with pytest.raises(ValueError):
        ledger.claim(worker_id="worker-test", lease_seconds=True)
    with pytest.raises(ValueError):
        ledger.claim(worker_id=" " * 201)
    assert session.calls == []


def test_empty_queue_returns_none(monkeypatch):
    configure(monkeypatch)
    ledger = PlatformJobLedger(session=FakeSession([None]))
    assert ledger.claim(worker_id="worker-test") is None


def test_rejects_non_object_and_non_json_payload(monkeypatch):
    configure(monkeypatch)
    ledger = PlatformJobLedger(session=FakeSession([{}]))
    with pytest.raises(ValueError):
        ledger.request_hash(["not", "an", "object"])
    with pytest.raises(ValueError):
        ledger.request_hash({"bad": object()})


def test_enforce_job_metadata_and_json_size_limits(monkeypatch):
    configure(monkeypatch)
    ledger = PlatformJobLedger(session=FakeSession([{
        "job_id": "job-1", "status": "queued", "created": True, "attempt_count": 0,
    }]))
    with pytest.raises(ValueError):
        ledger.enqueue(job_type=" " * 121, actor_scope="service:test",
                       idempotency_key="request-1", payload={})
    with pytest.raises(ValueError):
        ledger.enqueue(job_type="demo.validate", actor_scope="service:test",
                       idempotency_key="request-1", payload={}, max_attempts=True)
    with pytest.raises(ValueError):
        ledger.request_hash({"oversized": "x" * (PlatformJobLedger.MAX_JSON_BYTES + 1)})


def test_finish_rejects_oversized_result_before_network_call(monkeypatch):
    configure(monkeypatch)
    session = FakeSession([])
    ledger = PlatformJobLedger(session=session)
    with pytest.raises(ValueError):
        ledger.finish(job_id="job-1", worker_id="worker-test", lease_token="lease-1",
                      status="succeeded", result={"large": "x" * PlatformJobLedger.MAX_JSON_BYTES})
    assert session.calls == []


def test_transport_errors_are_redacted(monkeypatch):
    configure(monkeypatch)
    ledger = PlatformJobLedger(session=FakeSession(error=requests.Timeout("sensitive host and token")))
    with pytest.raises(PlatformLedgerUnavailable) as caught:
        ledger.claim(worker_id="worker-test")
    assert "sensitive host" not in str(caught.value)
    assert "synthetic-secret" not in str(caught.value)


def test_idempotency_conflict_is_distinguished_from_service_unavailable(monkeypatch):
    configure(monkeypatch)
    error = requests.HTTPError("conflict", response=SimpleNamespace(status_code=409))
    ledger = PlatformJobLedger(session=FakeSession(error=error))
    with pytest.raises(PlatformLedgerConflict):
        ledger.enqueue(
            job_type="platform.synthetic.validate",
            actor_scope="service:test",
            idempotency_key="same-key",
            payload={"different": True},
        )


def test_closes_session(monkeypatch):
    configure(monkeypatch)
    session = FakeSession([None])
    ledger = PlatformJobLedger(session=session)
    ledger.close()
    assert session.closed



def test_reserve_dispatches_validates_limit_and_returns_job_ids(monkeypatch):
    configure(monkeypatch)
    session = FakeSession([[
        {"job_id": "00000000-0000-0000-0000-000000000123"}
    ]])
    ledger = PlatformJobLedger(session=session)
    assert ledger.reserve_dispatches(limit=10) == ["00000000-0000-0000-0000-000000000123"]
    assert session.calls[0][1] == {"p_limit": 10}
    with pytest.raises(ValueError):
        ledger.reserve_dispatches(limit=True)
    with pytest.raises(ValueError):
        ledger.reserve_dispatches(limit=101)


def test_reserve_dispatches_rejects_invalid_response(monkeypatch):
    configure(monkeypatch)
    ledger = PlatformJobLedger(session=FakeSession([[{"job_id": "not-a-uuid"}]]))
    with pytest.raises(PlatformLedgerUnavailable):
        ledger.reserve_dispatches()


def test_get_metrics_accepts_aggregate_only_response(monkeypatch):
    configure(monkeypatch)
    expected = {
        "total": 5, "queued": 1, "running": 1, "succeeded": 1,
        "failed": 1, "needs_review": 1, "expired_leases": 0,
        "oldest_queued_age_seconds": 42, "created_last_24h": 4,
        "finished_last_24h": 3, "sampled_at": "2026-10-23T10:00:00+00:00",
    }
    session = FakeSession([expected])
    ledger = PlatformJobLedger(session=session)
    assert ledger.get_metrics() == expected
    assert session.calls[0][0].endswith("/rpc/platform_get_job_metrics")
    assert session.calls[0][1] == {}


@pytest.mark.parametrize("patch", [
    {"queued": -1},
    {"failed": True},
    {"total": 99},
    {"expired_leases": 2},
    {"unexpected_sensitive_field": "payload"},
    {"sampled_at": ""},
])
def test_get_metrics_rejects_invalid_or_unsafe_response(monkeypatch, patch):
    configure(monkeypatch)
    response = {
        "total": 1, "queued": 1, "running": 0, "succeeded": 0,
        "failed": 0, "needs_review": 0, "expired_leases": 0,
        "oldest_queued_age_seconds": 0, "created_last_24h": 1,
        "finished_last_24h": 0, "sampled_at": "2026-10-23T10:00:00+00:00",
    }
    response.update(patch)
    ledger = PlatformJobLedger(session=FakeSession([response]))
    with pytest.raises(PlatformLedgerUnavailable):
        ledger.get_metrics()
