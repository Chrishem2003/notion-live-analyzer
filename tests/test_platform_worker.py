from unittest.mock import MagicMock
from platform_jobs import worker

def _repo(job=None):
    repo = MagicMock()
    repo.claim.return_value = job
    repo.finish.return_value = True
    repo.fail.return_value = True
    return repo

def test_run_once_returns_idle_and_closes_repository(monkeypatch):
    repo = _repo()
    monkeypatch.setattr(worker, "SupabaseJobRepository", lambda: repo)
    assert worker.run_once() == "idle"
    repo.close.assert_called_once()

def test_run_once_executes_one_job_and_persists_result(monkeypatch):
    job = {"job_id": "job-1", "job_type": "intelligence.solve", "payload": {"prompt": "hello"}, "attempt_count": 1}
    repo = _repo(job)
    monkeypatch.setattr(worker, "SupabaseJobRepository", lambda: repo)
    monkeypatch.setattr(worker, "_execute", lambda _: {"answer": "hello"})
    assert worker.run_once() == "succeeded"
    repo.claim.assert_called_once_with(lease_seconds=900)
    repo.finish.assert_called_once_with("job-1", {"answer": "hello"})
    repo.close.assert_called_once()

def test_run_once_records_sanitized_failure(monkeypatch):
    job = {"job_id": "job-2", "job_type": "intelligence.solve", "payload": {"prompt": "private"}, "attempt_count": 2}
    repo = _repo(job)
    monkeypatch.setattr(worker, "SupabaseJobRepository", lambda: repo)
    def fail(_):
        raise RuntimeError("do not leak this")
    monkeypatch.setattr(worker, "_execute", fail)
    assert worker.run_once() == "failed"
    repo.fail.assert_called_once_with("job-2", "RuntimeError", retry_delay_seconds=60)
    repo.close.assert_called_once()

def test_run_once_reports_store_unavailable(monkeypatch):
    def unavailable():
        raise worker.JobStoreUnavailable("no store")
    monkeypatch.setattr(worker, "SupabaseJobRepository", unavailable)
    assert worker.run_once() == "unavailable"
