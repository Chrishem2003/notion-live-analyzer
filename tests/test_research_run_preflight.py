"""Tests for deployment preflight; all Notion HTTP calls are mocked."""
from pathlib import Path

import pytest

from scripts.research_run_preflight import PreflightError, run_preflight


SOURCE_KEYS = {
    "NOTION_ANALYSIS_RUNS_DATA_SOURCE_ID": "runs-source",
    "NOTION_PROJECTS_DATA_SOURCE_ID": "projects-source",
    "NOTION_PROTOCOLS_DATA_SOURCE_ID": "protocols-source",
    "NOTION_SAMPLES_DATA_SOURCE_ID": "samples-source",
    "NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID": "data-source",
    "NOTION_LITERATURE_DATA_SOURCE_ID": "literature-source",
    "NOTION_GENOMIC_SEQUENCE_DATA_SOURCE_ID": "genomic-source",
    "NOTION_TASKS_DATA_SOURCE_ID": "tasks-source",
    "NOTION_BRAIN_NOTES_DATA_SOURCE_ID": "brain-source",
}


class Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class Session:
    def __init__(self, schemas):
        self.schemas = schemas
        self.calls = []

    def get(self, url, headers, timeout):
        self.calls.append((url, headers, timeout))
        source_id = url.rsplit("/", 1)[-1]
        return Response(200, self.schemas[source_id])


def env_for(tmp_path):
    return {
        "PLATFORM_API_KEY": "test-api-key",
        "NOTION_TOKEN": "test-notion-token",
        **SOURCE_KEYS,
        "RESEARCH_RUN_IDEMPOTENCY_DB": str(tmp_path / "persistent" / "runs.sqlite3"),
        "RESEARCH_RUN_ALLOW_EPHEMERAL_LEDGER": "true",
    }


def schema(source_id, properties):
    return {"id": source_id, "properties": properties}


def relation(target):
    return {"type": "relation", "relation": {"data_source_id": target}}


def text_type(kind):
    return {"type": kind}


def valid_schemas():
    return {
        "runs-source": schema("runs-source", {
            "Run Name": text_type("title"),
            "External Run ID": text_type("rich_text"),
            "Project": relation("projects-source"),
            "Protocol": relation("protocols-source"),
            "Input Samples": relation("samples-source"),
            "Input Data Records": relation("data-source"),
            "Input Dataset Version": text_type("rich_text"),
            "Source Evidence": relation("literature-source"),
            "Run Status": text_type("select"),
            "Workflow Gate": text_type("select"),
            "QC Outcome": text_type("select"),
            "Record Classification": text_type("select"),
            "Reproducibility Check": text_type("select"),
        }),
        "projects-source": schema("projects-source", {
            "Project Name": text_type("title"),
            "Daily Task": relation("tasks-source"),
            "Literature & Sources": relation("literature-source"),
        }),
        "protocols-source": schema("protocols-source", {
            "Protocol Name": text_type("title"),
            "Project": relation("projects-source"),
            "Source Evidence": relation("literature-source"),
        }),
        "samples-source": schema("samples-source", {
            "Sample Name": text_type("title"),
            "Project": relation("projects-source"),
            "Protocol": relation("protocols-source"),
            "Literature": relation("literature-source"),
        }),
        "data-source": schema("data-source", {
            "Project": relation("projects-source"),
            "Protocol": relation("protocols-source"),
            "Sample": relation("samples-source"),
            "Source Evidence": relation("literature-source"),
            "🧬 Genomic Sequence Log": relation("genomic-source"),
        }),
        "literature-source": schema("literature-source", {
            "Paper Name": text_type("title"),
            "Project Master": relation("projects-source"),
            "Literature & Sources": relation("brain-source"),
        }),
        "genomic-source": schema("genomic-source", {
            "🧪 Project Master": relation("projects-source"),
            "Genomic Sequence Log": relation("data-source"),
        }),
        "tasks-source": schema("tasks-source", {
            "Project Master": relation("projects-source"),
        }),
        "brain-source": schema("brain-source", {
            "📄Literature\u00a0": relation("literature-source"),
        }),
    }


def test_preflight_checks_all_sources_and_relation_edges(tmp_path):
    env = env_for(tmp_path)
    Path(env["RESEARCH_RUN_IDEMPOTENCY_DB"]).parent.mkdir(parents=True)
    session = Session(valid_schemas())

    result = run_preflight(env, session)

    assert result["status"] == "ready_for_synthetic_staging"
    assert result["data_sources_checked"] == 9
    assert result["relation_edges_checked"] == 23
    assert result["research_records_written"] == 0
    assert len(session.calls) == 9
    assert all(call[1]["Notion-Version"] == "2025-09-03" for call in session.calls)
    assert Path(env["RESEARCH_RUN_IDEMPOTENCY_DB"]).exists()


def test_preflight_fails_closed_on_cross_workspace_relation(tmp_path):
    env = env_for(tmp_path)
    Path(env["RESEARCH_RUN_IDEMPOTENCY_DB"]).parent.mkdir(parents=True)
    schemas = valid_schemas()
    schemas["samples-source"]["properties"]["Project"] = relation("template-projects")
    with pytest.raises(PreflightError, match="Relation mismatch"):
        run_preflight(env, Session(schemas))


def test_preflight_rejects_missing_configuration(tmp_path):
    env = env_for(tmp_path)
    env["NOTION_TOKEN"] = ""
    with pytest.raises(PreflightError, match="NOTION_TOKEN"):
        run_preflight(env, Session(valid_schemas()))


def test_preflight_requires_absolute_persistent_ledger_path(tmp_path):
    env = env_for(tmp_path)
    env["RESEARCH_RUN_IDEMPOTENCY_DB"] = "./runs.sqlite3"
    with pytest.raises(PreflightError, match="absolute path"):
        run_preflight(env, Session(valid_schemas()))


def test_preflight_rejects_missing_relation_property(tmp_path):
    env = env_for(tmp_path)
    Path(env["RESEARCH_RUN_IDEMPOTENCY_DB"]).parent.mkdir(parents=True)
    schemas = valid_schemas()
    del schemas["samples-source"]["properties"]["Protocol"]
    with pytest.raises(PreflightError, match="Protocol"):
        run_preflight(env, Session(schemas))


def test_preflight_rejects_ephemeral_ledger_without_staging_override(tmp_path):
    env = env_for(tmp_path)
    env["RESEARCH_RUN_IDEMPOTENCY_DB"] = "/tmp/research-run-ledger.sqlite3"
    env["RESEARCH_RUN_ALLOW_EPHEMERAL_LEDGER"] = "false"
    with pytest.raises(PreflightError, match="ephemeral"):
        run_preflight(env, Session(valid_schemas()))
