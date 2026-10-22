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




def test_dispatch_reconciler_is_gated_and_closes_ledger(monkeypatch):
    ledger = FakeWorkerLedger()
    reservations = ["job-1", "job-2"]
    dispatches = []
    monkeypatch.setenv("PLATFORM_JOB_LEDGER_ENABLED", "false")
    monkeypatch.setattr(ledger_tasks, "PlatformJobLedger", lambda: ledger)
    disabled = ledger_tasks.reconcile_platform_ledger_dispatches.run()
    assert disabled == {"enabled": False, "reserved": 0, "dispatched": 0}
    assert not ledger.closed

    monkeypatch.setenv("PLATFORM_JOB_LEDGER_ENABLED", "true")
    monkeypatch.setattr(ledger, "reserve_dispatches", lambda *, limit: reservations)
    monkeypatch.setattr(ledger_tasks.celery_app, "send_task", lambda name: dispatches.append(name))
    result = ledger_tasks.reconcile_platform_ledger_dispatches.run()
    assert result == {
        "enabled": True, "reserved": 2, "dispatched": 2, "dispatch_incomplete": False
    }
    assert dispatches == [
        "tasks.process_platform_ledger_job", "tasks.process_platform_ledger_job"
    ]
    assert ledger.closed


def test_dispatch_reconciler_reports_broker_failure_without_leaking_details(monkeypatch):
    ledger = FakeWorkerLedger()
    monkeypatch.setenv("PLATFORM_JOB_LEDGER_ENABLED", "true")
    monkeypatch.setattr(ledger_tasks, "PlatformJobLedger", lambda: ledger)
    monkeypatch.setattr(ledger, "reserve_dispatches", lambda *, limit: ["job-1", "job-2"])

    def broker_failure(_name):
        raise RuntimeError("secret broker password")

    monkeypatch.setattr(ledger_tasks.celery_app, "send_task", broker_failure)
    result = ledger_tasks.reconcile_platform_ledger_dispatches.run()
    assert result == {
        "enabled": True, "reserved": 2, "dispatched": 0, "dispatch_incomplete": True
    }
    assert "secret broker password" not in str(result)
    assert ledger.closed
