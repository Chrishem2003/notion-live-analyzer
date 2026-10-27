from __future__ import annotations

import pytest

from nema_agora.supabase_repository import (
    NemaStorageUnavailableError,
    SupabaseReadOnlyNemaRepository,
)


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class Session:
    def __init__(self, payload):
        self.headers = {}
        self.payload = payload
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return Response(self.payload)


@pytest.fixture
def configured_repo(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    session = Session([])
    repo = SupabaseReadOnlyNemaRepository(session=session)
    return repo, session


def test_measurement_read_is_scoped_to_measured_status_and_bounded(configured_repo):
    repo, session = configured_repo
    session.payload = [{
        "measurement_id": "m-1", "indicator_id": "ENV-ALERT-001",
        "status": "measured", "created_at": "2026-10-27T10:00:00Z",
    }]
    rows = repo.list_indicator_measurements(limit=20, status="measured", indicator_id="ENV-ALERT-001")
    assert rows == session.payload
    assert session.calls[0]["url"].endswith("/rest/v1/nema_indicator_measurements")
    assert session.calls[0]["params"]["status"] == "eq.measured"
    assert session.calls[0]["params"]["indicator_id"] == "eq.ENV-ALERT-001"
    assert session.calls[0]["params"]["limit"] == "20"
    assert "created_at.desc" in session.calls[0]["params"]["order"]


def test_measurement_status_and_limit_validation(configured_repo):
    repo, _ = configured_repo
    with pytest.raises(ValueError, match="Unsupported measurement status"):
        repo.list_indicator_measurements(status="unreviewed")
    with pytest.raises(ValueError, match="Limit"):
        repo.list_indicator_measurements(limit=True)


def test_measurement_audit_query_is_bound_to_exact_measurement(configured_repo):
    repo, session = configured_repo
    session.payload = [{
        "audit_id": "m-1:submitted", "measurement_id": "m-1",
        "actor_id": "submitter", "actor_role": "submitter",
        "action": "measurement_submitted", "created_at": "2026-10-27T10:00:00Z",
    }]
    rows = repo.list_measurement_audit_events("m-1")
    assert rows == session.payload
    assert session.calls[0]["url"].endswith("/rest/v1/nema_measurement_audit")
    assert session.calls[0]["params"]["measurement_id"] == "eq.m-1"
    assert session.calls[0]["params"]["order"] == "created_at.asc,audit_id.asc"


def test_audit_row_for_another_measurement_is_rejected(configured_repo):
    repo, session = configured_repo
    session.payload = [{
        "audit_id": "wrong", "measurement_id": "m-other",
        "actor_id": "x", "actor_role": "reviewer",
        "action": "measurement_submitted", "created_at": "2026-10-27T10:00:00Z",
    }]
    with pytest.raises(NemaStorageUnavailableError, match="different measurement"):
        repo.list_measurement_audit_events("m-1")


def test_audit_reader_rejects_incomplete_rows(configured_repo):
    repo, session = configured_repo
    session.payload = [{"audit_id": "m-1:submitted", "measurement_id": "m-1"}]
    with pytest.raises(NemaStorageUnavailableError, match="incomplete event"):
        repo.list_measurement_audit_events("m-1")
