from __future__ import annotations

from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

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


def test_supabase_auth_network_outage_returns_retryable_service_error(monkeypatch):
    monkeypatch.setenv("USER_JOB_API_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "public-test-key")
    monkeypatch.setattr(
        user_api.requests,
        "get",
        Mock(side_effect=user_api.requests.RequestException("connection reset")),
    )

    with pytest.raises(HTTPException) as error:
        user_api._verified_user("Bearer valid-token")

    assert error.value.status_code == 503
    assert "temporarily unavailable" in error.value.detail


@pytest.mark.parametrize("status_code", [429, 500, 502, 503])
def test_supabase_auth_server_outage_returns_retryable_service_error(monkeypatch, status_code):
    monkeypatch.setenv("USER_JOB_API_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "public-test-key")
    monkeypatch.setattr(
        user_api.requests,
        "get",
        Mock(return_value=Mock(status_code=status_code)),
    )

    with pytest.raises(HTTPException) as error:
        user_api._verified_user("Bearer valid-token")

    assert error.value.status_code == 503


@pytest.mark.parametrize("field", ["tenant_id", "requested_by", "role", "is_admin"])
def test_user_job_request_rejects_client_supplied_identity_fields(field):
    with pytest.raises(ValidationError):
        user_api.UserJobCreateRequest(prompt="build a workflow", **{field: "attacker-controlled"})


@pytest.mark.parametrize("field", ["provider", "model", "strategy"])
def test_user_job_request_rejects_blank_routing_values(field):
    with pytest.raises(ValidationError):
        user_api.UserJobCreateRequest(prompt="build a workflow", **{field: "   "})


def test_two_user_job_isolation_does_not_disclose_other_users_jobs(monkeypatch):
    user_a = "11111111-1111-4111-8111-111111111111"
    user_b = "22222222-2222-4222-8222-222222222222"
    job_id = "33333333-3333-4333-8333-333333333333"
    rows_by_owner = {
        (user_b, job_id): {
            "job_id": job_id,
            "tenant_id": user_b,
            "status": "completed",
            "result_json": {"answer": "private result for B"},
        }
    }
    repo = Mock()
    repo.get_job.side_effect = lambda requested_job, *, tenant_id: rows_by_owner.get((tenant_id, requested_job))
    repo.close = Mock()
    monkeypatch.setattr(user_api, "SupabaseJobRepository", lambda: repo)

    # User A requests User B's job: the same not-found response used for unknown jobs.
    with pytest.raises(HTTPException) as error:
        user_api.get_user_job(job_id, user={"id": user_a, "email": "a@example.com"})
    assert error.value.status_code == 404
    assert error.value.detail == "Job not found."

    # The actual owner can retrieve that job.
    result = user_api.get_user_job(job_id, user={"id": user_b, "email": "b@example.com"})
    assert result["result_json"]["answer"] == "private result for B"
    assert repo.get_job.call_args_list[0].kwargs["tenant_id"] == user_a
    assert repo.get_job.call_args_list[1].kwargs["tenant_id"] == user_b
    assert repo.close.call_count == 2


def test_quota_retry_is_scoped_to_same_user_and_idempotency_key(monkeypatch):
    user_a = "11111111-1111-4111-8111-111111111111"
    user_b = "22222222-2222-4222-8222-222222222222"
    repo = Mock()
    repo.reserve_user_quota.return_value = True
    repo.enqueue.side_effect = [
        {"job_id": "33333333-3333-4333-8333-333333333333", "status": "queued"},
        {"job_id": "33333333-3333-4333-8333-333333333333", "status": "queued"},
        {"job_id": "44444444-4444-4444-8444-444444444444", "status": "queued"},
    ]
    repo.close = Mock()
    monkeypatch.setattr(user_api, "SupabaseJobRepository", lambda: repo)

    for user_id in (user_a, user_a, user_b):
        user_api.create_user_job(
            user_api.UserJobCreateRequest(prompt="generate a safe workflow"),
            idempotency_key="same-client-key",
            user={"id": user_id, "email": ""},
        )

    # The same key can be retried for the same account, but never shares quota identity across accounts.
    calls = repo.reserve_user_quota.call_args_list
    assert calls[0].kwargs["tenant_id"] == user_a
    assert calls[1].kwargs["tenant_id"] == user_a
    assert calls[2].kwargs["tenant_id"] == user_b
    assert all(call.kwargs["idempotency_key"] == "same-client-key" for call in calls)
    assert repo.enqueue.call_args_list[0].kwargs["tenant_id"] == user_a
    assert repo.enqueue.call_args_list[1].kwargs["tenant_id"] == user_a
    assert repo.enqueue.call_args_list[2].kwargs["tenant_id"] == user_b
    assert repo.close.call_count == 3


@pytest.mark.parametrize(
    ("outcome", "expected_status"),
    [("cancelled", 200), ("not_found", 404), ("not_cancellable", 409)],
)
def test_user_job_cancellation_maps_atomic_store_outcome(monkeypatch, outcome, expected_status):
    user_id = "11111111-1111-4111-8111-111111111111"
    job_id = "33333333-3333-4333-8333-333333333333"
    repo = Mock()
    repo.cancel_user_job.return_value = outcome
    repo.close = Mock()
    monkeypatch.setattr(user_api, "SupabaseJobRepository", lambda: repo)

    if expected_status == 200:
        result = user_api.cancel_user_job(job_id, user={"id": user_id, "email": ""})
        assert result == {"job_id": job_id, "status": "cancelled"}
    else:
        with pytest.raises(HTTPException) as error:
            user_api.cancel_user_job(job_id, user={"id": user_id, "email": ""})
        assert error.value.status_code == expected_status
        if expected_status == 404:
            assert error.value.detail == "Job not found."

    repo.cancel_user_job.assert_called_once_with(job_id=job_id, tenant_id=user_id)
    repo.close.assert_called_once()


def test_user_job_cancellation_rejects_invalid_uuid_before_store_access(monkeypatch):
    repo = Mock()
    repo.close = Mock()
    monkeypatch.setattr(user_api, "SupabaseJobRepository", lambda: repo)
    with pytest.raises(HTTPException) as error:
        user_api.cancel_user_job("not-a-uuid", user={"id": "11111111-1111-4111-8111-111111111111", "email": ""})
    assert error.value.status_code == 422
    repo.cancel_user_job.assert_not_called()



def test_user_can_cancel_only_their_own_job(monkeypatch):
    user_id = "11111111-1111-4111-8111-111111111111"
    job_id = "22222222-2222-4222-8222-222222222222"
    repo = Mock()
    repo.cancel_user_job.return_value = "cancelled"
    repo.close = Mock()
    monkeypatch.setattr(user_api, "SupabaseJobRepository", lambda: repo)

    result = user_api.cancel_user_job(job_id, user={"id": user_id, "email": "user@example.com"})

    assert result == {"job_id": job_id, "status": "cancelled"}
    repo.cancel_user_job.assert_called_once_with(job_id=job_id, tenant_id=user_id)
    repo.close.assert_called_once()


@pytest.mark.parametrize(("outcome", "status_code"), [("not_found", 404), ("not_cancellable", 409)])
def test_user_job_cancel_maps_safe_database_outcomes(monkeypatch, outcome, status_code):
    repo = Mock()
    repo.cancel_user_job.return_value = outcome
    repo.close = Mock()
    monkeypatch.setattr(user_api, "SupabaseJobRepository", lambda: repo)

    with pytest.raises(HTTPException) as error:
        user_api.cancel_user_job(
            "22222222-2222-4222-8222-222222222222",
            user={"id": "11111111-1111-4111-8111-111111111111", "email": ""},
        )

    assert error.value.status_code == status_code
    if status_code == 404:
        assert error.value.detail == "Job not found."
    repo.close.assert_called_once()


def test_user_job_cancel_rejects_invalid_uuid_before_store_access(monkeypatch):
    repo_factory = Mock()
    monkeypatch.setattr(user_api, "SupabaseJobRepository", repo_factory)

    with pytest.raises(HTTPException) as error:
        user_api.cancel_user_job("not-a-uuid", user={"id": "11111111-1111-4111-8111-111111111111", "email": ""})

    assert error.value.status_code == 422
    repo_factory.assert_not_called()


def test_user_job_cancel_fails_closed_when_database_unavailable(monkeypatch):
    repo = Mock()
    repo.cancel_user_job.side_effect = user_api.JobStoreUnavailable("unavailable")
    repo.close = Mock()
    monkeypatch.setattr(user_api, "SupabaseJobRepository", lambda: repo)

    with pytest.raises(HTTPException) as error:
        user_api.cancel_user_job(
            "22222222-2222-4222-8222-222222222222",
            user={"id": "11111111-1111-4111-8111-111111111111", "email": ""},
        )

    assert error.value.status_code == 503
    repo.close.assert_called_once()


def test_invalid_idempotency_key_is_rejected_before_quota_reservation(monkeypatch):
    repo_factory = Mock()
    monkeypatch.setattr(user_api, "SupabaseJobRepository", repo_factory)
    with pytest.raises(HTTPException) as error:
        user_api.create_user_job(
            user_api.UserJobCreateRequest(prompt="analyze"),
            idempotency_key="../invalid",
            user={"id": "11111111-1111-4111-8111-111111111111", "email": ""},
        )
    assert error.value.status_code == 422
    repo_factory.assert_not_called()
