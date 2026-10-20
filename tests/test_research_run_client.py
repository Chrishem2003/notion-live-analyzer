"""Tests for the Streamlit-facing research-run API client."""
import requests
import pytest

from modules.research_run_client import ResearchRunClient, ResearchRunClientError


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload or {}

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def payload():
    return {"run_id": "synthetic-run-1", "run_name": "Synthetic run"}


def test_client_posts_to_authenticated_endpoint_without_auto_retry():
    session = FakeSession([FakeResponse(200, {
        "run_id": "synthetic-run-1", "page_id": "notion-page-1",
        "page_url": "https://notion.example/run",
    })])
    client = ResearchRunClient("https://api.example/", "secret-test", session=session)
    result = client.create_run(payload())

    assert result["page_id"] == "notion-page-1"
    assert len(session.calls) == 1
    url, kwargs = session.calls[0]
    assert url == "https://api.example/api/v1/research-runs"
    assert kwargs["headers"]["X-API-Key"] == "secret-test"
    assert kwargs["json"] == payload()
    assert kwargs["timeout"] == 20.0


def test_client_requires_server_config_and_absolute_http_url():
    with pytest.raises(ValueError, match="URL"):
        ResearchRunClient("", "key")
    with pytest.raises(ValueError, match="HTTP"):
        ResearchRunClient("file:///tmp/api", "key")
    with pytest.raises(ValueError, match="PLATFORM_API_KEY"):
        ResearchRunClient("https://api.example", "")


def test_client_does_not_automatically_retry_ambiguous_timeout():
    session = FakeSession([requests.Timeout("lost response")])
    client = ResearchRunClient("https://api.example", "key", session=session)
    with pytest.raises(ResearchRunClientError, match="same run_id"):
        client.create_run(payload())
    assert len(session.calls) == 1


def test_client_surfaces_http_error_without_exposing_api_key():
    session = FakeSession([FakeResponse(409, {
        "detail": "This run_id was already reserved with a different payload."
    })])
    client = ResearchRunClient("https://api.example", "do-not-print-this", session=session)
    with pytest.raises(ResearchRunClientError, match="HTTP 409") as exc:
        client.create_run(payload())
    assert "do-not-print-this" not in str(exc.value)


def test_client_rejects_success_response_without_persisted_page_id():
    client = ResearchRunClient(
        "https://api.example", "key",
        session=FakeSession([FakeResponse(200, {"run_id": "synthetic-run-1"})]),
    )
    with pytest.raises(ResearchRunClientError, match="page_id"):
        client.create_run(payload())
