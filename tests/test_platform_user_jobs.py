from __future__ import annotations

from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from platform_jobs import user_api


def test_user_job_api_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("USER_JOB_API_ENABLED", raising=False)
    with pytest.raises(HTTPException) as error:
        user_api._verified_user("Bearer token")
    assert error.value.status_code == 503


def test_user_job_api_requires_bearer_token(monkeypatch):
    monkeypatch.setenv("USER_JOB_API_ENABLED", "true")
    with pytest.raises(HTTPException) as error:
        user_api._verified_user(None)
    assert error.value.status_code == 401


def test_verified_identity_is_taken_from_supabase_not_client_fields(monkeypatch):
    monkeypatch.setenv("USER_JOB_API_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "public-test-key")
    response = Mock(status_code=200)
    response.json.return_value = {
        "id": "11111111-1111-4111-8111-111111111111",
        "email": "user@example.com",
        "app_metadata": {"role": "admin"},
    }
    get = Mock(return_value=response)
    monkeypatch.setattr(user_api.requests, "get", get)

    identity = user_api._verified_user("Bearer valid-token")

    assert identity == {
        "id": "11111111-1111-4111-8111-111111111111",
        "email": "user@example.com",
    }
    assert get.call_args.kwargs["headers"]["Authorization"] == "Bearer valid-token"
    assert "service_role" not in str(get.call_args.kwargs["headers"]).lower()


def test_invalid_supabase_identity_uuid_is_rejected(monkeypatch):
    monkeypatch.setenv("USER_JOB_API_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "public-test-key")
    response = Mock(status_code=200)
    response.json.return_value = {"id": "not-a-uuid", "email": "user@example.com"}
    monkeypatch.setattr(user_api.requests, "get", Mock(return_value=response))

    with pytest.raises(HTTPException) as error:
        user_api._verified_user("Bearer valid-token")
    assert error.value.status_code == 401
