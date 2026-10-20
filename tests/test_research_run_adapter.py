"""Tests for the safe Analysis Run write-back adapter."""
import requests
import pytest

from modules.research_run_adapter import (
    AmbiguousWriteError,
    ResearchRunAdapter,
    ResearchRunWriteError,
    build_analysis_run_properties,
)


class Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, post_results=None, get_results=None):
        self.post_results = list(post_results or [])
        self.get_results = list(get_results or [])
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        result = self.post_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        result = self.get_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def page(page_id="page-123"):
    return {"id": page_id, "object": "page", "properties": {}}


def adapter(session):
    return ResearchRunAdapter(
        "test-token", "analysis-db", session=session
    )


def empty_query():
    return Response(200, {"results": []})


def found_query(page_id="page-123"):
    return Response(200, {"results": [{"id": page_id}]})


def test_creates_relation_linked_run_and_verifies_readback():
    session = FakeSession(
        post_results=[
            empty_query(),
            Response(200, page()),
        ],
        get_results=[Response(200, page())],
    )
    result = adapter(session).create_or_get_run(
        "run-001",
        {
            "Name": {"title": [{"text": {"content": "Synthetic run"}}]},
            "Project": {"relation": [{"id": "project-page-id"}]},
            "Input Samples": {"relation": [{"id": "sample-page-id"}]},
        },
    )
    assert result["created"] is True
    assert result["page"]["id"] == "page-123"
    create_call = session.calls[1]
    payload = create_call[2]["json"]
    assert payload["parent"] == {"type": "data_source_id", "data_source_id": "analysis-db"}
    assert payload["properties"]["External Run ID"]["rich_text"][0]["text"]["content"] == "run-001"
    assert payload["properties"]["Project"]["relation"] == [{"id": "project-page-id"}]
    assert session.calls[-1][0] == "GET"


def test_existing_run_is_returned_without_creating_duplicate():
    session = FakeSession(
        post_results=[found_query("existing-page")],
        get_results=[Response(200, page("existing-page"))],
    )
    result = adapter(session).create_or_get_run("run-002", {"Name": {"title": []}})
    assert result["created"] is False
    assert result["page"]["id"] == "existing-page"
    assert len([c for c in session.calls if c[0] == "POST"]) == 1


def test_timeout_recovers_by_stable_id_without_second_create():
    session = FakeSession(
        post_results=[
            empty_query(),
            requests.Timeout("simulated lost response"),
            found_query("recovered-page"),
        ],
        get_results=[Response(200, page("recovered-page"))],
    )
    result = adapter(session).create_or_get_run("run-003", {"Name": {"title": []}})
    assert result["created"] is False
    assert result["page"]["id"] == "recovered-page"
    # Query, attempted create, query-after-timeout. No second create POST.
    assert len([c for c in session.calls if c[0] == "POST"]) == 3
    assert session.calls[1][1].endswith("/pages")


def test_timeout_without_visible_record_is_marked_ambiguous_not_retried():
    session = FakeSession(
        post_results=[empty_query(), requests.Timeout("lost response"), empty_query()]
    )
    with pytest.raises(AmbiguousWriteError):
        adapter(session).create_or_get_run("run-004", {"Name": {"title": []}})
    assert len(session.calls) == 3


def test_duplicate_external_ids_block_write():
    session = FakeSession(
        post_results=[Response(200, {"results": [{"id": "a"}, {"id": "b"}]})]
    )
    with pytest.raises(ResearchRunWriteError, match="Duplicate External Run ID"):
        adapter(session).create_or_get_run("run-005", {})


def test_rejects_conflicting_external_run_id():
    session = FakeSession()
    with pytest.raises(ValueError, match="must match"):
        adapter(session).create_or_get_run(
            "run-006",
            {"External Run ID": {"rich_text": [{"text": {"content": "other"}}]}},
        )
    assert session.calls == []


def test_rejects_missing_token_or_database():
    with pytest.raises(ValueError, match="token"):
        ResearchRunAdapter("", "analysis-db")
    with pytest.raises(ValueError, match="database"):
        ResearchRunAdapter("token", "")


def test_http_failure_does_not_silently_report_success():
    session = FakeSession(post_results=[empty_query(), Response(403, {"message": "forbidden"})])
    with pytest.raises(ResearchRunWriteError, match="HTTP 403"):
        adapter(session).create_or_get_run("run-007", {})


def test_payload_builder_uses_canonical_schema_and_safe_initial_gates():
    payload = build_analysis_run_properties(
        run_name="Synthetic smoke test",
        project_page_id="private-project-id",
        protocol_page_id="private-protocol-id",
        input_sample_page_ids=["private-sample-id"],
        input_data_record_page_ids=["private-data-id"],
        code_revision="abc123",
        manifest_hash="sha256:example",
    )
    assert payload["Run Name"]["title"][0]["text"]["content"] == "Synthetic smoke test"
    assert payload["Project"]["relation"] == [{"id": "private-project-id"}]
    assert payload["Protocol"]["relation"] == [{"id": "private-protocol-id"}]
    assert payload["Input Samples"]["relation"] == [{"id": "private-sample-id"}]
    assert payload["Input Data Records"]["relation"] == [{"id": "private-data-id"}]
    assert payload["Run Status"]["select"]["name"] == "Draft"
    assert payload["Workflow Gate"]["select"]["name"] == "Intake"
    assert payload["QC Outcome"]["select"]["name"] == "Pending"
    assert payload["Reproducibility Check"]["select"]["name"] == "Not Checked"
    assert payload["Record Classification"]["select"]["name"] == "Synthetic/Test"
    assert "External Run ID" not in payload  # injected by the adapter from run_id


def test_payload_builder_requires_project_and_protocol_and_valid_relation_ids():
    with pytest.raises(ValueError, match="project_page_id"):
        build_analysis_run_properties(
            run_name="Run", project_page_id=" ", protocol_page_id="protocol"
        )
    with pytest.raises(ValueError, match="protocol_page_id"):
        build_analysis_run_properties(
            run_name="Run", project_page_id="project", protocol_page_id=""
        )
    with pytest.raises(ValueError, match="empty page ID"):
        build_analysis_run_properties(
            run_name="Run", project_page_id="project", protocol_page_id="protocol",
            input_sample_page_ids=[""],
        )
