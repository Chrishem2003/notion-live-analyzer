"""Deployment configuration must fail closed on invalid persistence settings."""
from pathlib import Path

import pytest

from nema_agora.config import (
    backup_dir_from_secrets,
    backup_retention_from_secrets,
    database_path_from_secrets,
    mode_from_secrets,
)


@pytest.mark.parametrize("value", ["", "production", "persistent-ish", None, 7, True])
def test_unknown_or_malformed_mode_defaults_to_demo(value):
    assert mode_from_secrets({"nema_agora": {"mode": value}}) == "demo"


def test_only_explicit_persistent_mode_enables_persistent_configuration():
    assert mode_from_secrets({"nema_agora": {"mode": " PERSISTENT "}}) == "persistent"
    assert mode_from_secrets({"nema_agora": {"mode": "demo"}}) == "demo"


@pytest.mark.parametrize("secrets", [{}, {"nema_agora": {}}, {"nema_agora": {"database_path": ""}}, {"nema_agora": {"database_path": None}}, {"nema_agora": "not-a-section"}])
def test_missing_or_malformed_database_path_is_not_inferred(secrets):
    assert database_path_from_secrets(secrets) is None


def test_database_path_is_explicit_and_expands_home_marker():
    path = database_path_from_secrets({"nema_agora": {"database_path": "~/nema/pilot.sqlite3"}})
    assert path == Path("~/nema/pilot.sqlite3").expanduser()


@pytest.mark.parametrize("value", [0, -1, 3651, "not-a-number", True, None])
def test_invalid_backup_retention_fails_closed(value):
    assert backup_retention_from_secrets({"nema_agora": {"backup_retention": value}}) is None


def test_backup_retention_accepts_only_bounded_integer_values():
    assert backup_retention_from_secrets({"nema_agora": {"backup_retention": 1}}) == 1
    assert backup_retention_from_secrets({"nema_agora": {"backup_retention": "30"}}) == 30
    assert backup_retention_from_secrets({"nema_agora": {"backup_retention": 3650}}) == 3650


def test_missing_or_malformed_backup_directory_is_not_guessed():
    assert backup_dir_from_secrets({}) is None
    assert backup_dir_from_secrets({"nema_agora": {"backup_dir": []}}) is None
    assert backup_dir_from_secrets({"nema_agora": {"backup_dir": "  "}}) is None
