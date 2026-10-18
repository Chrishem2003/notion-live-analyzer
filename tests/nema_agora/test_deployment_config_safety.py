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
def test_unknown_or_malformed_explicit_mode_is_invalid_not_demo(value):
    assert mode_from_secrets({"nema_agora": {"mode": value}}) == "invalid"


def test_missing_mode_defaults_to_safe_demo_but_valid_modes_are_explicit():
    assert mode_from_secrets({}) == "demo"
    assert mode_from_secrets({"nema_agora": {}}) == "demo"
    assert mode_from_secrets({"nema_agora": {"mode": " PERSISTENT "}}) == "persistent"
    assert mode_from_secrets({"nema_agora": {"mode": "demo"}}) == "demo"


def test_missing_or_malformed_database_path_is_not_inferred():
    for value in (
        {},
        {"nema_agora": {}},
        {"nema_agora": {"database_path": ""}},
        {"nema_agora": {"database_path": None}},
        {"nema_agora": "not-a-section"},
    ):
        assert database_path_from_secrets(value) is None


def test_database_path_is_explicit_and_expands_home_marker():
    path = database_path_from_secrets({"nema_agora": {"database_path": "~/nema/pilot.sqlite3"}})
    assert path == Path("~/nema/pilot.sqlite3").expanduser()


@pytest.mark.parametrize("value", [0, -1, 3651, "not-a-number", True, None, 1.5, 1.0, [], {}])
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


def test_persistent_runtime_initializes_database_under_explicit_path(tmp_path):
    from nema_agora.runtime import initialize_persistent_service

    database_path = tmp_path / "nested" / "pilot.sqlite3"
    service = initialize_persistent_service(database_path)

    assert database_path.is_file()
    assert Path(service.repository.database_path) == database_path


def test_persistent_runtime_surfaces_unavailable_storage_instead_of_falling_back(tmp_path):
    from nema_agora.runtime import initialize_persistent_service

    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("block directory creation", encoding="utf-8")
    database_path = blocked_parent / "pilot.sqlite3"

    with pytest.raises(OSError):
        initialize_persistent_service(database_path)

    assert not database_path.exists()
