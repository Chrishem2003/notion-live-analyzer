from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from nema_agora import api
from nema_agora.client import NemaApiError, get_review_packet


def _configure_sqlite(monkeypatch, path):
    monkeypatch.setenv("PLATFORM_API_KEY", "test-platform-key")
    monkeypatch.setenv("NEMA_CASE_STORAGE_BACKEND", "sqlite")
    monkeypatch.setenv("NEMA_CASE_DATABASE_PATH", str(path))
    monkeypatch.setenv("NEMA_CASE_STORAGE_DURABLE", "true")


def _case(case_id="NEMA-PREVIEW-001"):
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


def test_review_packet_endpoint_is_readonly_and_versioned(monkeypatch, tmp_path):
    database = tmp_path / "nema-cases.sqlite3"
    _configure_sqlite(monkeypatch, database)
    from nema_agora.repository import NemaCaseRepository

    repository = NemaCaseRepository(database)
    try:
        repository.create_case(
            _case(), actor="test-suite", created_at="2026-10-22T12:00:00+00:00"
        )
        before_audit = repository.list_audit_events("NEMA-PREVIEW-001", limit=100)
    finally:
        repository.close()

    packet = api.review_packet("NEMA-PREVIEW-001", _auth=True)
    assert packet["workflow"] == "nema.case_review_packet"
    assert packet["execution_mode"] == "preview_only"
    assert packet["review_status"] == "human_review_required"
    assert packet["record_version"] == 1
    assert packet["source_mode"] == "read_only"

    repository = NemaCaseRepository(database)
    try:
        record, version = repository.get_case("NEMA-PREVIEW-001")
        after_audit = repository.list_audit_events("NEMA-PREVIEW-001", limit=100)
        assert version == 1
        assert record == _case()
        assert len(after_audit) == len(before_audit)
    finally:
        repository.close()


def test_review_packet_endpoint_returns_404_for_missing_case(monkeypatch, tmp_path):
    _configure_sqlite(monkeypatch, tmp_path / "nema-cases.sqlite3")
    with pytest.raises(HTTPException) as missing:
        api.review_packet("missing-case", _auth=True)
    assert missing.value.status_code == 404


def test_review_packet_route_is_get_only_and_authenticated():
    route = next(
        route for route in api.router.routes
        if route.path == "/api/v1/nema/cases/{case_id}/review-packet"
    )
    assert route.methods == {"GET"}
    assert any(
        dependency.call.__name__ == "_require_nema_api_key"
        for dependency in route.dependant.dependencies
    )


@patch.dict("os.environ", {
    "NEMA_CASE_API_BASE_URL": "https://api.example.test",
    "PLATFORM_API_KEY": "test-secret",
})
@patch("nema_agora.client.requests.get")
def test_client_calls_review_preview_with_server_side_auth_and_timeout(mock_get):
    response = Mock()
    response.ok = True
    response.status_code = 200
    response.json.return_value = {
        "workflow": "nema.case_review_packet",
        "execution_mode": "preview_only",
        "review_status": "human_review_required",
    }
    mock_get.return_value = response

    result = get_review_packet("NEMA-PREVIEW-001")

    assert result["execution_mode"] == "preview_only"
    args, kwargs = mock_get.call_args
    assert args[0] == "https://api.example.test/api/v1/nema/cases/NEMA-PREVIEW-001/review-packet"
    assert kwargs["headers"]["X-API-Key"] == "test-secret"
    assert kwargs["timeout"] == (3.05, 12)


def test_client_rejects_invalid_review_case_id_before_request():
    with pytest.raises(ValueError):
        get_review_packet(" ")


@patch.dict("os.environ", {
    "NEMA_CASE_API_BASE_URL": "https://api.example.test",
    "PLATFORM_API_KEY": "test-secret",
})
@patch("nema_agora.client.requests.get")
def test_client_uses_safe_error_for_missing_review_packet(mock_get):
    response = Mock()
    response.ok = False
    response.status_code = 404
    mock_get.return_value = response
    with pytest.raises(NemaApiError, match="not found"):
        get_review_packet("missing-case")
