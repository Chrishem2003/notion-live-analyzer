"""Offline tests for the explicit synthetic staging acceptance runner."""
import pytest
import requests

from scripts.research_run_staging_smoke import SmokeTestError, main, run_smoke


class Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def success(created, page_id="synthetic-page"):
    return Response(200, {
        "created": created,
        "run_id": "smoke-run-001",
        "page_id": page_id,
        "page_url": "https://notion.example/synthetic-run",
        "record_classification": "Synthetic/Test",
        "run_status": "Draft",
        "workflow_gate": "Intake",
        "qc_outcome": "Pending",
        "manifest_hash": "sha256:synthetic-test-hash",
    })


def test_smoke_checks_create_retry_and_changed_payload_conflict():
    session = Session([
        success(True),
        success(False),
        Response(409, {"detail": "different payload"}),
    ])
    result = run_smoke(
        base_url="https://staging.example.org",
        api_key="test-key",
        project_page_id="project-page",
        protocol_page_id="protocol-page",
        run_id="smoke-run-001",
        session=session,
    )
    assert result["status"] == "passed"
    assert result["same_id_retry_reused_page"] is True
    assert result["changed_payload_conflict_http_409"] is True
    assert len(session.calls) == 3
    first_payload = session.calls[0][1]["json"]
    retry_payload = session.calls[1][1]["json"]
    conflict_payload = session.calls[2][1]["json"]
    assert first_payload == retry_payload
    assert conflict_payload["run_id"] == first_payload["run_id"]
    assert conflict_payload["analysis_method"] != first_payload["analysis_method"]
    assert all(call[1]["headers"]["X-API-Key"] == "test-key" for call in session.calls)
    assert first_payload["input_sample_page_ids"] == []
    assert first_payload["input_data_record_page_ids"] == []
    assert first_payload["source_evidence_page_ids"] == []
    assert first_payload["parameters_json"] == '{"synthetic":true,"purpose":"staging acceptance"}'


def test_smoke_requires_https_and_does_not_use_live_http():
    with pytest.raises(SmokeTestError, match="HTTPS"):
        run_smoke(
            base_url="http://staging.example.org",
            api_key="test-key",
            project_page_id="project-page",
            protocol_page_id="protocol-page",
            run_id="smoke-run-001",
            session=Session([]),
        )


def test_cli_defaults_to_dry_run(capsys):
    assert main([]) == 0
    assert "no API requests sent" in capsys.readouterr().out



def _invoke(session):
    return run_smoke(
        base_url="https://staging.example.org",
        api_key="test-key",
        project_page_id="project-page",
        protocol_page_id="protocol-page",
        run_id="smoke-run-001",
        session=session,
    )


def test_smoke_stops_after_non_200_initial_response():
    session = Session([Response(503, {"detail": "unavailable"})])
    with pytest.raises(SmokeTestError, match="Initial synthetic run returned HTTP 503"):
        _invoke(session)
    assert len(session.calls) == 1


def test_smoke_rejects_wrong_run_id_before_retry():
    initial = success(True)
    initial.payload["run_id"] = "different-run"
    session = Session([initial])
    with pytest.raises(SmokeTestError, match="matching run ID"):
        _invoke(session)
    assert len(session.calls) == 1


def test_smoke_rejects_non_synthetic_classification_before_retry():
    initial = success(True)
    initial.payload["record_classification"] = "Research"
    session = Session([initial])
    with pytest.raises(SmokeTestError, match="Synthetic/Test classification"):
        _invoke(session)
    assert len(session.calls) == 1


def test_smoke_rejects_retry_that_does_not_reuse_original_page():
    session = Session([success(True), success(False, page_id="different-page")])
    with pytest.raises(SmokeTestError, match="original page"):
        _invoke(session)
    assert len(session.calls) == 2


def test_smoke_requires_changed_payload_conflict_to_be_http_409():
    session = Session([success(True), success(False), Response(200, {"created": False})])
    with pytest.raises(SmokeTestError, match="expected HTTP 409"):
        _invoke(session)
    assert len(session.calls) == 3


def test_smoke_rejects_invalid_json_without_retry():
    class InvalidJSON(Response):
        def json(self):
            raise ValueError("synthetic invalid JSON")

    session = Session([InvalidJSON(200, {})])
    with pytest.raises(SmokeTestError, match="invalid JSON"):
        _invoke(session)
    assert len(session.calls) == 1


def test_smoke_does_not_automatically_retry_request_timeout():
    class TimeoutSession(Session):
        def post(self, url, **kwargs):
            self.calls.append((url, kwargs))
            raise requests.Timeout("synthetic timeout")

    session = TimeoutSession([])
    with pytest.raises(SmokeTestError, match="reuse the same --run-id"):
        _invoke(session)
    assert len(session.calls) == 1


def test_cli_requires_explicit_synthetic_confirmation_before_execution(monkeypatch):
    monkeypatch.delenv("RESEARCH_RUN_SMOKE_CONFIRM_SYNTHETIC", raising=False)
    assert main(["--execute", "--run-id", "smoke-run-001"]) == 2
