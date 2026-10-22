from __future__ import annotations

import pytest
from fastapi import HTTPException

from nema_agora import api


def _configure_storage(monkeypatch, path):
    monkeypatch.setenv("PLATFORM_API_KEY", "test-platform-key")
    monkeypatch.setenv("NEMA_CASE_DATABASE_PATH", str(path))
    monkeypatch.setenv("NEMA_CASE_STORAGE_DURABLE", "true")


def _case(case_id="NEMA-TEST-001"):
    return {
        "case_id": case_id,
        "district_or_site": "Synthetic Pilot Site",
        "category": "Water pollution",
        "severity": "Moderate",
        "status": "Received",
        "observation_date": "2026-10-22",
        "description": "Synthetic test record only.",
        "source": "automated_test",
        "reporter_reference": "synthetic",
        "latitude": None,
        "longitude": None,
    }


def test_case_api_authentication_fails_closed(monkeypatch):
    monkeypatch.delenv("PLATFORM_API_KEY", raising=False)
    with pytest.raises(HTTPException) as missing:
        api._require_nema_api_key(x_api_key="anything")
    assert missing.value.status_code == 503

    monkeypatch.setenv("PLATFORM_API_KEY", "expected-key")
    with pytest.raises(HTTPException) as wrong:
        api._require_nema_api_key(x_api_key="wrong-key")
    assert wrong.value.status_code == 401

    assert api._require_nema_api_key(x_api_key="expected-key") is True


def test_case_api_rejects_unconfirmed_or_ephemeral_storage(monkeypatch, tmp_path):
    monkeypatch.setenv("NEMA_CASE_DATABASE_PATH", str(tmp_path / "cases.sqlite3"))
    monkeypatch.setenv("NEMA_CASE_STORAGE_DURABLE", "false")
    with pytest.raises(HTTPException) as not_confirmed:
        api._database_path()
    assert not_confirmed.value.status_code == 503

    monkeypatch.setenv("NEMA_CASE_DATABASE_PATH", "/tmp/nema-cases.sqlite3")
    monkeypatch.setenv("NEMA_CASE_STORAGE_DURABLE", "true")
    with pytest.raises(HTTPException) as ephemeral:
        api._database_path()
    assert ephemeral.value.status_code == 503


def test_case_api_lists_and_reads_persisted_records_read_only(monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path / "nema-cases.sqlite3")
    from nema_agora.repository import NemaCaseRepository

    repository = NemaCaseRepository(tmp_path / "nema-cases.sqlite3")
    try:
        repository.create_case(
            _case(), actor="test-suite", created_at="2026-10-22T12:00:00+00:00"
        )
    finally:
        repository.close()

    listed = api.list_cases(limit=10, _auth=True)
    assert listed["count"] == 1
    assert listed["mode"] == "read_only"
    assert listed["items"][0]["record"]["case_id"] == "NEMA-TEST-001"

    retrieved = api.get_case("NEMA-TEST-001", _auth=True)
    assert retrieved["record"]["case_id"] == "NEMA-TEST-001"
    assert retrieved["version"] == 1
    assert retrieved["audit"][0]["event_type"] == "case_created"
    assert retrieved["mode"] == "read_only"


def test_storage_readiness_does_not_create_missing_database(monkeypatch, tmp_path):
    missing_db = tmp_path / "missing.sqlite3"
    _configure_storage(monkeypatch, missing_db)

    with pytest.raises(HTTPException) as missing:
        api.storage_readiness(_auth=True)

    assert missing.value.status_code == 503
    assert missing.value.detail["reason"] == "database_file_missing"
    assert not missing_db.exists()


def test_storage_readiness_checks_integrity_without_claiming_durability(monkeypatch, tmp_path):
    from nema_agora.repository import NemaCaseRepository

    database = tmp_path / "nema-cases.sqlite3"
    _configure_storage(monkeypatch, database)
    repository = NemaCaseRepository(database)
    repository.close()

    readiness = api.storage_readiness(_auth=True)
    assert readiness["status"] == "configured"
    assert readiness["sqlite_integrity"] == "ok"
    assert readiness["required_schema_present"] is True
    assert readiness["durability_flag_configured"] is True
    assert readiness["storage_durability_verified"] is False
    assert readiness["production_writes_enabled"] is False


def test_supabase_backend_readiness_uses_read_only_adapter(monkeypatch):
    monkeypatch.setenv("NEMA_CASE_STORAGE_BACKEND", "supabase_postgres")

    class FakeRemoteRepository:
        closed = False

        def storage_readiness(self):
            return {
                "status": "configured",
                "storage_backend": "supabase_postgres",
                "database_reachable": True,
                "required_schema_present": True,
                "storage_durability_verified": False,
                "production_writes_enabled": False,
            }

        def close(self):
            self.closed = True

    from nema_agora import supabase_repository
    fake = FakeRemoteRepository()
    monkeypatch.setattr(supabase_repository, "SupabaseReadOnlyNemaRepository", lambda: fake)

    result = api.storage_readiness(_auth=True)
    assert result["storage_backend"] == "supabase_postgres"
    assert result["database_reachable"] is True
    assert result["storage_durability_verified"] is False
    assert result["production_writes_enabled"] is False
    assert fake.closed is True


def test_unknown_storage_backend_fails_closed(monkeypatch):
    monkeypatch.setenv("NEMA_CASE_STORAGE_BACKEND", "unknown_backend")
    with pytest.raises(HTTPException) as error:
        api.storage_readiness(_auth=True)
    assert error.value.status_code == 503


def test_case_api_does_not_expose_a_write_route():
    route_shapes = {(route.path, tuple(sorted(route.methods or []))) for route in api.router.routes}
    assert ("/api/v1/nema/cases", ("GET",)) in route_shapes
    assert ("/api/v1/nema/cases/storage-readiness", ("GET",)) in route_shapes
    assert ("/api/v1/nema/cases/{case_id}", ("GET",)) in route_shapes
    assert not any(
        "POST" in methods or "PUT" in methods or "PATCH" in methods or "DELETE" in methods
        for _, methods in route_shapes
    )
