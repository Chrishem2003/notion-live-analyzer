"""Explicitly gated acceptance smoke test for synthetic Analysis Run write-back.

The script never sends a request unless --execute is supplied and
RESEARCH_RUN_SMOKE_CONFIRM_SYNTHETIC=true is set. It creates or reuses one
synthetic Analysis Run, verifies same-ID idempotency, then verifies that a
changed payload with the same ID is rejected. It does not delete the record;
keep the synthetic run as acceptance evidence.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests


class SmokeTestError(RuntimeError):
    """The staging acceptance check failed or was not safely configured."""


def build_payload(run_id: str, project_page_id: str, protocol_page_id: str) -> Dict[str, Any]:
    if not isinstance(run_id, str) or not run_id.strip() or len(run_id.strip()) > 200:
        raise SmokeTestError("--run-id must be a stable non-empty ID of at most 200 characters.")
    if not project_page_id.strip() or not protocol_page_id.strip():
        raise SmokeTestError("Private Demo project and protocol page IDs are required.")
    return {
        "run_id": run_id.strip(),
        "run_name": "Synthetic deployment acceptance smoke test",
        "project_page_id": project_page_id.strip(),
        "protocol_page_id": protocol_page_id.strip(),
        "input_sample_page_ids": [],
        "input_data_record_page_ids": [],
        "source_evidence_page_ids": [],
        "input_dataset_version": "staging-smoke-v1",
        "analysis_method": "Synthetic API acceptance check; no scientific analysis performed.",
        "code_revision": "staging-smoke",
        "environment": "staging",
        "manifest_hash": "",
        "parameters_json": "{\"synthetic\":true,\"purpose\":\"staging acceptance\"}",
    }


def _post(session: Any, endpoint: str, api_key: str, payload: Dict[str, Any]):
    try:
        return session.post(
            endpoint,
            json=payload,
            headers={
                "X-API-Key": api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=90,
        )
    except requests.RequestException as exc:
        raise SmokeTestError(
            f"API request failed ({type(exc).__name__}). Re-run only with the same --run-id to reconcile safely."
        ) from exc


def _body(response: Any, label: str) -> Dict[str, Any]:
    try:
        body = response.json()
    except Exception as exc:
        raise SmokeTestError(f"{label}: API returned invalid JSON.") from exc
    if not isinstance(body, dict):
        raise SmokeTestError(f"{label}: API response must be a JSON object.")
    return body


def run_smoke(
    *,
    base_url: str,
    api_key: str,
    project_page_id: str,
    protocol_page_id: str,
    run_id: str,
    session: Optional[Any] = None,
) -> Dict[str, Any]:
    parsed = urlparse(base_url.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise SmokeTestError("The staging API URL must be an absolute HTTPS URL.")
    if not api_key.strip():
        raise SmokeTestError("PLATFORM_API_KEY is missing.")
    payload = build_payload(run_id, project_page_id, protocol_page_id)
    endpoint = base_url.strip().rstrip("/") + "/api/v1/research-runs"
    client = session or requests.Session()

    first = _post(client, endpoint, api_key.strip(), payload)
    if first.status_code != 200:
        raise SmokeTestError(f"Initial synthetic run returned HTTP {first.status_code}; no acceptance passed.")
    first_body = _body(first, "Initial synthetic run")
    page_id = first_body.get("page_id")
    if not page_id or first_body.get("run_id") != payload["run_id"]:
        raise SmokeTestError("Initial response did not identify a persisted run page and matching run ID.")
    if first_body.get("record_classification") != "Synthetic/Test":
        raise SmokeTestError("Initial response did not preserve Synthetic/Test classification.")
    if first_body.get("run_status") != "Draft" or first_body.get("workflow_gate") != "Intake":
        raise SmokeTestError("Initial run did not remain at Draft / Intake.")

    retry = _post(client, endpoint, api_key.strip(), payload)
    if retry.status_code != 200:
        raise SmokeTestError(f"Same-ID retry returned HTTP {retry.status_code}, expected HTTP 200.")
    retry_body = _body(retry, "Same-ID retry")
    if retry_body.get("created") is not False or retry_body.get("page_id") != page_id:
        raise SmokeTestError("Same-ID retry did not return the original page without creating a duplicate.")

    changed_payload = dict(payload)
    changed_payload["analysis_method"] = payload["analysis_method"] + " Changed payload to test conflict."
    conflict = _post(client, endpoint, api_key.strip(), changed_payload)
    if conflict.status_code != 409:
        raise SmokeTestError(f"Changed payload with the same run ID returned HTTP {conflict.status_code}, expected HTTP 409.")

    return {
        "status": "passed",
        "run_id": payload["run_id"],
        "page_id": page_id,
        "page_url": first_body.get("page_url"),
        "created_on_first_call": first_body.get("created") is True,
        "same_id_retry_reused_page": True,
        "changed_payload_conflict_http_409": True,
        "record_classification": first_body.get("record_classification"),
        "run_status": first_body.get("run_status"),
        "workflow_gate": first_body.get("workflow_gate"),
        "note": "Synthetic acceptance record retained in Notion as evidence; no real research inputs were used.",
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Actually send synthetic requests; otherwise dry-run only.")
    parser.add_argument("--run-id", default="", help="Stable run ID; reuse this exact value if reconciling an ambiguous attempt.")
    args = parser.parse_args(argv)
    if not args.execute:
        print("DRY RUN: no API requests sent. Configure the staging environment and pass --execute --run-id <stable-id> to run the synthetic acceptance check.")
        return 0
    if os.environ.get("RESEARCH_RUN_SMOKE_CONFIRM_SYNTHETIC", "").strip().lower() != "true":
        print("NOT READY: set RESEARCH_RUN_SMOKE_CONFIRM_SYNTHETIC=true only after confirming this is a synthetic staging test.", file=sys.stderr)
        return 2
    if not args.run_id.strip():
        print("NOT READY: --run-id is required for execution so retries can reuse the same stable ID.", file=sys.stderr)
        return 2

    try:
        result = run_smoke(
            base_url=os.environ.get("RESEARCH_RUN_API_URL", ""),
            api_key=os.environ.get("PLATFORM_API_KEY", ""),
            project_page_id=os.environ.get("RESEARCH_RUN_SMOKE_PROJECT_PAGE_ID", ""),
            protocol_page_id=os.environ.get("RESEARCH_RUN_SMOKE_PROTOCOL_PAGE_ID", ""),
            run_id=args.run_id,
        )
    except SmokeTestError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
