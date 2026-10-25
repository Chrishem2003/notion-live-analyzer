"""Opt-in black-box staging smoke test for per-user durable-job isolation.

Requires an isolated staging API/database with USER_JOB_API_ENABLED=true and
PLATFORM_JOB_WORKER_ENABLED=false. Tokens are read from environment variables
and are never printed. This script creates/cancels synthetic staging jobs.
Never point it at production.
"""
from __future__ import annotations

import os
import sys
import uuid
from urllib.parse import urlparse

import requests


def require_https_base() -> str:
    base = os.environ.get("STAGING_SHARED_AI_API_URL", "").strip().rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise SystemExit("Set STAGING_SHARED_AI_API_URL to the HTTPS base URL of an isolated staging API.")
    if "onrender.com" in parsed.netloc and "staging" not in parsed.netloc.lower():
        raise SystemExit("Refusing a likely production Render hostname; use a clearly named isolated staging service.")
    return base


def request(method: str, url: str, token: str, **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    headers["Authorization"] = f"Bearer {token}"
    return requests.request(method, url, headers=headers, timeout=10, **kwargs)


def expect_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise RuntimeError(f"{label}: expected HTTP {expected}, got {response.status_code}. Response body withheld.")


def main() -> int:
    base = require_https_base()
    token_a = os.environ.get("STAGING_USER_A_ACCESS_TOKEN", "").strip()
    token_b = os.environ.get("STAGING_USER_B_ACCESS_TOKEN", "").strip()
    if not token_a or not token_b or token_a == token_b:
        raise SystemExit("Provide two different staging user access tokens in environment variables; tokens are never printed.")

    root = f"{base}/api/v1/user-jobs"
    # Validate that both independent tokens can reach the user-scoped route.
    expect_status(request("GET", f"{root}?limit=1", token_a), 200, "User A history")
    expect_status(request("GET", f"{root}?limit=1", token_b), 200, "User B history")

    key = str(uuid.uuid4())
    payload = {
        "job_type": "intelligence.solve",
        "prompt": "STAGING ISOLATION TEST ONLY: return a short synthetic acknowledgement.",
        "strategy": "direct",
        "max_attempts": 1,
    }
    created = request("POST", root, token_a, json=payload, headers={"Idempotency-Key": key})
    expect_status(created, 202, "Create synthetic job as User A")
    body = created.json()
    job_id = body.get("job_id")
    if not isinstance(job_id, str):
        raise RuntimeError("Create synthetic job: response did not contain a job ID.")
    try:
        job_id = str(uuid.UUID(job_id))
    except ValueError as exc:
        raise RuntimeError("Create synthetic job: returned job ID is not a UUID.") from exc

    # Same-key retry must return the same job, not create a duplicate.
    retry = request("POST", root, token_a, json=payload, headers={"Idempotency-Key": key})
    expect_status(retry, 202, "Idempotent retry as User A")
    if retry.json().get("job_id") != job_id:
        raise RuntimeError("Idempotent retry returned a different job ID.")

    # User A can inspect it; User B cannot discover or cancel it.
    expect_status(request("GET", f"{root}/{job_id}", token_a), 200, "User A reads own job")
    expect_status(request("GET", f"{root}/{job_id}", token_b), 404, "User B cross-account read")
    expect_status(request("DELETE", f"{root}/{job_id}", token_b), 404, "User B cross-account cancellation")

    history_b = request("GET", f"{root}?limit=50", token_b)
    expect_status(history_b, 200, "User B history after User A submission")
    rows = history_b.json()
    if not isinstance(rows, list) or any(row.get("job_id") == job_id for row in rows if isinstance(row, dict)):
        raise RuntimeError("User B history exposed User A's job.")

    # Cancel own synthetic job so a worker-disabled staging queue stays tidy.
    cancelled = request("DELETE", f"{root}/{job_id}", token_a)
    if cancelled.status_code not in (200, 409):
        raise RuntimeError(f"User A cancellation: expected HTTP 200 or 409, got {cancelled.status_code}.")
    print("PASS: two distinct users, owner read, cross-user 404, history isolation, idempotency, and cancellation request.")
    print("Review staging logs separately for token/prompt/result non-disclosure. No tokens or response bodies were printed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
