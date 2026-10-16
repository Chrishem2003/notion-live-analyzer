"""Explicit, idempotent handoff of successful local workflow runs to Notion.

This adapter requires a user-configured Notion integration token and a database ID.
It does not mark scientific QC or reproducibility as passed; the created record stays
pending review and is classified Synthetic/Test until a reviewer changes it.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Mapping

import requests

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"


class NotionHandoffError(RuntimeError):
    """Raised when a run cannot be safely delivered to the configured Notion database."""


def manifest_digest(run: Mapping[str, Any]) -> str:
    """Return a deterministic digest for the result payload and its run identity."""
    manifest = {
        "run_id": run.get("run_id"),
        "workflow_id": run.get("workflow_id"),
        "task_type": run.get("task_type"),
        "input": run.get("input"),
        "result": run.get("result"),
        "status": run.get("status"),
    }
    try:
        encoded = json.dumps(
            manifest, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise NotionHandoffError("run manifest is not finite JSON-compatible data") from exc
    return hashlib.sha256(encoded).hexdigest()


def _rich_text(value: str) -> dict[str, Any]:
    return {"rich_text": [{"type": "text", "text": {"content": value[:1900]}}]}


def _response_json(response: Any) -> dict[str, Any]:
    try:
        payload = response.json()
    except Exception as exc:
        raise NotionHandoffError("Notion returned a non-JSON response") from exc
    if not isinstance(payload, dict):
        raise NotionHandoffError("Notion returned an unexpected response shape")
    if getattr(response, "status_code", 500) >= 400:
        message = payload.get("message", "request failed")
        raise NotionHandoffError(f"Notion API request failed ({response.status_code}): {message}")
    return payload


def sync_run_to_notion(
    run: Mapping[str, Any],
    *,
    token: str | None = None,
    database_id: str | None = None,
    session: Any = requests,
) -> dict[str, Any]:
    """Create or return an existing matching Analysis Runs record.

    Only successful runs are eligible. Idempotency uses the manifest hash property.
    The Notion database must expose the property names/types documented in this repo.
    """
    api_token = token or os.environ.get("NOTION_API_KEY")
    target_database = database_id or os.environ.get("NOTION_ANALYSIS_RUNS_DATABASE_ID")
    if not isinstance(api_token, str) or not api_token.strip():
        raise NotionHandoffError("NOTION_API_KEY is not configured")
    if not isinstance(target_database, str) or not target_database.strip():
        raise NotionHandoffError("NOTION_ANALYSIS_RUNS_DATABASE_ID is not configured")
    if run.get("status") != "succeeded":
        raise NotionHandoffError("only successful workflow runs can be handed off")
    run_id = run.get("run_id")
    workflow_id = run.get("workflow_id")
    task_type = run.get("task_type")
    if not all(isinstance(v, str) and v.strip() for v in (run_id, workflow_id, task_type)):
        raise NotionHandoffError("run identity is incomplete")
    digest = manifest_digest(run)
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }
    base = f"{NOTION_API_BASE}/databases/{target_database}/query"
    query_response = session.post(
        base,
        headers=headers,
        json={
            "filter": {
                "property": "Run Manifest Hash",
                "rich_text": {"equals": digest},
            },
            "page_size": 1,
        },
        timeout=20,
    )
    queried = _response_json(query_response)
    existing = queried.get("results", [])
    if existing:
        first = existing[0]
        return {
            "created": False,
            "page_id": first.get("id"),
            "url": first.get("url"),
            "manifest_hash": digest,
        }

    now = run.get("updated_at") or run.get("created_at")
    properties: dict[str, Any] = {
        "Run Name": {"title": [{"type": "text", "text": {"content": f"{task_type}: {workflow_id}"[:1800]}}]},
        "Run Status": {"select": {"name": "Complete"}},
        "Workflow Gate": {"select": {"name": "Execution Recorded"}},
        "QC Outcome": {"select": {"name": "Pending"}},
        "Reproducibility Check": {"select": {"name": "Not Checked"}},
        "Record Classification": {"select": {"name": "Synthetic/Test"}},
        "Analysis Method": _rich_text(task_type),
        "Run Manifest Hash": _rich_text(digest),
        "Execution Evidence / Handoff": _rich_text(
            f"Local run ID: {run_id}; workflow: {workflow_id}; task: {task_type}; "
            "handoff status: delivered; QC and reproducibility are still pending."
        ),
        "Environment": _rich_text("Local SQLite workflow runtime; explicit user-triggered Notion handoff"),
        "Parameters": _rich_text(json.dumps(run.get("input"), sort_keys=True, ensure_ascii=False, allow_nan=False)),
    }
    if run.get("created_at"):
        properties["Started At"] = {"date": {"start": run["created_at"]}}
    if now:
        properties["Completed At"] = {"date": {"start": now}}
    if run.get("error_message"):
        properties["Blocker / Recovery Action"] = _rich_text(str(run["error_message"]))
    created_response = session.post(
        f"{NOTION_API_BASE}/pages",
        headers=headers,
        json={"parent": {"database_id": target_database}, "properties": properties},
        timeout=20,
    )
    created = _response_json(created_response)
    return {
        "created": True,
        "page_id": created.get("id"),
        "url": created.get("url"),
        "manifest_hash": digest,
    }
