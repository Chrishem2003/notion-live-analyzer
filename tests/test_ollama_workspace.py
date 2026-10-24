from unittest.mock import patch

from modules.ollama_workspace import _router


def test_router_uses_server_config_and_ollama_model():
    with patch.dict("os.environ", {
        "OLLAMA_BASE_URL": "https://ollama.example.internal",
        "OLLAMA_MODEL": "qwen2.5:3b",
        "GEMINI_API_KEY": "must-not-be-used",
    }, clear=False):
        router = _router()
    assert router.ollama_base_url == "https://ollama.example.internal"
    assert router.ollama_model == "qwen2.5:3b"
    assert router.gemini_api_key == ""


def test_workspace_requires_authenticated_session(monkeypatch):
    # Import is intentionally light; render path exits before network access.
    import modules.ollama_workspace as workspace

    calls = []
    monkeypatch.setattr(workspace.st, "session_state", {"portal_unlocked": False, "user_identity": {}})
    monkeypatch.setattr(workspace.st, "error", lambda message: calls.append(message))
    workspace.render_ollama_workspace()
    assert calls and "Sign in" in calls[0]

def test_ollama_gateway_token_is_server_side_bearer_header():
    from modules.llm_router import LLMRouter

    with patch.dict("os.environ", {"OLLAMA_API_KEY": "test-secret"}, clear=False):
        router = LLMRouter(gemini_api_key="", ollama_base_url="https://gateway.example.test")
        assert router._ollama_headers() == {"Authorization": "Bearer test-secret"}

    with patch.dict("os.environ", {"OLLAMA_API_KEY": ""}, clear=False):
        router = LLMRouter(gemini_api_key="", ollama_base_url="http://127.0.0.1:11434")
        assert router._ollama_headers() == {}

def test_gateway_rejects_missing_or_wrong_token(monkeypatch):
    from fastapi import HTTPException
    from ollama_gateway import _authorize

    monkeypatch.setenv("OLLAMA_GATEWAY_TOKEN", "x" * 40)
    try:
        _authorize(None)
        assert False, "missing token should be rejected"
    except HTTPException as exc:
        assert exc.status_code == 401

    try:
        _authorize("Bearer wrong-token")
        assert False, "wrong token should be rejected"
    except HTTPException as exc:
        assert exc.status_code == 401


def test_gateway_rejects_weak_or_missing_server_secret(monkeypatch):
    from fastapi import HTTPException
    from ollama_gateway import _configured_token

    monkeypatch.setenv("OLLAMA_GATEWAY_TOKEN", "short")
    try:
        _configured_token()
        assert False, "weak token should be rejected"
    except HTTPException as exc:
        assert exc.status_code == 503
