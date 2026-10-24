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
    monkeypatch.setattr(gateway.httpx, "get", lambda *args, **kwargs: Response())
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
    assert _parse_json_object('\\`\\`\\`json\\n{"ok": true}\\n\\`\\`\\`') == {"ok": True}
