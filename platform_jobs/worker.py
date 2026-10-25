"""Bounded and continuous processing for the durable Supabase job queue."""
from __future__ import annotations
import argparse
import logging
import os
import signal
import time
from typing import Any
from platform_jobs.repository import JobStoreUnavailable, SupabaseJobRepository

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("platform_jobs.worker")
_STOP = False

def _stop(_signum: int, _frame: Any) -> None:
    global _STOP
    _STOP = True

def _execute(job: dict[str, Any]) -> dict[str, Any]:
    if job.get("job_type") != "intelligence.solve":
        raise ValueError("unsupported_job_type")
    payload = job.get("payload")
    if not isinstance(payload, dict) or not isinstance(payload.get("prompt"), str) or not payload["prompt"].strip():
        raise ValueError("invalid_job_payload")
    from sovereign_intelligence.api.service_router import _get_brain
    result = _get_brain().solve_governed(
        prompt=payload["prompt"], provider=payload.get("provider"),
        model=payload.get("model"), strategy=payload.get("strategy", "direct"),
    )
    verification = getattr(result, "verification", None)
    assessment = getattr(result, "assessment", None)
    control = getattr(result, "control", None)
    action = getattr(control, "action", None)
    return {
        "answer": result.answer, "provider": result.provider, "model": result.model,
        "verification": {"passed": getattr(verification, "passed", None), "confidence": getattr(verification, "confidence", None)} if verification else None,
        "governance": {"accepted": getattr(assessment, "accepted", None), "action": getattr(action, "value", None)},
    }

def run_once() -> str:
    """Claim and process at most one job; return a sanitized outcome label."""
    repo = None
    try:
        repo = SupabaseJobRepository()
        job = repo.claim(lease_seconds=900)
        if not job:
            return "idle"
        job_id = str(job.get("job_id", ""))
        try:
            result = _execute(job)
            if not repo.finish(job_id, result):
                log.warning("Job completion was not accepted; job_id=%s", job_id)
                return "completion_rejected"
            return "succeeded"
        except Exception as exc:
            code = type(exc).__name__
            log.warning("Job attempt failed; job_id=%s error_type=%s", job_id, code)
            try:
                repo.fail(job_id, code, retry_delay_seconds=min(30 * int(job.get("attempt_count", 1)), 300))
            except Exception:
                log.exception("Unable to record job failure; job_id=%s", job_id)
            return "failed"
    except JobStoreUnavailable:
        log.warning("Job store unavailable")
        return "unavailable"
    except Exception:
        log.exception("Worker cycle failed")
        return "error"
    finally:
        if repo:
            repo.close()

def run() -> None:
    global _STOP
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    poll_seconds = max(1.0, min(float(os.environ.get("PLATFORM_JOB_POLL_SECONDS", "3")), 30.0))
    while not _STOP:
        outcome = run_once()
        if outcome in {"idle", "unavailable", "error"} and not _STOP:
            time.sleep(poll_seconds if outcome == "idle" else min(poll_seconds * 3, 30.0))

def main() -> int:
    parser = argparse.ArgumentParser(description="Process durable platform jobs.")
    parser.add_argument("--once", action="store_true", help="claim at most one job and exit")
    args = parser.parse_args()
    if args.once:
        outcome = run_once()
        log.info("One-shot worker outcome=%s", outcome)
        return 0 if outcome in {"idle", "succeeded"} else 1
    run()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
