from __future__ import annotations

import requests
import pytest

from nema_agora import supabase_repository as remote


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payloads=None, error=None):
        self.headers = {}
        self.payloads = payloads or {}
        self.error = error
        self.calls = []
        self.closed = False

    def get(self, url, *, params, timeout):
        self.calls.append((url, params, timeout))
        if self.error:
            raise self.error
        return FakeResponse(self.payloads.get(url.rsplit("/", 1)[-1], []))

    def close(self):
        self.closed = True


def _configure(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example-project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "synthetic-test-key")


def test_remote_repository_requires_https_and_server_key(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://example-project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "synthetic-test-key")
    with pytest.raises(remote.NemaStorageUnavailableError):
        remote.SupabaseReadOnlyNemaRepository(session=FakeSession())

    monkeypatch.setenv("SUPABASE_URL", "https://example-project.supabase.co")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(remote.NemaStorageUnavailableError):
        remote.SupabaseReadOnlyNemaRepository(session=FakeSession())


def test_remote_repository_lists_and_reads_cases_and_audit(monkeypatch):
    _configure(monkeypatch)
    session = FakeSession(
        {
            "nema_cases": [
                {
                    "record_json": {"case_id": "NEMA-SYNTH-01", "status": "Received"},
                    "version": 2,
                }
            ],
            "nema_case_audit": [{"event_json": {"event_type": "case_created"}}],
        }
    )
    repository = remote.SupabaseReadOnlyNemaRepository(session=session)
    try:
        rows = repository.list_cases(limit=10)
        assert rows == [({"case_id": "NEMA-SYNTH-01", "status": "Received"}, 2)]
        found = repository.get_case("NEMA-SYNTH-01")
        assert found == ({"case_id": "NEMA-SYNTH-01", "status": "Received"}, 2)
        events = repository.list_audit_events("NEMA-SYNTH-01")
        assert events == [{"event_type": "case_created"}]
        assert session.headers["apikey"] == "synthetic-test-key"
        assert session.headers["Authorization"] == "Bearer synthetic-test-key"
    finally:
        repository.close()
    assert session.closed is True


def test_remote_repository_readiness_does_not_claim_durability(monkeypatch):
    _configure(monkeypatch)
    session = FakeSession()
    repository = remote.SupabaseReadOnlyNemaRepository(session=session)
    try:
        result = repository.storage_readiness()
        assert result["status"] == "configured"
        assert result["database_reachable"] is True
        assert result["required_schema_present"] is True
        assert result["storage_durability_verified"] is False
        assert result["production_writes_enabled"] is False
        assert len(session.calls) == 2
        assert all(call[2] <= 5.0 for call in session.calls)
    finally:
        repository.close()


def test_remote_repository_redacts_transport_errors(monkeypatch):
    _configure(monkeypatch)
    session = FakeSession(error=requests.Timeout("secret endpoint details"))
    repository = remote.SupabaseReadOnlyNemaRepository(session=session)
    try:
        with pytest.raises(remote.NemaStorageUnavailableError) as error:
            repository.list_cases()
        assert "secret endpoint details" not in str(error.value)
        assert "synthetic-test-key" not in str(error.value)
    finally:
        repository.close()
