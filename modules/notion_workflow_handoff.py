"""Explicit, duplicate-aware handoff of successful local workflow runs to Notion.

This adapter requires a user-configured Notion integration token and a database ID.
It does not mark scientific QC or reproducibility as passed; the created record stays
pending review and is classified Synthetic/Test until a reviewer changes it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from typing import Any, Mapping

import requests

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"
DEFAULT_ANALYSIS_RUNS_DATABASE_ID = "c2edb48da81649aa90a8b9db6e15bf11"


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
    """Build one Notion text fragment without silently hiding truncation."""
    limit = 1900
    if len(value) > limit:
        marker = "… [truncated; see manifest hash and local run store]"
        value = value[:limit - len(marker)] + marker
    return {"rich_text": [{"type": "text", "text": {"content": value}}]}


def _validated_timestamp(value: Any, field: str) -> str:
    """Require an ISO-8601 timestamp with timezone before sending a Notion date."""
    if not isinstance(value, str) or not value.strip():
        raise NotionHandoffError(f"successful run is missing {field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NotionHandoffError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise NotionHandoffError(f"{field} must include a timezone")
    return parsed.isoformat()


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



def _validate_database_schema(payload: Mapping[str, Any]) -> None:
    """Fail before writing if the target database cannot represent a safe handoff."""
    props = payload.get("properties")
    if not isinstance(props, dict):
        raise NotionHandoffError("target Notion database returned no property schema")
    required = {
        "Run Name": ("title", None),
        "Run Status": ("select", "Complete"),
        "Workflow Gate": ("select", "Execution Recorded"),
        "QC Outcome": ("select", "Pending"),
        "Reproducibility Check": ("select", "Not Checked"),
        "Record Classification": ("select", "Synthetic/Test"),
        "Analysis Method": ("rich_text", None),
        "Code Revision": ("rich_text", None),
        "Input Dataset Version": ("rich_text", None),
        "Run Manifest Hash": ("rich_text", None),
        "Execution Evidence / Handoff": ("rich_text", None),
        "Environment": ("rich_text", None),
        "Parameters": ("rich_text", None),
        "Started At": ("date", None),
        "Completed At": ("date", None),
    }
    missing = sorted(set(required) - set(props))
    if missing:
        raise NotionHandoffError("target database is missing required properties: " + ", ".join(missing))
    for name, (expected_type, required_option) in required.items():
        spec = props.get(name)
        if not isinstance(spec, dict) or spec.get("type") != expected_type:
            actual = spec.get("type", "unknown") if isinstance(spec, dict) else "missing"
            raise NotionHandoffError(
                f"target property {name!r} has type {actual!r}; expected {expected_type!r}"
            )
        if required_option:
            options = spec.get("select", {}).get("options", [])
            names = {option.get("name") for option in options if isinstance(option, dict)}
            if required_option not in names:
                raise NotionHandoffError(
                    f"target property {name!r} is missing required option {required_option!r}"
                )
    blocker = props.get("Blocker / Recovery Action")
    if blocker is not None and (not isinstance(blocker, dict) or blocker.get("type") != "rich_text"):
        raise NotionHandoffError("target property 'Blocker / Recovery Action' must be rich_text")

def _safe_notion_request(
    session: Any,
    method: str,
    url: str,
    *,
    headers: Mapping[str, str],
    json_body: Mapping[str, Any] | None = None,
    retries: int = 3,
) -> dict[str, Any]:
    """Retry only reads/idempotent lookups on transient transport/API failures."""
    if method not in {"GET", "POST"}:
        raise NotionHandoffError("unsupported Notion request method")
    for attempt in range(retries):
        try:
            if method == "GET":
                response = session.get(url, headers=headers, timeout=20)
            else:
                response = session.post(url, headers=headers, json=json_body, timeout=20)
        except requests.RequestException as exc:
            if attempt + 1 >= retries:
                raise NotionHandoffError(
                    f"Notion {method} request failed after {retries} attempts "
                    f"({type(exc).__name__})"
                ) from exc
            time.sleep(min(0.25 * (2 ** attempt), 2.0))
            continue

        status = getattr(response, "status_code", 500)
        if status == 429 or status >= 500:
            if attempt + 1 < retries:
                retry_after = getattr(response, "headers", {}).get("Retry-After", "")
                try:
                    delay = float(retry_after)
                except (TypeError, ValueError):
                    delay = 0.25 * (2 ** attempt)
                time.sleep(max(0.0, min(delay, 2.0)))
                continue
        return _response_json(response)
    raise NotionHandoffError("Notion request exhausted its retry budget")


def _validate_database_id(value: str) -> str:
    """Accept only a Notion UUID so configuration cannot alter the API path."""
    candidate = value.strip()
    if not re.fullmatch(r"[0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", candidate):
        raise NotionHandoffError("Notion database ID must be a 32-character UUID, with optional hyphens")
    return candidate


def _sync_run_to_notion_unlocked(
    run: Mapping[str, Any],
    *,
    token: str | None = None,
    database_id: str | None = None,
    session: Any = requests,
) -> dict[str, Any]:
    """Create or return an existing matching Analysis Runs record.

    Only successful runs are eligible. The adapter verifies the live database
    property types and required select options before any write. Repeat calls query
    by manifest hash before creating a page; Notion does not provide an atomic unique
    constraint for this property, so concurrent simultaneous calls can still race.
    """
    api_token = token or os.environ.get("NOTION_API_KEY")
    target_database = database_id or os.environ.get("NOTION_ANALYSIS_RUNS_DATABASE_ID") or DEFAULT_ANALYSIS_RUNS_DATABASE_ID
    if not isinstance(api_token, str) or not api_token.strip():
        raise NotionHandoffError("NOTION_API_KEY is not configured")
    if not isinstance(target_database, str) or not target_database.strip():
        raise NotionHandoffError("NOTION_ANALYSIS_RUNS_DATABASE_ID is not configured")
    api_token = api_token.strip()
    target_database = _validate_database_id(target_database)
    if run.get("status") != "succeeded":
        raise NotionHandoffError("only successful workflow runs can be handed off")
    run_id = run.get("run_id")
    workflow_id = run.get("workflow_id")
    task_type = run.get("task_type")
    if not all(isinstance(v, str) and v.strip() for v in (run_id, workflow_id, task_type)):
        raise NotionHandoffError("run identity is incomplete")
    started_at = _validated_timestamp(run.get("created_at"), "created_at")
    completed_at = _validated_timestamp(run.get("updated_at"), "updated_at")
    digest = manifest_digest(run)
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }
    schema_payload = _safe_notion_request(
        session, "GET", f"{NOTION_API_BASE}/databases/{target_database}",
        headers=headers,
    )
    _validate_database_schema(schema_payload)
    base = f"{NOTION_API_BASE}/databases/{target_database}/query"
    query_body = {
        "filter": {
            "property": "Run Manifest Hash",
            "rich_text": {"equals": digest},
        },
        "page_size": 1,
    }
    queried = _safe_notion_request(
        session, "POST", base, headers=headers, json_body=query_body,
    )
    existing = queried.get("results", [])
    if existing:
        first = existing[0]
        return {
            "created": False,
            "page_id": first.get("id"),
            "url": first.get("url"),
            "manifest_hash": digest,
        }

    properties: dict[str, Any] = {
        "Run Name": {"title": [{"type": "text", "text": {"content": f"{task_type}: {workflow_id} · {run_id}"[:1800]}}]},
        "Run Status": {"select": {"name": "Complete"}},
        "Workflow Gate": {"select": {"name": "Execution Recorded"}},
        "QC Outcome": {"select": {"name": "Pending"}},
        "Reproducibility Check": {"select": {"name": "Not Checked"}},
        "Record Classification": {"select": {"name": "Synthetic/Test"}},
        "Analysis Method": _rich_text(task_type),
        "Code Revision": _rich_text(
            str(run.get("code_revision") or os.environ.get("GIT_COMMIT_SHA") or "Not supplied by runtime")
        ),
        "Input Dataset Version": _rich_text(
            str((run.get("input") or {}).get("dataset_version") or "Not supplied by runtime")
            if isinstance(run.get("input"), Mapping) else "Not supplied by runtime"
        ),
        "Run Manifest Hash": _rich_text(digest),
        "Execution Evidence / Handoff": _rich_text(
            f"Local run ID: {run_id}; workflow: {workflow_id}; task: {task_type}; "
            f"result: {json.dumps(run.get('result'), sort_keys=True, ensure_ascii=False, allow_nan=False)}; "
            "handoff status: delivered; QC and reproducibility are still pending."
        ),
        "Environment": _rich_text("Local SQLite workflow runtime; explicit user-triggered Notion handoff"),
        "Parameters": _rich_text(json.dumps(run.get("input"), sort_keys=True, ensure_ascii=False, allow_nan=False)),
    }
    properties["Started At"] = {"date": {"start": started_at}}
    properties["Completed At"] = {"date": {"start": completed_at}}
    if run.get("error_message"):
        properties["Blocker / Recovery Action"] = _rich_text(str(run["error_message"]))
    try:
        created_response = session.post(
            f"{NOTION_API_BASE}/pages",
            headers=headers,
            json={"parent": {"database_id": target_database}, "properties": properties},
            timeout=20,
        )
    except requests.RequestException as exc:
        # The server may have committed the page before the connection failed.
        # Never blindly replay this non-idempotent create request. A fresh call
        # will query by manifest hash before deciding whether creation is needed.
        raise NotionHandoffError(
            "Notion page creation outcome is unknown after a transport failure; "
            "retry the handoff action to reconcile by manifest hash before creating again"
        ) from exc
    created = _response_json(created_response)
    return {
        "created": True,
        "page_id": created.get("id"),
        "url": created.get("url"),
        "manifest_hash": digest,
    }



@contextmanager
def _handoff_ledger_lock(database_path: str | Path):
    """Serialize handoffs that share a durable SQLite database path.

    BEGIN IMMEDIATE reserves the SQLite write lock before checking Notion and holds
    it through the create/reconciliation request. This closes the local concurrent
    query-before-create race for processes sharing the same database file. It does
    not create a distributed lock across hosts with separate filesystems, and it
    cannot make Notion's API transactionally atomic with SQLite.
    """
    path = str(database_path)
    if path != ":memory:":
        Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30, isolation_level=None)
    try:
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("BEGIN IMMEDIATE")
        yield
        connection.execute("COMMIT")
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def sync_run_to_notion(
    run: Mapping[str, Any],
    *,
    token: str | None = None,
    database_id: str | None = None,
    session: Any = requests,
    ledger_database: str | Path | None = None,
) -> dict[str, Any]:
    """Safely hand off a successful run, optionally serializing through SQLite.

    The Streamlit execution center passes the durable runtime database as the
    ledger_database argument. Concurrent handoffs sharing that file are serialized
    so the second caller re-queries Notion after the first caller has finished.
    Callers that omit the ledger path retain compatibility behavior, including the
    documented query-before-create race. Separate hosts/filesystems still require a
    centralized outbox/worker to guarantee cross-host serialization.
    """
    if ledger_database is None:
        configured_path = os.environ.get("WORKFLOW_RUNTIME_DB")
        if configured_path:
            ledger_database = configured_path
    if ledger_database is None:
        return _sync_run_to_notion_unlocked(
            run, token=token, database_id=database_id, session=session
        )
    with _handoff_ledger_lock(ledger_database):
        return _sync_run_to_notion_unlocked(
            run, token=token, database_id=database_id, session=session
        )
