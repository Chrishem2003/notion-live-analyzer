"""Static safeguards for the Render research-run deployment blueprint."""
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


def test_free_api_service_fails_closed_without_durable_storage():
    source = Path("render.yaml").read_text(encoding="utf-8")
    api_block = source.split("name: notion-live-analyzer-api", 1)[1]

    assert "plan: free" in api_block
    assert "key: RESEARCH_RUN_IDEMPOTENCY_DB\n        value: /var/data/research_run_idempotency.sqlite3" in api_block
    assert "key: RESEARCH_RUN_IDEMPOTENCY_DB\n        value: /tmp/research_run_idempotency.sqlite3" not in api_block
    assert 'key: RESEARCH_RUN_ALLOW_EPHEMERAL_LEDGER\n        value: "false"' in api_block
    assert 'key: RESEARCH_RUN_WRITEBACK_ENABLED\n        value: "false"' in api_block
    assert "Do not enable this API for real research until the disk/database and" in source


def test_api_startup_script_preflights_before_uvicorn_when_writeback_enabled():
    source = Path("scripts/start_research_run_api.sh").read_text(encoding="utf-8")
    default_off = 'if [ "${RESEARCH_RUN_WRITEBACK_ENABLED:-false}" = "true" ]; then'
    assert default_off in source
    assert source.index(default_off) < source.index("python scripts/research_run_preflight.py")
    assert source.index("python scripts/research_run_preflight.py") < source.index("uvicorn api_server:app")
    assert "exec uvicorn api_server:app" in source


def test_blueprint_does_not_add_unapproved_billable_cron_service():
    source = Path("render.yaml").read_text(encoding="utf-8")
    assert "- type: cron" not in source
    assert "notion-live-analyzer-keepalive" not in source


def test_api_service_uses_dedicated_lightweight_runtime_image():
    blueprint = Path("render.yaml").read_text(encoding="utf-8")
    api_block = blueprint.split("name: notion-live-analyzer-api", 1)[1]
    assert "dockerfilePath: ./Dockerfile.api" in api_block
    assert "dockerfilePath: ./Dockerfile\n" not in api_block

    dockerfile = Path("Dockerfile.api").read_text(encoding="utf-8")
    assert "COPY requirements-api.txt ." in dockerfile
    assert "pip install --no-cache-dir -r requirements-api.txt" in dockerfile
    assert "scripts/start_research_run_api.sh" in dockerfile

    requirements = Path("requirements-api.txt").read_text(encoding="utf-8")
    for package in ("fastapi", "uvicorn[standard]", "requests", "celery[redis]", "redis", "pycrdt"):
        assert package in requirements
    assert "scikit-learn" not in requirements
    assert "streamlit>=" not in requirements
