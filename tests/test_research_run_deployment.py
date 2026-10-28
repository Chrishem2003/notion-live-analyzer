"""Static and functional safeguards for the Render research-run deployment."""
import os
import subprocess
from pathlib import Path

import pytest


def test_render_blueprint_exposes_separate_api_service_and_health_check():
    source = Path("render.yaml").read_text(encoding="utf-8")
    assert "name: notion-live-analyzer-api" in source
    assert "dockerCommand: sh scripts/start_research_run_api.sh" in source
    assert "healthCheckPath: /api/v1/health" in source
    assert "RESEARCH_RUN_API_URL" in source
    assert "https://notion-live-analyzer-api.onrender.com" in source
    assert "https://YOUR-APP-URL" not in source
    assert "value: https://notion-live-analyzer-api.onrender.com" in source
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


def test_api_startup_script_normalizes_flag_and_preflights_before_uvicorn():
    source = Path("scripts/start_research_run_api.sh").read_text(encoding="utf-8")
    assert "writeback_flag=" in source
    assert 'if [ "$writeback_flag" = "true" ]; then' in source
    assert source.index("writeback_flag=") < source.index("python scripts/research_run_preflight.py")
    assert source.index("python scripts/research_run_preflight.py") < source.index("uvicorn api_server:app")
    assert "exec uvicorn api_server:app" in source


def _run_startup_script(tmp_path, flag):
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "start_research_run_api.sh"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    call_log = tmp_path / "commands.log"

    stubs = {
        "python": '#!/bin/sh\nprintf \'python:%s\\n\' "$*" >> "$CALL_LOG"\nexit 0\n',
        "uvicorn": '#!/bin/sh\nprintf \'uvicorn:%s\\n\' "$*" >> "$CALL_LOG"\nexit 0\n',
    }
    for name, body in stubs.items():
        executable = bin_dir / name
        executable.write_text(body, encoding="utf-8")
        executable.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '/usr/bin:/bin')}"
    env["CALL_LOG"] = str(call_log)
    env["PORT"] = "8123"
    if flag is None:
        env.pop("RESEARCH_RUN_WRITEBACK_ENABLED", None)
    else:
        env["RESEARCH_RUN_WRITEBACK_ENABLED"] = flag

    completed = subprocess.run(
        ["sh", str(script)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return call_log.read_text(encoding="utf-8").splitlines(), completed.stdout


@pytest.mark.parametrize("flag", ["true", "TRUE", "TrUe", " True "])
def test_startup_runs_preflight_for_every_value_api_treats_as_enabled(tmp_path, flag):
    calls, stdout = _run_startup_script(tmp_path, flag)
    assert calls == [
        "python:scripts/research_run_preflight.py",
        "uvicorn:api_server:app --host 0.0.0.0 --port 8123",
    ]
    assert "write-back disabled" not in stdout


@pytest.mark.parametrize("flag", [None, "false", "FALSE", "", "1", "true-ish"])
def test_startup_stays_in_safe_mode_for_non_true_values(tmp_path, flag):
    calls, stdout = _run_startup_script(tmp_path, flag)
    assert calls == ["uvicorn:api_server:app --host 0.0.0.0 --port 8123"]
    assert "Research-run write-back disabled" in stdout


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
