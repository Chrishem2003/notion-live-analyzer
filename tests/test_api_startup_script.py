"""Regression tests for the API startup script's optional preflight behavior."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
STARTUP_SCRIPT = REPO_ROOT / "scripts" / "start_research_run_api.sh"


def _make_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


@pytest.mark.parametrize(
    ("preflight_exit", "warning_expected"),
    [(0, False), (23, True)],
)
def test_api_startup_runs_uvicorn_even_when_optional_preflight_fails(
    tmp_path: Path, preflight_exit: int, warning_expected: bool
) -> None:
    """A failed Notion preflight warns, but does not stop unrelated API routes."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    args_file = tmp_path / "uvicorn-args.txt"

    # Simulate the preflight command without accessing real credentials or Notion.
    _make_executable(
        bin_dir / "python",
        f"#!/bin/sh\nexit {preflight_exit}\n",
    )
    _make_executable(
        bin_dir / "uvicorn",
        '#!/bin/sh\nprintf "%s\\n" "$@" > "$UVICORN_ARGS_FILE"\nexit 0\n',
    )

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["UVICORN_ARGS_FILE"] = str(args_file)
    env["PORT"] = "9123"

    completed = subprocess.run(
        ["sh", str(STARTUP_SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr
    assert args_file.exists(), "Uvicorn must be invoked even when preflight fails"
    assert args_file.read_text(encoding="utf-8").splitlines() == [
        "api_server:app",
        "--host",
        "0.0.0.0",
        "--port",
        "9123",
    ]
    assert ("WARNING: research-run integration is not ready" in completed.stderr) is warning_expected
    assert ("Research-run preflight passed." in completed.stdout) is (not warning_expected)
