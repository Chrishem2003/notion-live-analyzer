"""Credential-bearing HTTP clients must reject redirects rather than forward secrets."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from modules.research_run_adapter import ResearchRunAdapter, ResearchRunWriteError
from modules.research_run_client import ResearchRunClient, ResearchRunClientError
from platform_jobs.repository import JobStoreUnavailable, SupabaseJobRepository
from nema_agora.supabase_repository import NemaStorageUnavailableError, SupabaseReadOnlyNemaRepository
from scripts.research_run_preflight import REQUIRED_ENV, PreflightError, run_preflight
import platform_jobs.user_api as user_jobs_api
import shared_ai_gateway


class FakeResponse:
    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = {} if payload is None else payload
        self.content = b"redirect-response"
        self.headers = {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("unexpected test response")


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def get(self, *args, **kwargs):
        self.calls.append(("get", args, kwargs))
        return self.responses.pop(0)

    def post(self, *args, **kwargs):
        self.calls.append(("post", args, kwargs))
        return self.responses.pop(0)

    def request(self, *args, **kwargs):
        self.calls.append(("request", args, kwargs))
        return self.responses.pop(0)

    def close(self):
        return None


def test_research_run_preflight_never_follows_notion_schema_redirect(tmp_path):
    env = {key: f"synthetic-{index}" for index, key in enumerate(REQUIRED_ENV)}
    env.update({
        "NOTION_TOKEN": "synthetic-notion-token",
        "RESEARCH_RUN_IDEMPOTENCY_DB": str(tmp_path / "ledger.sqlite3"),
        "RESEARCH_RUN_ALLOW_EPHEMERAL_LEDGER": "true",
    })
    session = FakeSession([FakeResponse(302)])

    with pytest.raises(PreflightError, match="HTTP 302"):
        run_preflight(environ=env, session=session)

    assert len(session.calls) == 1
    assert session.calls[0][2]["allow_redirects"] is False


def test_research_run_adapter_disables_redirects_for_query_and_create():
    session = FakeSession([FakeResponse(200, {"results": []}), FakeResponse(302)])
    adapter = ResearchRunAdapter(
        token="synthetic-notion-token",
        data_source_id="synthetic-data-source",
        session=session,
    )

    with pytest.raises(ResearchRunWriteError, match="HTTP 302"):
        adapter.create_or_get_run("synthetic-run-redirect-001", {})

    assert [call[0] for call in session.calls] == ["post", "post"]
    assert all(call[2]["allow_redirects"] is False for call in session.calls)


def test_research_run_api_client_never_forwards_service_key_on_redirect():
    session = FakeSession([FakeResponse(302)])
    client = ResearchRunClient(
        base_url="https://api.example.test",
        api_key="synthetic-api-key",
        session=session,
    )

    with pytest.raises(ResearchRunClientError, match="HTTP 302"):
        client.create_run({"run_id": "synthetic-run-redirect-002"})

    assert len(session.calls) == 1
    assert session.calls[0][2]["allow_redirects"] is False


def test_platform_jobs_repository_rejects_supabase_redirect(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.example.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "synthetic-service-role")
    session = FakeSession([FakeResponse(302)])
    repository = SupabaseJobRepository(session=session)

    with pytest.raises(JobStoreUnavailable, match="unexpected redirect"):
        repository.get_job("00000000-0000-4000-8000-000000000001")

    assert len(session.calls) == 1
    assert session.calls[0][2]["allow_redirects"] is False


def test_nema_repository_rejects_supabase_redirect(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.example.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "synthetic-service-role")
    session = FakeSession([FakeResponse(302)])
    repository = SupabaseReadOnlyNemaRepository(session=session)

    with pytest.raises(NemaStorageUnavailableError, match="unexpected redirect"):
        repository.list_cases()

    assert len(session.calls) == 1
    assert session.calls[0][2]["allow_redirects"] is False


def test_user_jobs_auth_rejects_supabase_redirect(monkeypatch):
    monkeypatch.setenv("USER_JOB_API_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.example.test")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "synthetic-publishable-key")
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(302)

    monkeypatch.setattr(user_jobs_api.requests, "get", fake_get)

    with pytest.raises(HTTPException) as exc:
        user_jobs_api._verified_user("Bearer synthetic-user-token")

    assert exc.value.status_code == 503
    assert len(calls) == 1
    assert calls[0][1]["allow_redirects"] is False


def test_shared_ai_user_auth_rejects_supabase_redirect(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.example.test")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "synthetic-publishable-key")

    def reject_chat_token(_token):
        raise shared_ai_gateway.ChatAuthError("synthetic invalid token")

    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(302)

    monkeypatch.setattr(shared_ai_gateway, "verify_chat_token", reject_chat_token)
    monkeypatch.setattr(shared_ai_gateway.requests, "get", fake_get)

    with pytest.raises(HTTPException) as exc:
        shared_ai_gateway.require_user("Bearer synthetic-user-token")

    assert exc.value.status_code == 503
    assert len(calls) == 1
    assert calls[0][1]["allow_redirects"] is False


def test_shared_ai_rate_limit_rpc_rejects_supabase_redirect(monkeypatch):
    monkeypatch.setenv("CHAT_TOKEN_SECRET", "synthetic-audit-secret")
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.example.test")
    monkeypatch.setenv("AI_GATEWAY_SUPABASE_SERVICE_ROLE_KEY", "synthetic-service-role")
    monkeypatch.delenv("AI_GATEWAY_REDIS_URL", raising=False)
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(302)

    monkeypatch.setattr(shared_ai_gateway.requests, "post", fake_post)

    with pytest.raises(HTTPException) as exc:
        shared_ai_gateway._consume_rate_limit("synthetic-actor")

    assert exc.value.status_code == 503
    assert len(calls) == 1
    assert calls[0][1]["allow_redirects"] is False
