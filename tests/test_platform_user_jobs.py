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

def test_user_job_read_is_scoped_to_verified_user_uuid(monkeypatch):
    user_id = "11111111-1111-4111-8111-111111111111"
    repo = Mock()
    repo.get_job.return_value = None
    repo.close = Mock()
    monkeypatch.setattr(user_api, "SupabaseJobRepository", lambda: repo)

    with pytest.raises(HTTPException) as error:
        user_api.get_user_job(
            "22222222-2222-4222-8222-222222222222",
            user={"id": user_id, "email": "user@example.com"},
        )

    assert error.value.status_code == 404
    repo.get_job.assert_called_once_with(
        "22222222-2222-4222-8222-222222222222", tenant_id=user_id
    )
    repo.close.assert_called_once()


def test_user_job_creation_sets_owner_from_verified_identity(monkeypatch):
    user_id = "11111111-1111-4111-8111-111111111111"
    repo = Mock()
    repo.reserve_user_quota.return_value = True
    repo.enqueue.return_value = {
        "job_id": "33333333-3333-4333-8333-333333333333",
        "status": "queued",
        "created_at": "2026-10-25T00:00:00Z",
    }
    repo.close = Mock()
    monkeypatch.setattr(user_api, "SupabaseJobRepository", lambda: repo)

    result = user_api.create_user_job(
        user_api.UserJobCreateRequest(prompt="summarize my dataset"),
        idempotency_key="request-1",
        user={"id": user_id, "email": "user@example.com"},
    )

    assert result["mode"] == "user_scoped"
    assert repo.enqueue.call_args.kwargs["tenant_id"] == user_id
    assert repo.enqueue.call_args.kwargs["requested_by"] == user_id
    repo.close.assert_called_once()



def test_user_job_quota_exhaustion_rejects_before_enqueue(monkeypatch):
    user_id = "11111111-1111-4111-8111-111111111111"
    repo = Mock()
    repo.reserve_user_quota.return_value = False
    repo.close = Mock()
    monkeypatch.setattr(user_api, "SupabaseJobRepository", lambda: repo)

    with pytest.raises(HTTPException) as error:
        user_api.create_user_job(
            user_api.UserJobCreateRequest(prompt="build a workflow"),
            idempotency_key="quota-test",
            user={"id": user_id, "email": "user@example.com"},
        )

    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "3600"
    repo.enqueue.assert_not_called()
    repo.close.assert_called_once()


def test_user_job_quota_store_failure_fails_closed(monkeypatch):
    user_id = "11111111-1111-4111-8111-111111111111"
    repo = Mock()
    repo.reserve_user_quota.side_effect = user_api.JobStoreUnavailable("not available")
    repo.close = Mock()
    monkeypatch.setattr(user_api, "SupabaseJobRepository", lambda: repo)

    with pytest.raises(HTTPException) as error:
        user_api.create_user_job(
            user_api.UserJobCreateRequest(prompt="build a workflow"),
            idempotency_key="quota-store-down",
            user={"id": user_id, "email": "user@example.com"},
        )

    assert error.value.status_code == 503
    repo.enqueue.assert_not_called()
    repo.close.assert_called_once()


def test_invalid_quota_configuration_fails_closed(monkeypatch):
    monkeypatch.setenv("USER_JOB_QUOTA_PER_HOUR", "not-a-number")
    with pytest.raises(user_api.JobStoreUnavailable):
        user_api._quota_limit()


def test_quota_configuration_is_bounded(monkeypatch):
    monkeypatch.setenv("USER_JOB_QUOTA_PER_HOUR", "1001")
    with pytest.raises(user_api.JobStoreUnavailable):
        user_api._quota_limit()
