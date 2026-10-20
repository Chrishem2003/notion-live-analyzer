"""HTTP contract tests for the authenticated research-run endpoint.

All Notion operations are mocked; these tests never write to a live workspace.
"""
import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api(monkeypatch, tmp_path):
    monkeypatch.setenv("PLATFORM_API_KEY", "test-platform-key")
    import api_server
    api_server = importlib.reload(api_server)
    api_server.API_KEY = "test-platform-key"

    required = {
        "NOTION_TOKEN": "test-notion-token",
        "NOTION_ANALYSIS_RUNS_DATA_SOURCE_ID": "private-runs",
        "NOTION_PROJECTS_DATA_SOURCE_ID": "private-projects",
        "NOTION_PROTOCOLS_DATA_SOURCE_ID": "private-protocols",
        "NOTION_SAMPLES_DATA_SOURCE_ID": "private-samples",
        "NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID": "private-data",
        "NOTION_LITERATURE_DATA_SOURCE_ID": "private-literature",
        "RESEARCH_RUN_IDEMPOTENCY_DB": str(tmp_path / "runs.sqlite3"),
    }
    for key, value in required.items():
        monkeypatch.setenv(key, value)
    return api_server, TestClient(api_server.app), required


def request_payload():
    return {
        "run_id": "synthetic-api-test-001",
        "run_name": "Synthetic endpoint smoke test",
        "project_page_id": "project-page",
        "protocol_page_id": "protocol-page",
        "input_sample_page_ids": ["sample-page"],
        "input_data_record_page_ids": ["data-page"],
        "source_evidence_page_ids": ["literature-page"],
        "input_dataset_version": "demo-v1",
        "analysis_method": "mock validation",
        "code_revision": "test-commit",
        "environment": "staging",
        "manifest_hash": "sha256:test",
        "parameters_json": "{\"synthetic\":true}",
    }


def test_endpoint_requires_api_key(api):
    _, client, _ = api
    response = client.post("/api/v1/research-runs", json=request_payload())
    assert response.status_code == 401


def test_endpoint_fails_closed_when_notion_config_is_missing(api, monkeypatch):
    _, client, _ = api
    monkeypatch.delenv("NOTION_TOKEN")
    response = client.post(
        "/api/v1/research-runs",
        headers={"X-API-Key": "test-platform-key"},
        json=request_payload(),
    )
    assert response.status_code == 503
    assert "NOTION_TOKEN" in response.json()["detail"]["missing"]


def test_endpoint_fails_closed_when_literature_source_is_missing(api, monkeypatch):
    _, client, _ = api
    monkeypatch.delenv("NOTION_LITERATURE_DATA_SOURCE_ID")
    response = client.post(
        "/api/v1/research-runs",
        headers={"X-API-Key": "test-platform-key"},
        json=request_payload(),
    )
    assert response.status_code == 503
    assert "NOTION_LITERATURE_DATA_SOURCE_ID" in response.json()["detail"]["missing"]


def test_endpoint_validates_private_relations_and_returns_verified_run(api, monkeypatch):
    api_server, client, _ = api
    import modules.research_run_adapter as adapter_module
    import modules.research_run_idempotency as ledger_module

    checked_relations = []

    class FakeAdapter:
        def __init__(self, token, data_source_id):
            assert token == "test-notion-token"
            assert data_source_id == "private-runs"
            self.checked = []

        def validate_page_parent(self, page_id, expected_data_source_id, label):
            self.checked.append((page_id, expected_data_source_id, label))
            checked_relations.append((page_id, expected_data_source_id, label))
            return {"id": page_id}

        def create_or_get_run(self, run_id, properties):
            assert run_id == "synthetic-api-test-001"
            assert properties["Record Classification"]["select"]["name"] == "Synthetic/Test"
            assert properties["Source Evidence"]["relation"] == [{"id": "literature-page"}]
            assert properties["Input Dataset Version"]["rich_text"][0]["text"]["content"] == "demo-v1"
            return {"created": True, "page": {
                "id": "created-page", "url": "https://notion.example/synthetic-run"
            }}

        def get_page(self, page_id):
            return {"id": page_id, "url": "https://notion.example/synthetic-run"}

    class FakeLedger:
        def __init__(self, database_path):
            assert database_path.endswith("runs.sqlite3")

        def reserve(self, run_id, properties):
            return {"action": "reserved", "page_id": None}

        def mark_complete(self, run_id, page_id):
            assert run_id == "synthetic-api-test-001"
            assert page_id == "created-page"

        def mark_ambiguous(self, run_id):
            raise AssertionError("No ambiguous write expected")

        def mark_failed(self, run_id):
            raise AssertionError("No failed write expected")

    monkeypatch.setattr(adapter_module, "ResearchRunAdapter", FakeAdapter)
    monkeypatch.setattr(ledger_module, "RunIdempotencyLedger", FakeLedger)
    response = client.post(
        "/api/v1/research-runs",
        headers={"X-API-Key": "test-platform-key"},
        json=request_payload(),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(checked_relations) == {
        ("project-page", "private-projects", "Project"),
        ("protocol-page", "private-protocols", "Protocol"),
        ("sample-page", "private-samples", "Input Sample"),
        ("data-page", "private-data", "Input Data Record"),
        ("literature-page", "private-literature", "Source Evidence"),
    }
    assert body == {
        "created": True,
        "run_id": "synthetic-api-test-001",
        "page_id": "created-page",
        "page_url": "https://notion.example/synthetic-run",
        "run_status": "Draft",
        "workflow_gate": "Intake",
        "qc_outcome": "Pending",
        "record_classification": "Synthetic/Test",
    }
