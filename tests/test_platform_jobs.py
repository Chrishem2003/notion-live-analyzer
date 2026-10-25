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
