from __future__ import annotations

import pytest

import modules.platform_ledger_tasks as ledger_tasks
from modules.platform_ledger_tasks import _execute


class HashOnlyLedger:
    @staticmethod
    def request_hash(payload):
        return "synthetic-hash"


def test_synthetic_handler_does_not_echo_payload():
    result = _execute(
        "platform.synthetic.validate",
        {"private_note": "must not be echoed"},
        HashOnlyLedger(),
    )
    assert result == {
        "validated": True,
        "mode": "synthetic",
        "payload_sha256": "synthetic-hash",
    }
    assert "private_note" not in str(result)


def test_unregistered_job_types_are_rejected():
    with pytest.raises(ValueError, match="unsupported_job_type"):
        _execute("notion.write_real_record", {"x": 1}, HashOnlyLedger())


class FakeWorkerLedger:
    def __init__(self, finish_status="queued"):
        self.finish_status = finish_status
        self.closed = False
        self.finished = []

    def claim(self, *, worker_id, lease_seconds):
        return {
            "job_id": "job-123",
            "job_type": "platform.synthetic.validate",
            "payload": {"safe": True},
            "lease_token": "lease-123",
        }

    def finish(self, **kwargs):
        self.finished.append(kwargs)
        return {"job_id": kwargs["job_id"], "status": self.finish_status}

    def close(self):
        self.closed = True


def test_handler_failure_schedules_retry_when_ledger_requeues(monkeypatch):
    ledger = FakeWorkerLedger(finish_status="queued")
    dispatches = []
    monkeypatch.setattr(ledger_tasks, "PlatformJobLedger", lambda: ledger)
    monkeypatch.setattr(ledger_tasks, "_execute", lambda *args: (_ for _ in ()).throw(RuntimeError("sensitive")))
    monkeypatch.setattr(ledger_tasks.celery_app, "send_task", lambda name: dispatches.append(name))

    result = ledger_tasks.process_platform_ledger_job.run()

    assert result == {"processed": True, "status": "queued", "job_id": "job-123"}
    assert ledger.finished[0]["status"] == "failed"
    assert dispatches == ["tasks.process_platform_ledger_job"]
    assert ledger.closed


def test_exhausted_handler_failure_does_not_schedule_another_retry(monkeypatch):
    ledger = FakeWorkerLedger(finish_status="failed")
    dispatches = []
    monkeypatch.setattr(ledger_tasks, "PlatformJobLedger", lambda: ledger)
    monkeypatch.setattr(ledger_tasks, "_execute", lambda *args: (_ for _ in ()).throw(RuntimeError("sensitive")))
    monkeypatch.setattr(ledger_tasks.celery_app, "send_task", lambda name: dispatches.append(name))

    result = ledger_tasks.process_platform_ledger_job.run()

    assert result == {"processed": True, "status": "failed", "job_id": "job-123"}
    assert dispatches == []
    assert ledger.closed

