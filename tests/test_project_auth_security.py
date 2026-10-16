"""Regression tests for project-collaboration signing-key resolution and JWT validation."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "modules" / "project_collaboration" / "project_auth.py"
SPEC = importlib.util.spec_from_file_location("project_auth_security_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
project_auth = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(project_auth)


def test_configured_signing_key_is_used(monkeypatch):
    monkeypatch.setenv("PROJECT_COLLAB_SIGNING_KEY", "test-secret-from-environment")
    assert project_auth.resolve_signing_key() == "test-secret-from-environment"


def test_missing_signing_key_uses_unpredictable_ephemeral_values(monkeypatch):
    monkeypatch.delenv("PROJECT_COLLAB_SIGNING_KEY", raising=False)

    first = project_auth.resolve_signing_key()
    second = project_auth.resolve_signing_key()

    assert len(first) >= 64
    assert len(second) >= 64
    assert first != second
    assert first != "chrishem-collab-signing-key-v1-secure"


def test_token_created_and_verified_by_same_manager_round_trips():
    manager = project_auth.ProjectAuthManager(signing_key="unit-test-signing-key")
    token, original = manager.create_access_token(
        user_id="researcher-1",
        project_id="project-42",
        role=project_auth.ProjectRole.RESEARCHER,
        display_name="Test Researcher",
    )

    valid, decoded, message = manager.validate_token(token)

    assert valid, message
    assert decoded is not None
    assert decoded.sub == original.sub
    assert decoded.project_id == original.project_id
    assert decoded.role == project_auth.ProjectRole.RESEARCHER
    assert decoded.permissions["edit_canvas"] is True


def test_tampered_token_is_rejected():
    manager = project_auth.ProjectAuthManager(signing_key="unit-test-signing-key")
    token, _ = manager.create_access_token(
        user_id="researcher-1",
        project_id="project-42",
        role=project_auth.ProjectRole.RESEARCHER,
    )
    parts = token.split(".")
    assert len(parts) == 3
    parts[1] = parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")

    valid, decoded, _ = manager.validate_token(".".join(parts))

    assert not valid
    assert decoded is None
