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
from modules.platform_job_ledger import PlatformJobLedger, PlatformLedgerUnavailable


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
            ledger.finish(
                job_id=job_id, worker_id=worker_id, lease_token=lease_token,
                status="failed", error={"code": "handler_failed"},
            )
            return {"processed": True, "status": "failed", "job_id": job_id}

        ledger.finish(
            job_id=job_id, worker_id=worker_id, lease_token=lease_token,
            status="succeeded", result=result,
        )
        return {"processed": True, "status": "succeeded", "job_id": job_id}
    finally:
        ledger.close()
