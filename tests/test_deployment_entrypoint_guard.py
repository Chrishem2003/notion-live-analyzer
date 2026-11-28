"""Static deployment-entrypoint guard for dormant legacy API modules.

These checks validate the checked-in Render/Docker startup contract only.
They do not prove the live service configuration or runtime exposure.
"""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_render_manifest_selects_only_the_reviewed_service_entrypoints():
    manifest = _read("render.yaml")

    assert "name: notion-live-analyzer" in manifest
    assert "dockerfilePath: ./Dockerfile" in manifest
    assert "name: notion-live-analyzer-api" in manifest
    assert "dockerfilePath: ./Dockerfile.api" in manifest
    assert "dockerCommand: sh scripts/start_research_run_api.sh" in manifest

    # These standalone legacy ASGI applications have not passed an auth review.
    assert "fastapi_app:app" not in manifest
    assert "api_gateway:app" not in manifest


def test_streamlit_image_keeps_the_reviewed_streamlit_entrypoint():
    dockerfile = _read("Dockerfile")

    assert "streamlit run app.py" in dockerfile
    assert "uvicorn fastapi_app:app" not in dockerfile
    assert "uvicorn api_gateway:app" not in dockerfile


def test_api_image_uses_the_guarded_research_run_startup_script():
    dockerfile = _read("Dockerfile.api")
    startup = _read("scripts/start_research_run_api.sh")
    manifest = _read("render.yaml")

    assert 'CMD ["sh", "scripts/start_research_run_api.sh"]' in dockerfile
    assert "exec uvicorn api_server:app" in startup
    assert "uvicorn fastapi_app:app" not in startup
    assert "uvicorn api_gateway:app" not in startup

    assert re.search(
        r'- key: RESEARCH_RUN_WRITEBACK_ENABLED\s+value: "false"',
        manifest,
    )
    assert re.search(
        r'- key: RESEARCH_RUN_ALLOW_EPHEMERAL_LEDGER\s+value: "false"',
        manifest,
    )
