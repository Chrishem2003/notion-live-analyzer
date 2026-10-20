"""Static safeguards for the Render staging deployment blueprint."""
from pathlib import Path


def test_render_blueprint_exposes_separate_api_service_and_health_check():
    source = Path("render.yaml").read_text(encoding="utf-8")
    assert "name: notion-live-analyzer-api" in source
    assert "dockerCommand: sh scripts/start_research_run_api.sh" in source
    assert "healthCheckPath: /api/v1/health" in source
    assert "RESEARCH_RUN_API_URL" in source
    assert "https://notion-live-analyzer-api.onrender.com" in source
    assert "https://YOUR-APP-URL" not in source
    assert "https://notion-live-analyzer.onrender.com" in source
    assert ".onrender.com.onrender.com" not in source


def test_free_api_service_is_explicitly_synthetic_staging_only():
    source = Path("render.yaml").read_text(encoding="utf-8")
    assert "RESEARCH_RUN_ALLOW_EPHEMERAL_LEDGER" in source
    assert "value: /tmp/research_run_idempotency.sqlite3" in source
    assert "MUST NOT" in source
    assert "Persistent storage and a suitable plan are" in source
    assert "key: NOTION_TOKEN\n        sync: false" in source
    assert "key: PLATFORM_API_KEY\n        sync: false" in source


def test_api_startup_script_runs_read_only_preflight_before_uvicorn():
    source = Path("scripts/start_research_run_api.sh").read_text(encoding="utf-8")
    assert "python scripts/research_run_preflight.py" in source
    assert source.index("python scripts/research_run_preflight.py") < source.index("uvicorn api_server:app")
    assert "exec uvicorn api_server:app" in source



def test_blueprint_does_not_add_unapproved_billable_cron_service():
    source = Path("render.yaml").read_text(encoding="utf-8")
    assert "- type: cron" not in source
    assert "notion-live-analyzer-keepalive" not in source
