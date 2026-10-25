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
