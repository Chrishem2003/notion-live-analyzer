from __future__ import annotations

from unittest.mock import Mock

import pytest

from platform_jobs.repository import JobStoreUnavailable, SupabaseJobRepository


USER_A = "11111111-1111-4111-8111-111111111111"
USER_B = "22222222-2222-4222-8222-222222222222"


def _repo():
    repo = object.__new__(SupabaseJobRepository)
    repo._request = Mock()
    return repo


def test_enqueue_persists_verified_tenant_and_requester():
    repo = _repo()
    repo._request.return_value = [{"job_id": "job-1", "status": "queued", "created_at": "now"}]

    repo.enqueue(
        idempotency_key="request-1",
        job_type="intelligence.solve",
        payload={"prompt": "analyze"},
        tenant_id=USER_A,
        requested_by=USER_A,
    )

    body = repo._request.call_args.kwargs["json"]
    assert body["tenant_id"] == USER_A
    assert body["requested_by"] == USER_A


def test_enqueue_idempotency_lookup_is_scoped_to_same_tenant():
    repo = _repo()
    repo._request.side_effect = [
        JobStoreUnavailable("insert conflict"),
        [{"job_id": "job-a", "status": "queued", "payload_hash": repo.fingerprint({
            "job_type": "intelligence.solve", "payload": {"prompt": "analyze"}
        }), "created_at": "now"}],
    ]

    result = repo.enqueue(
        idempotency_key="same-key",
        job_type="intelligence.solve",
        payload={"prompt": "analyze"},
        tenant_id=USER_A,
        requested_by=USER_A,
    )

    assert result["job_id"] == "job-a"
    assert repo._request.call_args_list[1].kwargs["params"]["tenant_id"] == f"eq.{USER_A}"


def test_job_read_is_scoped_to_tenant():
    repo = _repo()
    repo._request.return_value = []
    assert repo.get_job("job-1", tenant_id=USER_B) is None
    assert repo._request.call_args.kwargs["params"]["tenant_id"] == f"eq.{USER_B}"


def test_quota_reservation_uses_atomic_user_scoped_rpc():
    repo = _repo()
    repo._request.return_value = True
    assert repo.reserve_user_quota(tenant_id=USER_A, idempotency_key="key-1") is True
    assert repo._request.call_args.args == ("POST", "rpc/reserve_user_job_quota")
    assert repo._request.call_args.kwargs["json"]["p_tenant_id"] == USER_A


def test_quota_reservation_fails_closed_on_invalid_rpc_result():
    repo = _repo()
    repo._request.return_value = {"allowed": True}
    with pytest.raises(JobStoreUnavailable):
        repo.reserve_user_quota(tenant_id=USER_A, idempotency_key="key-1")


def test_quota_reservation_rejects_non_uuid_tenant_before_rpc():
    repo = _repo()
    with pytest.raises(ValueError):
        repo.reserve_user_quota(tenant_id="platform-service", idempotency_key="key-1")
    repo._request.assert_not_called()


@pytest.mark.parametrize("outcome", ["cancelled", "not_found", "not_cancellable"])
def test_cancellation_maps_atomic_rpc_outcomes(outcome):
    repo = _repo()
    repo._request.return_value = outcome
    assert repo.cancel_user_job(job_id=USER_A, tenant_id=USER_B) == outcome
    assert repo._request.call_args.args == ("POST", "rpc/cancel_user_platform_job")
    assert repo._request.call_args.kwargs["json"] == {
        "p_job_id": USER_A,
        "p_tenant_id": USER_B,
    }


def test_cancellation_fails_closed_on_unknown_rpc_result():
    repo = _repo()
    repo._request.return_value = {"status": "cancelled"}
    with pytest.raises(JobStoreUnavailable):
        repo.cancel_user_job(job_id=USER_A, tenant_id=USER_B)


def test_job_history_query_is_tenant_scoped_and_bounded():
    repo = _repo()
    repo._request.return_value = []
    assert repo.list_user_jobs(tenant_id=USER_A, limit=10) == []
    params = repo._request.call_args.kwargs["params"]
    assert params["tenant_id"] == f"eq.{USER_A}"
    assert params["limit"] == "10"
    assert "payload" not in params["select"]
    assert "result_json" not in params["select"]


def test_job_history_rejects_invalid_tenant_and_limit_before_query():
    repo = _repo()
    with pytest.raises(ValueError):
        repo.list_user_jobs(tenant_id="platform-service", limit=20)
    with pytest.raises(ValueError):
        repo.list_user_jobs(tenant_id=USER_A, limit=51)
    repo._request.assert_not_called()
