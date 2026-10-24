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
