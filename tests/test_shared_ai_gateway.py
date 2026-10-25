import hashlib
import hmac
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient

import shared_ai_gateway as gateway

def client():
    app = FastAPI()
    app.include_router(gateway.router)
    return TestClient(app)

def test_gateway_requires_signed_user_token(monkeypatch):
    monkeypatch.setenv("SHARED_AI_GATEWAY_ENABLED", "true")
    response = client().post("/api/v1/ai/respond", json={
        "product": "sovereign_intelligence", "task": "help", "input": "hello"
    })
    assert response.status_code == 401

def test_gateway_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SHARED_AI_GATEWAY_ENABLED", raising=False)
    monkeypatch.setattr(gateway, "verify_chat_token", lambda token: "user@example.com")
    response = client().post("/api/v1/ai/respond",
        headers={"Authorization": "Bearer test-token"},
        json={"product": "sovereign_intelligence", "task": "help", "input": "hello"})
    assert response.status_code == 503
    assert "disabled" in response.json()["detail"].lower()

def test_automation_draft_is_schema_validated_and_never_executed(monkeypatch):
    monkeypatch.setenv("SHARED_AI_GATEWAY_ENABLED", "true")
    monkeypatch.setattr(gateway, "verify_chat_token", lambda token: "user@example.com")
    monkeypatch.setattr(gateway, "_ensure_enabled", lambda actor: None)
    monkeypatch.setattr(gateway, "_generate", lambda *args, **kwargs: {
        "provider": "ollama", "model": "qwen2.5:3b", "output": json.dumps({
            "title": "New lead follow-up",
            "trigger": "A new lead is created",
            "steps": [{"id":"step_1","type":"trigger","description":"Receive new lead",
                       "connector":None,"inputs":{},"requires_approval":False}],
            "error_handling": ["Stop and notify an administrator"],
            "permissions_required": ["CRM read/write"],
            "approval_required": False,
            "risk_level": "medium",
            "test_plan": ["Use a synthetic lead"],
            "assumptions": ["CRM connector is configured"]
        }), "usage": {}})
    response = client().post("/api/v1/automations/draft",
        headers={"Authorization": "Bearer test-token"},
        json={"description":"When a lead arrives, create a follow-up task."})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "draft_only"
    assert data["executed"] is False
    assert data["draft"]["approval_required"] is True
    assert data["draft"]["steps"][0]["requires_approval"] is True

def test_automation_draft_rejects_invalid_model_json(monkeypatch):
    monkeypatch.setenv("SHARED_AI_GATEWAY_ENABLED", "true")
    monkeypatch.setattr(gateway, "verify_chat_token", lambda token: "user@example.com")
    monkeypatch.setattr(gateway, "_ensure_enabled", lambda actor: None)
    monkeypatch.setattr(gateway, "_generate", lambda *args, **kwargs: {
        "provider": "ollama", "model": "qwen2.5:3b", "output": "not json", "usage": {}})
    response = client().post("/api/v1/automations/draft",
        headers={"Authorization": "Bearer test-token"},
        json={"description":"Build an automation"})
    assert response.status_code == 502
    assert "nothing was saved or executed" in response.json()["detail"].lower()

def test_supabase_jwt_is_validated_by_auth_service(monkeypatch):
    class Response:
        status_code = 200
        def json(self):
            return {"id": "user-123", "email": "person@example.com"}

    def reject_hmac(_token):
        raise gateway.ChatAuthError("not a chat token")

    monkeypatch.setattr(gateway, "verify_chat_token", reject_hmac)
    monkeypatch.setattr(gateway.requests, "get", lambda *args, **kwargs: Response())
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")
    assert gateway.require_user("Bearer supabase-user-token") == "supabase:user-123"

def test_supabase_jwt_requires_https_identity_endpoint(monkeypatch):
    def reject_hmac(_token):
        raise gateway.ChatAuthError("not a chat token")

    monkeypatch.setattr(gateway, "verify_chat_token", reject_hmac)
    monkeypatch.setenv("SUPABASE_URL", "http://untrusted.example")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")
    from fastapi import HTTPException
    try:
        gateway.require_user("Bearer supabase-user-token")
        assert False, "Expected authentication rejection"
    except HTTPException as exc:
        assert exc.status_code == 401

def test_json_parser_accepts_fenced_json():
    from shared_ai_gateway import _parse_json_object
    assert _parse_json_object(chr(96) * 3 + 'json\n{"ok": true}\n' + chr(96) * 3) == {"ok": True}


def test_enabled_gateway_requires_distributed_rate_limit_backend(monkeypatch):
    monkeypatch.setenv("SHARED_AI_GATEWAY_ENABLED", "true")
    monkeypatch.delenv("AI_GATEWAY_REDIS_URL", raising=False)
    from fastapi import HTTPException
    try:
        gateway._ensure_enabled("user@example.com")
        assert False, "Expected fail-closed quota configuration"
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "rate-limit" in exc.detail.lower()

def test_distributed_rate_limit_returns_429_after_limit(monkeypatch):
    class FakeRedis:
        def eval(self, *args):
            return 2

    monkeypatch.setenv("AI_GATEWAY_REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("AI_GATEWAY_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setattr(gateway.redis.Redis, "from_url", lambda *args, **kwargs: FakeRedis())
    from fastapi import HTTPException
    try:
        gateway._consume_rate_limit("user@example.com")
        assert False, "Expected rate-limit rejection"
    except HTTPException as exc:
        assert exc.status_code == 429


def test_ai_response_audit_logs_metadata_without_prompt(monkeypatch, caplog):
    monkeypatch.setenv("SHARED_AI_GATEWAY_ENABLED", "true")
    monkeypatch.setattr(gateway, "verify_chat_token", lambda token: "person@example.com")
    monkeypatch.setattr(gateway, "_ensure_enabled", lambda actor: None)
    monkeypatch.setattr(gateway, "_generate", lambda *args, **kwargs: {
        "provider": "ollama", "model": "qwen2.5:3b", "output": "safe answer", "usage": {}
    })
    caplog.set_level("INFO", logger="shared_ai_gateway")
    secret_prompt = "private-case-detail-do-not-log"
    response = client().post(
        "/api/v1/ai/respond",
        headers={"Authorization": "Bearer test-token"},
        json={"product": "bio_research", "task": "summarize", "input": secret_prompt},
    )
    assert response.status_code == 200
    assert "shared_ai_audit event=ai.respond" in caplog.text
    assert "actor_hash=" in caplog.text
    assert "success" in caplog.text
    assert secret_prompt not in caplog.text
    assert "person@example.com" not in caplog.text



def test_request_cannot_spoof_actor_identity(monkeypatch):
    monkeypatch.setenv("SHARED_AI_GATEWAY_ENABLED", "true")
    actors = {
        "alice-token": "alice@example.com",
        "bob-token": "bob@example.com",
    }
    monkeypatch.setattr(
        gateway, "verify_chat_token",
        lambda token: actors[token] if token in actors else (_ for _ in ()).throw(gateway.ChatAuthError("invalid")),
    )
    monkeypatch.setattr(gateway, "_ensure_enabled", lambda actor: None)
    monkeypatch.setattr(gateway, "_generate", lambda *args, **kwargs: {
        "provider": "ollama", "model": "qwen2.5:3b", "output": "ok", "usage": {}
    })

    app_client = client()
    alice = app_client.post(
        "/api/v1/ai/respond",
        headers={"Authorization": "Bearer alice-token"},
        json={
            "product": "platform_general",
            "task": "help",
            "input": "hello",
            "user_id": "bob",
            "email": "bob@example.com",
            "actor": "bob@example.com",
        },
    )
    bob = app_client.post(
        "/api/v1/ai/respond",
        headers={"Authorization": "Bearer bob-token"},
        json={"product": "platform_general", "task": "help", "input": "hello"},
    )

    assert alice.status_code == 200
    assert bob.status_code == 200
    assert alice.json()["actor"] == "alice@example.com"
    assert bob.json()["actor"] == "bob@example.com"
    assert alice.json()["actor"] != bob.json()["actor"]


def test_ai_request_rejects_oversized_input(monkeypatch):
    monkeypatch.setenv("SHARED_AI_GATEWAY_ENABLED", "true")
    monkeypatch.setattr(gateway, "verify_chat_token", lambda token: "user@example.com")
    monkeypatch.setattr(gateway, "_ensure_enabled", lambda actor: None)
    response = client().post(
        "/api/v1/ai/respond",
        headers={"Authorization": "Bearer test-token"},
        json={"product": "platform_general", "task": "help", "input": "x" * 12001},
    )
    assert response.status_code == 422

def test_audit_actor_pseudonym_is_keyed_and_stable(monkeypatch, caplog):
    monkeypatch.setenv("CHAT_TOKEN_SECRET", "test-key-one")
    caplog.set_level("INFO", logger="shared_ai_gateway")
    gateway._audit_event("test.event", "alice@example.com", "platform_general", "help", "success")
    first_line = caplog.text.splitlines()[-1]
    first_hash = first_line.split("actor_hash=")[1].split()[0]

    caplog.clear()
    gateway._audit_event("test.event", "alice@example.com", "platform_general", "help", "success")
    second_hash = caplog.text.splitlines()[-1].split("actor_hash=")[1].split()[0]

    assert first_hash == second_hash
    assert first_hash != "unavailable"
    assert "alice@example.com" not in caplog.text


def test_audit_actor_pseudonym_changes_with_secret_and_fails_closed_without_it(monkeypatch, caplog):
    caplog.set_level("INFO", logger="shared_ai_gateway")
    monkeypatch.setenv("CHAT_TOKEN_SECRET", "test-key-one")
    gateway._audit_event("test.event", "alice@example.com", "platform_general", "help", "success")
    first_hash = caplog.text.split("actor_hash=")[1].split()[0]

    caplog.clear()
    monkeypatch.setenv("CHAT_TOKEN_SECRET", "test-key-two")
    gateway._audit_event("test.event", "alice@example.com", "platform_general", "help", "success")
    rotated_hash = caplog.text.split("actor_hash=")[1].split()[0]
    assert rotated_hash != first_hash
    assert "alice@example.com" not in caplog.text

    caplog.clear()
    monkeypatch.delenv("CHAT_TOKEN_SECRET", raising=False)
    gateway._audit_event("test.event", "alice@example.com", "platform_general", "help", "success")
    assert "actor_hash=unavailable" in caplog.text
    assert "alice@example.com" not in caplog.text


def test_supabase_rate_limit_rpc_returns_429_after_limit(monkeypatch):
    monkeypatch.setenv("CHAT_TOKEN_SECRET", "test-quota-hash-secret")
    class Response:
        status_code = 200
        def json(self):
            return 2

    captured = {}
    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.delenv("AI_GATEWAY_REDIS_URL", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("AI_GATEWAY_SUPABASE_SERVICE_ROLE_KEY", "server-only-test-key")
    monkeypatch.setenv("AI_GATEWAY_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setattr(gateway.requests, "post", fake_post)
    from fastapi import HTTPException
    try:
        gateway._consume_rate_limit("user@example.com")
        assert False, "Expected rate-limit rejection"
    except HTTPException as exc:
        assert exc.status_code == 429
    assert captured["url"] == "https://project.supabase.co/rest/v1/rpc/consume_shared_ai_rate_limit"
    assert captured["json"]["p_limit"] == 1
    assert len(captured["json"]["p_actor_hash"]) == 64
    expected_hash = hmac.new(
        b"test-quota-hash-secret", b"user@example.com", hashlib.sha256
    ).hexdigest()
    assert captured["json"]["p_actor_hash"] == expected_hash
    assert "user@example.com" not in str(captured["json"])


def test_supabase_rate_limit_fails_closed_on_malformed_counter(monkeypatch):
    monkeypatch.setenv("CHAT_TOKEN_SECRET", "test-quota-hash-secret")
    class Response:
        status_code = 200
        def json(self):
            return True  # bool is an int subclass in Python; it must not be accepted as a counter.

    monkeypatch.delenv("AI_GATEWAY_REDIS_URL", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("AI_GATEWAY_SUPABASE_SERVICE_ROLE_KEY", "server-only-test-key")
    monkeypatch.setattr(gateway.requests, "post", lambda *args, **kwargs: Response())
    from fastapi import HTTPException
    try:
        gateway._consume_rate_limit("user@example.com")
        assert False, "Expected malformed quota result to fail closed"
    except HTTPException as exc:
        assert exc.status_code == 503


def test_rate_limit_fails_closed_without_hashing_secret(monkeypatch):
    monkeypatch.delenv("AI_GATEWAY_REDIS_URL", raising=False)
    monkeypatch.delenv("CHAT_TOKEN_SECRET", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("AI_GATEWAY_SUPABASE_SERVICE_ROLE_KEY", "server-only-test-key")
    monkeypatch.setattr(
        gateway.requests, "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not send unkeyed actor hashes")),
    )
    from fastapi import HTTPException
    try:
        gateway._consume_rate_limit("user@example.com")
        assert False, "Expected missing hashing secret to fail closed"
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "hashing secret" in exc.detail.lower()


def test_supabase_rate_limit_fails_closed_on_rpc_error(monkeypatch):
    monkeypatch.setenv("CHAT_TOKEN_SECRET", "test-quota-hash-secret")
    class Response:
        status_code = 500
        def json(self):
            return {"message": "failure"}

    monkeypatch.delenv("AI_GATEWAY_REDIS_URL", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("AI_GATEWAY_SUPABASE_SERVICE_ROLE_KEY", "server-only-test-key")
    monkeypatch.setattr(gateway.requests, "post", lambda *args, **kwargs: Response())
    from fastapi import HTTPException
    try:
        gateway._consume_rate_limit("user@example.com")
        assert False, "Expected rate-limit backend failure"
    except HTTPException as exc:
        assert exc.status_code == 503

def test_distributed_rate_limit_returns_429_after_limit(monkeypatch):
    monkeypatch.setenv("CHAT_TOKEN_SECRET", "test-quota-hash-secret")
    class FakeRedis:
        def eval(self, *args):
            return 2

    monkeypatch.setenv("AI_GATEWAY_REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("AI_GATEWAY_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setattr(gateway.redis.Redis, "from_url", lambda *args, **kwargs: FakeRedis())
    from fastapi import HTTPException
    try:
        gateway._consume_rate_limit("user@example.com")
        assert False, "Expected rate-limit rejection"
    except HTTPException as exc:
        assert exc.status_code == 429


def test_shared_ai_client_uses_supabase_bearer_token(monkeypatch):
    from unittest.mock import Mock, patch

    from modules.shared_ai_client import request_shared_ai

    monkeypatch.setenv("SHARED_AI_API_URL", "https://api.example.test")
    response = Mock(status_code=200)
    response.json.return_value = {"output": "draft answer", "provider": "ollama"}
    with patch("modules.shared_ai_client.requests.post", return_value=response) as post:
        result = request_shared_ai(
            product="platform_general",
            task="help",
            input_text="hello",
            access_token="supabase-user-access-token",
        )

    assert result["output"] == "draft answer"
    args, kwargs = post.call_args
    assert args[0] == "https://api.example.test/api/v1/ai/respond"
    assert kwargs["headers"] == {"Authorization": "Bearer supabase-user-access-token"}
    assert kwargs["json"] == {"product": "platform_general", "task": "help", "input": "hello"}
    assert "X-API-Key" not in kwargs["headers"]


def test_shared_ai_client_fails_closed_without_user_token(monkeypatch):
    from unittest.mock import patch

    import pytest
    from modules.shared_ai_client import SharedAIError, request_shared_ai

    monkeypatch.setenv("SHARED_AI_API_URL", "https://api.example.test")
    with patch("modules.shared_ai_client.requests.post") as post:
        with pytest.raises(SharedAIError, match="not configured"):
            request_shared_ai(
                product="platform_general",
                task="help",
                input_text="hello",
                access_token="",
            )
    post.assert_not_called()


def test_shared_ai_client_rejects_remote_http_endpoint(monkeypatch):
    from unittest.mock import patch

    import pytest
    from modules.shared_ai_client import SharedAIError, request_shared_ai

    monkeypatch.setenv("SHARED_AI_API_URL", "http://api.example.test")
    with patch("modules.shared_ai_client.requests.post") as post:
        with pytest.raises(SharedAIError, match="HTTPS"):
            request_shared_ai(
                product="platform_general",
                task="help",
                input_text="hello",
                access_token="user-token",
            )
    post.assert_not_called()


def test_provider_failure_logs_only_safe_diagnostic_metadata(monkeypatch, caplog):
    class FakeProvider:
        default_model = "safe-test-model"
        def generate(self, request):
            raise gateway.ProviderError("contains-secret-and-user-prompt")

    class FakeRegistry:
        def get(self, name):
            return FakeProvider()

    monkeypatch.setattr(gateway.ProviderRegistry, "default", lambda: FakeRegistry())
    monkeypatch.setenv("SOVEREIGN_AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "must-never-be-logged")
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        gateway._generate(
            "platform_general", "test_task", "private-user-prompt",
            "supabase:test-user",
        )

    assert error.value.status_code == 502
    assert "shared_ai_provider_failure" in caplog.text
    assert "provider=openai" in caplog.text
    assert "error_type=ProviderError" in caplog.text
    assert "private-user-prompt" not in caplog.text
    assert "contains-secret-and-user-prompt" not in caplog.text
    assert "must-never-be-logged" not in caplog.text
