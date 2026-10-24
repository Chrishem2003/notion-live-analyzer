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
