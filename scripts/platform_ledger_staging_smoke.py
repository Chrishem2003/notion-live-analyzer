"""Fail-closed end-to-end smoke test for a NON-PRODUCTION platform ledger.

Required environment:
  PLATFORM_LEDGER_SMOKE_BASE_URL=https://<approved-staging-host>
  PLATFORM_LEDGER_SMOKE_API_KEY=<service API key>
  PLATFORM_LEDGER_SMOKE_CONFIRM=I_UNDERSTAND_NON_PRODUCTION

This script creates one synthetic validation job and deliberately checks an
idempotency conflict. It never submits real Notion/research work and refuses
the known current production API hostname.
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from urllib.parse import urlparse

import requests

PRODUCTION_HOSTS = {"notion-live-analyzer-api.onrender.com"}
CONFIRMATION = "I_UNDERSTAND_NON_PRODUCTION"
TERMINAL_STATES = {"succeeded", "failed", "needs_review"}


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def validate_metrics(payload: object) -> dict:
    """Validate the complete aggregate-only metrics contract."""
    fields = {
        "total", "queued", "running", "succeeded", "failed", "needs_review",
        "expired_leases", "oldest_queued_age_seconds", "created_last_24h",
        "finished_last_24h", "sampled_at",
    }
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ValueError("Metrics response has an unexpected schema.")
    for field in fields - {"sampled_at"}:
        value = payload.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"Metrics field {field!r} is invalid.")
    if not isinstance(payload.get("sampled_at"), str) or not payload["sampled_at"]:
        raise ValueError("Metrics sample timestamp is invalid.")
    states_total = sum(payload[field] for field in (
        "queued", "running", "succeeded", "failed", "needs_review"
    ))
    if payload["total"] != states_total or payload["expired_leases"] > payload["running"]:
        raise ValueError("Metrics counters are inconsistent.")
    return payload


def validate_successful_job_transition(before: dict, after: dict) -> None:
    """Require the completed smoke job to appear in the aggregate counters."""
    if after["succeeded"] < before["succeeded"] + 1:
        raise ValueError("Succeeded-job count did not increase after the smoke job.")
    if after["finished_last_24h"] < before["finished_last_24h"] + 1:
        raise ValueError("Finished-job count did not increase after the smoke job.")


def main() -> None:
    base_url = os.environ.get("PLATFORM_LEDGER_SMOKE_BASE_URL", "").strip().rstrip("/")
    api_key = os.environ.get("PLATFORM_LEDGER_SMOKE_API_KEY", "").strip()
    confirmation = os.environ.get("PLATFORM_LEDGER_SMOKE_CONFIRM", "")
    parsed = urlparse(base_url)

    if confirmation != CONFIRMATION:
        fail("Explicit non-production confirmation is required.")
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        fail("Base URL must be a valid HTTPS URL without embedded credentials.")
    if parsed.hostname.lower() in PRODUCTION_HOSTS:
        fail("Refusing to create a smoke-test job on the known production API host.")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        fail("Base URL must contain only the scheme and host.")
    if not api_key:
        fail("PLATFORM_LEDGER_SMOKE_API_KEY is required.")

    session = requests.Session()
    session.headers.update({
        "X-API-Key": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    session.verify = True
    timeout = (5, 10)
    idempotency_key = f"staging-smoke-{uuid.uuid4()}"

    try:
        health = session.get(f"{base_url}/api/v1/health", timeout=timeout)
        health.raise_for_status()
        health_body = health.json()
        if not isinstance(health_body, dict) or health_body.get("status") != "ok":
            fail("Health endpoint did not report a healthy API.")

        metrics_before_response = session.get(
            f"{base_url}/api/v1/platform-jobs/metrics", timeout=timeout
        )
        if metrics_before_response.status_code != 200:
            fail(f"Metrics endpoint unavailable (HTTP {metrics_before_response.status_code}); check staging flag, auth, and migrations.")
        try:
            metrics_before = validate_metrics(metrics_before_response.json())
        except ValueError:
            fail("Metrics endpoint returned an invalid or unsafe response.")

        request_body = {
            "job_type": "platform.synthetic.validate",
            "payload": {"smoke_test": True, "nonce": str(uuid.uuid4())},
            "max_attempts": 2,
        }
        enqueue = session.post(
            f"{base_url}/api/v1/platform-jobs",
            headers={"Idempotency-Key": idempotency_key},
            json=request_body,
            timeout=timeout,
        )
        if enqueue.status_code != 202:
            fail(f"Synthetic job was not accepted (HTTP {enqueue.status_code}).")
        accepted = enqueue.json()
        job_id = accepted.get("job_id")
        status_url = accepted.get("status_url")
        if not isinstance(job_id, str) or not isinstance(status_url, str):
            fail("Enqueue response is missing expected status fields.")
        if not status_url.startswith("/api/v1/platform-jobs/"):
            fail("Enqueue response contains an unexpected status URL.")

        # Same key and same request must be idempotent and return the same job.
        duplicate = session.post(
            f"{base_url}/api/v1/platform-jobs",
            headers={"Idempotency-Key": idempotency_key},
            json=request_body,
            timeout=timeout,
        )
        if duplicate.status_code != 202 or duplicate.json().get("job_id") != job_id:
            fail("Same-key retry did not return the original job.")

        # Same key with a different request must conflict instead of silently
        # changing the original job.
        conflicting_body = {**request_body, "payload": {"smoke_test": "conflict"}}
        conflict = session.post(
            f"{base_url}/api/v1/platform-jobs",
            headers={"Idempotency-Key": idempotency_key},
            json=conflicting_body,
            timeout=timeout,
        )
        if conflict.status_code != 409:
            fail(f"Changed request with reused idempotency key should return HTTP 409, got {conflict.status_code}.")

        deadline = time.monotonic() + 120
        final_status = None
        while time.monotonic() < deadline:
            response = session.get(f"{base_url}{status_url}", timeout=timeout)
            response.raise_for_status()
            state = response.json()
            if "payload" in state or "lease_token" in state:
                fail("Status endpoint exposed a payload or lease token.")
            final_status = state.get("status")
            if final_status in TERMINAL_STATES:
                break
            time.sleep(2)

        if final_status != "succeeded":
            fail(f"Synthetic job did not succeed within 120 seconds (state={final_status!r}).")

        metrics_after_response = session.get(
            f"{base_url}/api/v1/platform-jobs/metrics", timeout=timeout
        )
        metrics_after_response.raise_for_status()
        try:
            metrics_after = validate_metrics(metrics_after_response.json())
        except ValueError:
            fail("Metrics endpoint returned an invalid or unsafe response.")
        try:
            validate_successful_job_transition(metrics_before, metrics_after)
        except ValueError:
            fail("Aggregate metrics did not record the successful smoke job.")

        print("PASS: non-production synthetic job lifecycle completed.")
        print("PASS: same-key idempotency and changed-request conflict verified.")
        print("PASS: status and aggregate metrics passed sensitive-field checks.")
        print(f"Final synthetic job state: {final_status}")
    except requests.RequestException as exc:
        # Never print exception details because URLs/headers can be sensitive.
        fail(f"HTTP interaction failed ({type(exc).__name__}); inspect staging logs securely.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
