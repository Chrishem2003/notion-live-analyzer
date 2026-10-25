"""Celery worker for the durable platform ledger.

Only explicitly allow-listed, side-effect-free synthetic jobs are handled here.
Real research/Notion jobs must receive their own reviewed handler before they
are added to the dispatcher.
"""
from __future__ import annotations

import os
import socket
from typing import Any

from celery_app import celery_app
from modules.platform_job_ledger import PlatformJobLedger


def _worker_id() -> str:
    host = os.environ.get("PLATFORM_JOB_WORKER_ID", socket.gethostname()).strip()
    return (host or "platform-ledger-worker")[:200]


def _execute(job_type: str, payload: dict[str, Any], ledger: PlatformJobLedger) -> dict[str, Any]:
    """Execute one registered handler; never echo user payloads into logs/results."""
    if job_type == "platform.synthetic.validate":
        digest = ledger.request_hash(payload)
        return {"validated": True, "mode": "synthetic", "payload_sha256": digest}
    raise ValueError("unsupported_job_type")


@celery_app.task(name="tasks.process_platform_ledger_job", acks_late=True)
def process_platform_ledger_job() -> dict[str, Any]:
    """Claim and process at most one ledger job; lease recovery handles worker loss."""
    if os.environ.get("PLATFORM_JOB_LEDGER_ENABLED", "false").strip().lower() != "true":
        return {"processed": False, "reason": "ledger_disabled"}
    ledger = PlatformJobLedger()
    worker_id = _worker_id()
    try:
        job = ledger.claim(worker_id=worker_id, lease_seconds=120)
        if job is None:
            return {"processed": False, "reason": "queue_empty"}

        job_id = str(job["job_id"])
        lease_token = str(job["lease_token"])
        try:
            result = _execute(str(job["job_type"]), job["payload"], ledger)
        except ValueError as exc:
            ledger.finish(
                job_id=job_id, worker_id=worker_id, lease_token=lease_token,
                status="needs_review", error={"code": str(exc)[:120]},
            )
            return {"processed": True, "status": "needs_review", "job_id": job_id}
        except Exception:
            # Do not put exception text, tokens, or payloads into durable logs.
            finished = ledger.finish(
                job_id=job_id, worker_id=worker_id, lease_token=lease_token,
                status="failed", error={"code": "handler_failed"},
            )
            final_status = finished.get("status", "failed")
            if final_status == "queued":
                # DB has committed the retry transition. Dispatch another worker
                # task; if the broker is unavailable, a same-key API retry can
                # safely dispatch the still-queued durable row later.
                celery_app.send_task("tasks.process_platform_ledger_job")
            return {"processed": True, "status": final_status, "job_id": job_id}

        ledger.finish(
            job_id=job_id, worker_id=worker_id, lease_token=lease_token,
            status="succeeded", result=result,
        )
        return {"processed": True, "status": "succeeded", "job_id": job_id}
    finally:
        ledger.close()


@celery_app.task(name="tasks.reconcile_platform_ledger_dispatches")
def reconcile_platform_ledger_dispatches() -> dict[str, Any]:
    """Redispatch durable queued/expired jobs on a schedule; safe to run repeatedly."""
    if os.environ.get("PLATFORM_JOB_LEDGER_ENABLED", "false").strip().lower() != "true":
        return {"enabled": False, "reserved": 0, "dispatched": 0}

    ledger = PlatformJobLedger()
    reserved = 0
    dispatched = 0
    try:
        job_ids = ledger.reserve_dispatches(limit=25)
        reserved = len(job_ids)
        for _job_id in job_ids:
            try:
                celery_app.send_task("tasks.process_platform_ledger_job")
                dispatched += 1
            except Exception:
                # The reservation has a 60-second cooldown; a later beat tick
                # retries it. Never include broker exception text in task output.
                break
        return {
            "enabled": True,
            "reserved": reserved,
            "dispatched": dispatched,
            "dispatch_incomplete": dispatched < reserved,
        }
    finally:
        ledger.close()
