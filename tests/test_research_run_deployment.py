"""Static safeguards for the Render staging deployment blueprint."""
from pathlib import Path


def test_render_blueprint_exposes_separate_api_service_and_health_check():
    source = Path("render.yaml").read_text(encoding="utf-8")
    assert "name: notion-live-analyzer-api" in source
    assert "dockerCommand: uvicorn api_server:app" in source
    assert "healthCheckPath: /api/v1/health" in source
    assert "RESEARCH_RUN_API_URL" in source
    assert "https://notion-live-analyzer-api.onrender.com" in source
    assert "https://YOUR-APP-URL" not in source
    assert "https://notion-live-analyzer.onrender.com" in source


def test_free_api_service_is_explicitly_synthetic_staging_only():
    source = Path("render.yaml").read_text(encoding="utf-8")
    assert "RESEARCH_RUN_ALLOW_EPHEMERAL_LEDGER" in source
    assert "value: /tmp/research_run_idempotency.sqlite3" in source
    assert "MUST NOT" in source
    assert "Persistent storage and a suitable plan are" in source
    assert "key: NOTION_TOKEN\n        sync: false" in source
    assert "key: PLATFORM_API_KEY\n        sync: false" in source
