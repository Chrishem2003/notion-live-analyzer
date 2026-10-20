"""Deployment preflight for the Bio-Research Analysis Run integration.

This command validates environment configuration, Notion data-source schemas and
relation targets, plus local SQLite ledger initialization. It never creates or
updates research records. Run it before starting the API service.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import requests

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"

REQUIRED_ENV = (
    "PLATFORM_API_KEY",
    "NOTION_TOKEN",
    "NOTION_ANALYSIS_RUNS_DATA_SOURCE_ID",
    "NOTION_PROJECTS_DATA_SOURCE_ID",
    "NOTION_PROTOCOLS_DATA_SOURCE_ID",
    "NOTION_SAMPLES_DATA_SOURCE_ID",
    "NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID",
    "NOTION_LITERATURE_DATA_SOURCE_ID",
    "NOTION_GENOMIC_SEQUENCE_DATA_SOURCE_ID",
    "NOTION_TASKS_DATA_SOURCE_ID",
    "NOTION_BRAIN_NOTES_DATA_SOURCE_ID",
    "RESEARCH_RUN_IDEMPOTENCY_DB",
)

# (source environment key, property name, expected property type, target source key)
RELATIONS = (
    ("NOTION_ANALYSIS_RUNS_DATA_SOURCE_ID", "Project", "relation", "NOTION_PROJECTS_DATA_SOURCE_ID"),
    ("NOTION_ANALYSIS_RUNS_DATA_SOURCE_ID", "Protocol", "relation", "NOTION_PROTOCOLS_DATA_SOURCE_ID"),
    ("NOTION_ANALYSIS_RUNS_DATA_SOURCE_ID", "Input Samples", "relation", "NOTION_SAMPLES_DATA_SOURCE_ID"),
    ("NOTION_ANALYSIS_RUNS_DATA_SOURCE_ID", "Input Data Records", "relation", "NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID"),
    ("NOTION_ANALYSIS_RUNS_DATA_SOURCE_ID", "Source Evidence", "relation", "NOTION_LITERATURE_DATA_SOURCE_ID"),
    ("NOTION_SAMPLES_DATA_SOURCE_ID", "Project", "relation", "NOTION_PROJECTS_DATA_SOURCE_ID"),
    ("NOTION_SAMPLES_DATA_SOURCE_ID", "Protocol", "relation", "NOTION_PROTOCOLS_DATA_SOURCE_ID"),
    ("NOTION_SAMPLES_DATA_SOURCE_ID", "📄Literature\u00a0", "relation", "NOTION_LITERATURE_DATA_SOURCE_ID"),
    ("NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID", "Project", "relation", "NOTION_PROJECTS_DATA_SOURCE_ID"),
    ("NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID", "Protocol", "relation", "NOTION_PROTOCOLS_DATA_SOURCE_ID"),
    ("NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID", "Sample", "relation", "NOTION_SAMPLES_DATA_SOURCE_ID"),
    ("NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID", "Source Evidence", "relation", "NOTION_LITERATURE_DATA_SOURCE_ID"),
    ("NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID", "🧬 Genomic Sequence Log", "relation", "NOTION_GENOMIC_SEQUENCE_DATA_SOURCE_ID"),
    ("NOTION_PROTOCOLS_DATA_SOURCE_ID", "Project", "relation", "NOTION_PROJECTS_DATA_SOURCE_ID"),
    ("NOTION_PROTOCOLS_DATA_SOURCE_ID", "Source Evidence", "relation", "NOTION_LITERATURE_DATA_SOURCE_ID"),
    ("NOTION_PROJECTS_DATA_SOURCE_ID", "Daily Task", "relation", "NOTION_TASKS_DATA_SOURCE_ID"),
    ("NOTION_PROJECTS_DATA_SOURCE_ID", "Literature & Sources", "relation", "NOTION_LITERATURE_DATA_SOURCE_ID"),
    ("NOTION_LITERATURE_DATA_SOURCE_ID", "Project Master", "relation", "NOTION_PROJECTS_DATA_SOURCE_ID"),
    ("NOTION_LITERATURE_DATA_SOURCE_ID", "Literature & Sources", "relation", "NOTION_BRAIN_NOTES_DATA_SOURCE_ID"),
    ("NOTION_GENOMIC_SEQUENCE_DATA_SOURCE_ID", "🧪 Project Master", "relation", "NOTION_PROJECTS_DATA_SOURCE_ID"),
    ("NOTION_GENOMIC_SEQUENCE_DATA_SOURCE_ID", "Genomic Sequence Log", "relation", "NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID"),
    ("NOTION_TASKS_DATA_SOURCE_ID", "Project Master", "relation", "NOTION_PROJECTS_DATA_SOURCE_ID"),
    ("NOTION_BRAIN_NOTES_DATA_SOURCE_ID", "📄Literature ", "relation", "NOTION_LITERATURE_DATA_SOURCE_ID"),
)

REQUIRED_PROPERTIES = {
    "NOTION_ANALYSIS_RUNS_DATA_SOURCE_ID": {
        "Run Name": "title",
        "External Run ID": "rich_text",
        "Project": "relation",
        "Protocol": "relation",
        "Input Samples": "relation",
        "Input Data Records": "relation",
        "Input Dataset Version": "rich_text",
        "Source Evidence": "relation",
        "Run Status": "select",
        "Workflow Gate": "select",
        "QC Outcome": "select",
        "Record Classification": "select",
        "Reproducibility Check": "select",
    },
    "NOTION_PROJECTS_DATA_SOURCE_ID": {
        "Project Name": "title",
        "Daily Task": "relation",
        "Literature & Sources": "relation",
    },
    "NOTION_PROTOCOLS_DATA_SOURCE_ID": {
        "Protocol Name": "title", "Project": "relation", "Source Evidence": "relation"
    },
    "NOTION_SAMPLES_DATA_SOURCE_ID": {
        "Sample Name": "title", "Project": "relation", "Protocol": "relation", "📄Literature\u00a0": "relation"
    },
    "NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID": {
        "Project": "relation", "Protocol": "relation", "Sample": "relation",
        "Source Evidence": "relation", "🧬 Genomic Sequence Log": "relation"
    },
    "NOTION_LITERATURE_DATA_SOURCE_ID": {
        "Paper Name": "title", "Project Master": "relation", "Literature & Sources": "relation"
    },
    "NOTION_GENOMIC_SEQUENCE_DATA_SOURCE_ID": {
        "🧪 Project Master": "relation", "Genomic Sequence Log": "relation"
    },
    "NOTION_TASKS_DATA_SOURCE_ID": {"Project Master": "relation"},
    "NOTION_BRAIN_NOTES_DATA_SOURCE_ID": {"📄Literature ": "relation"},
}


class PreflightError(RuntimeError):
    """Deployment configuration or integration schema is not safe to use."""


def normalize_source_id(value: str) -> str:
    return value.strip().removeprefix("collection://").replace("-", "").lower()


def _properties(schema: Mapping[str, Any], env_key: str) -> Dict[str, Any]:
    props = schema.get("properties")
    if not isinstance(props, dict):
        raise PreflightError(f"{env_key}: Notion did not return a properties schema.")
    for name, expected_type in REQUIRED_PROPERTIES.get(env_key, {}).items():
        actual = props.get(name)
        if not isinstance(actual, dict) or actual.get("type") != expected_type:
            raise PreflightError(
                f"{env_key}: required property {name!r} must have type {expected_type!r}."
            )
    return props


def validate_relation_graph(schemas: Mapping[str, Mapping[str, Any]], env: Mapping[str, str]) -> None:
    """Raise on any cross-workspace or mismatched relation target."""
    for source_key, property_name, expected_type, target_key in RELATIONS:
        source_schema = schemas[source_key]
        props = _properties(source_schema, source_key)
        prop = props.get(property_name)
        if not isinstance(prop, dict) or prop.get("type") != expected_type:
            raise PreflightError(
                f"{source_key}: {property_name!r} must be a {expected_type} property."
            )
        relation = prop.get("relation")
        actual_target = relation.get("data_source_id") if isinstance(relation, dict) else None
        if not actual_target or normalize_source_id(actual_target) != normalize_source_id(env[target_key]):
            raise PreflightError(
                f"Relation mismatch: {source_key}.{property_name} does not target "
                f"the configured source {target_key}. No records were written."
            )


def run_preflight(
    environ: Optional[Mapping[str, str]] = None,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    env = environ if environ is not None else os.environ
    missing = [key for key in REQUIRED_ENV if not str(env.get(key, "")).strip()]
    if missing:
        raise PreflightError("Missing required environment variables: " + ", ".join(missing))

    db_path = Path(str(env["RESEARCH_RUN_IDEMPOTENCY_DB"]).strip()).expanduser()
    if not db_path.is_absolute():
        raise PreflightError("RESEARCH_RUN_IDEMPOTENCY_DB must be an absolute path on persistent storage.")
    if not db_path.parent.is_dir():
        raise PreflightError("Idempotency database parent directory does not exist; verify the persistent disk mount.")
    if not os.access(str(db_path.parent), os.W_OK):
        raise PreflightError("Idempotency database parent directory is not writable.")

    client = session or requests.Session()
    headers = {
        "Authorization": f"Bearer {env['NOTION_TOKEN']}",
        "Notion-Version": NOTION_VERSION,
        "Accept": "application/json",
    }
    source_keys = (
        "NOTION_ANALYSIS_RUNS_DATA_SOURCE_ID",
        "NOTION_PROJECTS_DATA_SOURCE_ID",
        "NOTION_PROTOCOLS_DATA_SOURCE_ID",
        "NOTION_SAMPLES_DATA_SOURCE_ID",
        "NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID",
        "NOTION_LITERATURE_DATA_SOURCE_ID",
        "NOTION_GENOMIC_SEQUENCE_DATA_SOURCE_ID",
        "NOTION_TASKS_DATA_SOURCE_ID",
        "NOTION_BRAIN_NOTES_DATA_SOURCE_ID",
    )
    schemas: Dict[str, Mapping[str, Any]] = {}
    for key in source_keys:
        source_id = str(env[key]).strip().removeprefix("collection://")
        try:
            response = client.get(
                f"{NOTION_API_URL}/data_sources/{source_id}",
                headers=headers,
                timeout=15,
            )
        except requests.RequestException as exc:
            raise PreflightError(f"Notion schema check failed for {key} ({type(exc).__name__}).") from exc
        if response.status_code != 200:
            raise PreflightError(f"Notion schema check failed for {key} (HTTP {response.status_code}).")
        schema = response.json()
        if normalize_source_id(str(schema.get("id", ""))) != normalize_source_id(source_id):
            raise PreflightError(f"Notion returned an unexpected source ID for {key}.")
        _properties(schema, key)
        schemas[key] = schema

    validate_relation_graph(schemas, env)

    # Initialize/open the ledger to prove that the configured path is writable.
    from modules.research_run_idempotency import RunIdempotencyLedger
    RunIdempotencyLedger(str(db_path))

    return {
        "status": "ready_for_synthetic_staging",
        "data_sources_checked": len(source_keys),
        "relation_edges_checked": len(RELATIONS),
        "idempotency_database": str(db_path),
        "research_records_written": 0,
        "note": "This check does not prove API deployment reachability or multi-worker shared-storage semantics.",
    }


def main() -> int:
    try:
        result = run_preflight()
    except PreflightError as exc:
        print(f"NOT READY: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"NOT READY: unexpected preflight error ({type(exc).__name__}).", file=sys.stderr)
        return 1
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
