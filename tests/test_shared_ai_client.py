from unittest.mock import Mock

import pytest

from modules import shared_ai_client as client


def _response(status=200, payload=None):
    response = Mock()
    response.status_code = status
    response.json.return_value = payload or {}
    return response


def test_automation_draft_sends_bearer_token_and_requires_approval(monkeypatch):
    monkeypatch.setenv("SHARED_AI_API_URL", "https://ai.example.test")
    response = _response(200, {
        "status": "draft_only",
        "executed": False,
        "provider": "test",
        "model": "test-model",
        "draft": {
            "title": "Review incoming reports",
            "trigger": "A report is submitted",
            "steps": [{"id": "step_1", "type": "action", "description": "Classify report", "requires_approval": True}],
            "approval_required": True,
            "risk_level": "low",
            "permissions_required": [],
            "error_handling": [],
            "test_plan": [],
            "assumptions": [],
        },
    })
    calls = []
    monkeypatch.setattr(client.requests, "post", lambda *a, **kw: (calls.append((a, kw)) or response))
    result = client.request_automation_draft(description="Classify reports", access_token="secret-token")
    assert calls[0][1]["headers"]["Authorization"] == "Bearer secret-token"
    assert calls[0][0][0] == "https://ai.example.test/api/v1/automations/draft"
    assert result["executed"] is False
    assert result["draft"]["approval_required"] is True


def test_automation_draft_rejects_unapproved_step(monkeypatch):
    monkeypatch.setenv("SHARED_AI_API_URL", "https://ai.example.test")
    response = _response(200, {
        "status": "draft_only", "executed": False,
        "draft": {
            "title": "Unsafe draft", "steps": [{"description": "Do thing", "requires_approval": False}],
            "approval_required": True, "risk_level": "low",
        },
    })
    monkeypatch.setattr(client.requests, "post", lambda *a, **kw: response)
    with pytest.raises(client.SharedAIError, match="approval gate"):
        client.request_automation_draft(description="Do a thing", access_token="token")


def test_automation_draft_fails_closed_without_token(monkeypatch):
    monkeypatch.setenv("SHARED_AI_API_URL", "https://ai.example.test")
    with pytest.raises(client.SharedAIError, match="not configured"):
        client.request_automation_draft(description="Build a flow", access_token="")


def test_automation_draft_rejects_non_https_remote_url(monkeypatch):
    monkeypatch.setenv("SHARED_AI_API_URL", "http://ai.example.test")
    with pytest.raises(client.SharedAIError, match="HTTPS"):
        client.request_automation_draft(description="Build a flow", access_token="token")


def test_user_job_submission_sends_bearer_and_idempotency(monkeypatch):
    monkeypatch.setenv("SHARED_AI_API_URL", "https://api.example.test")
    response = _response(202, {
        "job_id": "11111111-1111-4111-8111-111111111111",
        "status": "queued",
        "created_at": "now",
        "mode": "user_scoped",
    })
    calls = []
    monkeypatch.setattr(client.requests, "request", lambda *a, **kw: (calls.append((a, kw)) or response))
    result = client.request_user_job(
        prompt="Analyze my data",
        access_token="signed-in-token",
        idempotency_key="retry-safe-key",
    )
    assert calls[0][0] == ("POST", "https://api.example.test/api/v1/user-jobs")
    assert calls[0][1]["headers"]["Authorization"] == "Bearer signed-in-token"
    assert calls[0][1]["headers"]["Idempotency-Key"] == "retry-safe-key"
    assert calls[0][1]["json"]["prompt"] == "Analyze my data"
    assert result["client_idempotency_key"] == "retry-safe-key"


def test_user_job_client_fails_closed_without_token(monkeypatch):
    monkeypatch.setenv("SHARED_AI_API_URL", "https://api.example.test")
    request = Mock()
    monkeypatch.setattr(client.requests, "request", request)
    with pytest.raises(client.SharedAIError, match="not configured"):
        client.request_user_job(prompt="Analyze", access_token="")
    request.assert_not_called()


def test_user_job_client_hides_other_account_as_not_found(monkeypatch):
    monkeypatch.setenv("SHARED_AI_API_URL", "https://api.example.test")
    response = _response(404, {"detail": "Job not found."})
    monkeypatch.setattr(client.requests, "request", lambda *a, **kw: response)
    with pytest.raises(client.SharedAIError, match="not found for this account"):
        client.get_user_job(job_id="22222222-2222-4222-8222-222222222222", access_token="token")


def test_user_job_client_requires_cancel_confirmation(monkeypatch):
    monkeypatch.setenv("SHARED_AI_API_URL", "https://api.example.test")
    response = _response(200, {"job_id": "job-1", "status": "running"})
    monkeypatch.setattr(client.requests, "request", lambda *a, **kw: response)
    with pytest.raises(client.SharedAIError, match="did not confirm"):
        client.cancel_user_job(job_id="job-1", access_token="token")
