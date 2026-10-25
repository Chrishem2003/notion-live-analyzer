from __future__ import annotations

import pytest

from platform_jobs.api import JobCreateRequest
from platform_jobs.repository import JobConflict, JobStoreUnavailable, SupabaseJobRepository


def test_job_payload_fingerprint_is_stable_and_content_sensitive():
    left = {"prompt": "hello", "provider": None}
    right = {"provider": None, "prompt": "hello"}
    assert SupabaseJobRepository.fingerprint(left) == SupabaseJobRepository.fingerprint(right)
    assert SupabaseJobRepository.fingerprint(left) != SupabaseJobRepository.fingerprint({"prompt": "changed"})


def test_job_create_request_bounds_payload_and_rejects_blank_prompt():
    with pytest.raises(ValueError):
        JobCreateRequest(prompt="   ")
    with pytest.raises(Exception):
        JobCreateRequest(prompt="x" * 12001)


def test_job_create_request_defaults_to_allowlisted_job_type():
    request = JobCreateRequest(prompt="explain a dataset")
    assert request.job_type == "intelligence.solve"
    assert request.max_attempts == 3


def test_job_repository_fails_closed_without_server_credentials(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(JobStoreUnavailable):
        SupabaseJobRepository()


def test_worker_does_not_accept_arbitrary_job_types():
    from platform_jobs.worker import _execute
    with pytest.raises(ValueError, match="unsupported_job_type"):
        _execute({"job_type": "execute.python", "payload": {"code": "print(1)"}})


def test_idempotency_key_rejects_postgrest_filter_syntax():
    # Validate at the boundary so the key cannot alter PostgREST filter syntax.
    import os
    from unittest.mock import patch
    from platform_jobs.repository import SupabaseJobRepository

    with patch.dict(os.environ, {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "test-key"}):
        repo = SupabaseJobRepository()
        try:
            with pytest.raises(ValueError, match="Idempotency key"):
                repo.enqueue(idempotency_key="bad,key", job_type="intelligence.solve", payload={"prompt": "x"})
        finally:
            repo.close()

def _fake_response(rows):
    from unittest.mock import Mock
    response = Mock()
    response.status_code = 200
    response.content = b"[]" if rows is None else b"[{}]"
    response.json.return_value = rows
    response.raise_for_status.return_value = None
    return response


def test_repository_scopes_job_reads_to_requested_tenant(monkeypatch):
    import os
    from unittest.mock import Mock, patch
    tenant_id = "11111111-1111-4111-8111-111111111111"
    session = Mock()
    session.request.return_value = _fake_response([{"job_id": "job"}])
    with patch.dict(os.environ, {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "server-only-test-key",
    }):
        repo = SupabaseJobRepository(session=session)
        try:
            result = repo.get_job("22222222-2222-4222-8222-222222222222", tenant_id=tenant_id)
        finally:
            repo.close()
    assert result == {"job_id": "job"}
    assert session.request.call_args.kwargs["params"]["tenant_id"] == f"eq.{tenant_id}"


def test_repository_scopes_idempotency_recovery_to_tenant():
    import os
    from unittest.mock import Mock, patch
    tenant_id = "11111111-1111-4111-8111-111111111111"
    session = Mock()
    # Simulate an insert conflict followed by a tenant-scoped idempotency lookup.
    first = Mock(status_code=409, content=b'{"code":"23505"}')
    first.raise_for_status.side_effect = __import__("requests").HTTPError("conflict")
    second = _fake_response([{
        "job_id": "22222222-2222-4222-8222-222222222222",
        "status": "queued",
        "payload_hash": SupabaseJobRepository.fingerprint({"job_type": "intelligence.solve", "payload": {"prompt": "x"}}),
        "created_at": "2026-10-25T00:00:00Z",
    }])
    session.request.side_effect = [first, second]
    with patch.dict(os.environ, {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "server-only-test-key",
    }):
        repo = SupabaseJobRepository(session=session)
        try:
            result = repo.enqueue(
                idempotency_key="request-1", job_type="intelligence.solve",
                payload={"prompt": "x"}, tenant_id=tenant_id, requested_by=tenant_id,
            )
        finally:
            repo.close()
    assert result["job_id"] == "22222222-2222-4222-8222-222222222222"
    assert session.request.call_args_list[1].kwargs["params"]["tenant_id"] == f"eq.{tenant_id}"



def test_repository_quota_reservation_calls_atomic_rpc_and_returns_boolean():
    from unittest.mock import Mock, patch

    session = Mock()
    response = _fake_response(True)
    session.request.return_value = response
    tenant_id = "11111111-1111-4111-8111-111111111111"
    with patch.dict("os.environ", {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "server-only-test-key",
    }):
        repo = SupabaseJobRepository(session=session)
        try:
            allowed = repo.reserve_user_quota(
                tenant_id=tenant_id, idempotency_key="req-1", limit=20, window_seconds=3600,
            )
        finally:
            repo.close()

    assert allowed is True
    call = session.request.call_args
    assert call.args[0] == "POST"
    assert call.args[1].endswith("/rest/v1/rpc/reserve_user_job_quota")
    assert call.kwargs["json"] == {
        "p_tenant_id": tenant_id,
        "p_idempotency_key": "req-1",
        "p_limit": 20,
        "p_window_seconds": 3600,
    }


def test_worker_bounds_large_intelligence_answers(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import patch
    from sovereign_intelligence.api import service_router

    huge_answer = "A" * 50000
    brain = Mock()
    brain.solve_governed.return_value = SimpleNamespace(
        answer=huge_answer, provider="test-provider", model="test-model",
        verification=None, assessment=None, control=None,
    )
    monkeypatch.setattr(service_router, "_get_brain", lambda: brain)

    from platform_jobs.worker import _execute
    result = _execute({
        "job_type": "intelligence.solve",
        "payload": {"prompt": "summarize safely"},
    })

    assert len(result["answer"]) < 40100
    assert result["answer"].startswith("A" * 100)
    assert "Output truncated by platform storage limit" in result["answer"]
    brain.solve_governed.assert_called_once()


def test_worker_rejects_empty_or_non_text_intelligence_answers(monkeypatch):
    from types import SimpleNamespace
    from sovereign_intelligence.api import service_router

    for answer in ("  ", None, {"unexpected": "object"}):
        brain = Mock()
        brain.solve_governed.return_value = SimpleNamespace(
            answer=answer, provider="test-provider", model="test-model",
            verification=None, assessment=None, control=None,
        )
        monkeypatch.setattr(service_router, "_get_brain", lambda brain=brain: brain)
        from platform_jobs.worker import _execute
        with pytest.raises(ValueError, match="invalid_intelligence_result"):
            _execute({
                "job_type": "intelligence.solve",
                "payload": {"prompt": "test"},
            })


def test_repository_cancellation_uses_tenant_scoped_atomic_rpc():
    import os
    from unittest.mock import Mock, patch

    tenant_id = "11111111-1111-4111-8111-111111111111"
    job_id = "22222222-2222-4222-8222-222222222222"
    session = Mock()
    response = _fake_response("cancelled")
    session.request.return_value = response
    with patch.dict(os.environ, {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "server-only-test-key",
    }):
        repo = SupabaseJobRepository(session=session)
        try:
            result = repo.cancel_user_job(job_id=job_id, tenant_id=tenant_id)
        finally:
            repo.close()

    assert result == "cancelled"
    call = session.request.call_args
    assert call.args[0] == "POST"
    assert call.args[1].endswith("/rest/v1/rpc/cancel_user_platform_job")
    assert call.kwargs["json"] == {"p_job_id": job_id, "p_tenant_id": tenant_id}


def test_repository_rejects_unknown_cancellation_rpc_response():
    import os
    from unittest.mock import Mock, patch
    from platform_jobs.repository import JobStoreUnavailable

    session = Mock()
    session.request.return_value = _fake_response("some_other_state")
    with patch.dict(os.environ, {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "server-only-test-key",
    }):
        repo = SupabaseJobRepository(session=session)
        try:
            with pytest.raises(JobStoreUnavailable, match="cancellation service"):
                repo.cancel_user_job(
                    job_id="22222222-2222-4222-8222-222222222222",
                    tenant_id="11111111-1111-4111-8111-111111111111",
                )
        finally:
            repo.close()



def test_worker_does_not_resurrect_or_fail_job_when_completion_is_rejected(monkeypatch):
    from unittest.mock import Mock
    from platform_jobs import worker

    repo = Mock()
    repo.claim.return_value = {
        "job_id": "22222222-2222-4222-8222-222222222222",
        "job_type": "intelligence.solve",
        "payload": {"prompt": "test"},
        "attempt_count": 1,
    }
    repo.finish.return_value = False
    repo.close = Mock()
    monkeypatch.setattr(worker, "SupabaseJobRepository", lambda: repo)
    monkeypatch.setattr(worker, "_execute", lambda _job: {"answer": "late response"})

    assert worker.run_once() == "completion_rejected"
    repo.finish.assert_called_once_with("22222222-2222-4222-8222-222222222222", {"answer": "late response"})
    repo.fail.assert_not_called()
    repo.close.assert_called_once()


def test_user_job_status_projection_never_selects_private_prompt_payload():
    import os
    from unittest.mock import Mock, patch

    session = Mock()
    session.request.return_value = _fake_response([])
    with patch.dict(os.environ, {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "server-only-test-key",
    }):
        repo = SupabaseJobRepository(session=session)
        try:
            repo.get_job(
                "22222222-2222-4222-8222-222222222222",
                tenant_id="11111111-1111-4111-8111-111111111111",
            )
        finally:
            repo.close()

    selected = session.request.call_args.kwargs["params"]["select"]
    assert "payload" not in selected.split(",")
    assert "result_json" in selected.split(",")
    assert session.request.call_args.kwargs["params"]["tenant_id"] == "eq.11111111-1111-4111-8111-111111111111"
