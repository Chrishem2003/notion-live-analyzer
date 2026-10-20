"""Offline tests for the explicit synthetic staging acceptance runner."""
import pytest

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
