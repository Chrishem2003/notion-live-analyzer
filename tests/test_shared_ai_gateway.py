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
