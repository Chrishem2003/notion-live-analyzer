from datetime import datetime, timezone
import sqlite3

import pytest

from nema_agora.backup import backup_database, integrity_check, list_backups, prune_backups, restore_database
from nema_agora.core import CATEGORIES, make_observation
from nema_agora.storage import NemaAgoraRepository


def record():
    from datetime import date
    return make_observation(
        observation_date=date(2026, 10, 4), category=CATEGORIES[0], severity="Moderate",
        site="Pilot A", description="Synthetic test observation", latitude=2.5, longitude=32.1,
        consent_confirmed=True, created_at="2026-10-04T12:00:00+03:00",
    )


def test_backup_is_consistent_and_listed(tmp_path):
    db = tmp_path / "nema.sqlite3"
    NemaAgoraRepository(db).create_observation(record(), actor_id="submitter-1", role="submitter")
    backup = backup_database(db, tmp_path / "backups", now=datetime(2026, 10, 4, 9, tzinfo=timezone.utc))
    assert backup.name == "nema_agora_20261004T090000Z.sqlite3"
    assert integrity_check(backup)
    assert list_backups(tmp_path / "backups") == [backup]


def test_prune_keeps_newest_requested_count(tmp_path):
    directory = tmp_path / "backups"
    directory.mkdir()
    for stamp in ("20261001T090000Z", "20261002T090000Z", "20261003T090000Z"):
        sqlite3.connect(directory / f"nema_agora_{stamp}.sqlite3").close()
    removed = prune_backups(directory, keep=2)
    assert [p.name for p in removed] == ["nema_agora_20261001T090000Z.sqlite3"]
    assert len(list_backups(directory)) == 2


def test_restore_requires_explicit_confirmation_and_recovers_database(tmp_path):
    source_db = tmp_path / "source.sqlite3"
    target_db = tmp_path / "target.sqlite3"
    NemaAgoraRepository(source_db).create_observation(record(), actor_id="submitter-1", role="submitter")
    backup = backup_database(source_db, tmp_path / "backups", now=datetime(2026, 10, 4, 9, tzinfo=timezone.utc))
    with pytest.raises(PermissionError):
        restore_database(backup, target_db)
    restore_database(backup, target_db, confirm_destructive=True)
    assert integrity_check(target_db)
    assert len(NemaAgoraRepository(target_db).list_observations(actor_id="submitter-1", role="submitter")) == 1


def test_corrupt_backup_is_rejected(tmp_path):
    bad = tmp_path / "bad.sqlite3"
    bad.write_text("not sqlite")
    with pytest.raises(ValueError, match="integrity_check"):
        restore_database(bad, tmp_path / "target.sqlite3", confirm_destructive=True)

def test_backup_collision_does_not_overwrite_existing_backup(tmp_path):
    db = tmp_path / "nema.sqlite3"
    NemaAgoraRepository(db).create_observation(record(), actor_id="submitter-1", role="submitter")
    backup_dir = tmp_path / "backups"
    stamp = datetime(2026, 10, 4, 9, tzinfo=timezone.utc)
    first = backup_database(db, backup_dir, now=stamp)

    with pytest.raises(FileExistsError):
        backup_database(db, backup_dir, now=stamp)

    assert integrity_check(first)
    assert list_backups(backup_dir) == [first]


def test_restore_replaces_existing_database_after_validation(tmp_path):
    source_db = tmp_path / "source.sqlite3"
    target_db = tmp_path / "target.sqlite3"
    NemaAgoraRepository(source_db).create_observation(record(), actor_id="submitter-1", role="submitter")
    NemaAgoraRepository(target_db).create_observation(record(), actor_id="submitter-2", role="submitter")
    backup = backup_database(
        source_db,
        tmp_path / "backups",
        now=datetime(2026, 10, 4, 9, tzinfo=timezone.utc),
    )

    restore_database(backup, target_db, confirm_destructive=True)

    assert integrity_check(target_db)
    restored = NemaAgoraRepository(target_db)
    assert len(restored.list_observations(actor_id="submitter-1", role="submitter")) == 1
    assert restored.list_observations(actor_id="submitter-2", role="submitter") == []


def test_invalid_backup_does_not_modify_existing_target(tmp_path):
    target_db = tmp_path / "target.sqlite3"
    NemaAgoraRepository(target_db).create_observation(record(), actor_id="submitter-2", role="submitter")
    bad_backup = tmp_path / "bad.sqlite3"
    bad_backup.write_text("not sqlite")

    with pytest.raises(ValueError, match="integrity_check"):
        restore_database(bad_backup, target_db, confirm_destructive=True)

    assert integrity_check(target_db)
    assert len(NemaAgoraRepository(target_db).list_observations(actor_id="submitter-2", role="submitter")) == 1

def test_restore_post_replace_integrity_failure_rolls_back_existing_target(tmp_path, monkeypatch):
    import nema_agora.backup as backup_module

    source_db = tmp_path / "source.sqlite3"
    target_db = tmp_path / "target.sqlite3"
    NemaAgoraRepository(source_db).create_observation(
        record(), actor_id="source-user", role="submitter"
    )
    NemaAgoraRepository(target_db).create_observation(
        record(), actor_id="target-user", role="submitter"
    )
    backup = backup_database(
        source_db,
        tmp_path / "backups",
        now=datetime(2026, 10, 4, 9, tzinfo=timezone.utc),
    )

    original_integrity_check = backup_module.integrity_check
    calls = {"count": 0}

    def fail_once_after_replacement(path):
        calls["count"] += 1
        # source backup, temporary restore, and existing target all pass;
        # fail the post-replacement check to exercise rollback.
        if calls["count"] == 4:
            return False
        return original_integrity_check(path)

    monkeypatch.setattr(backup_module, "integrity_check", fail_once_after_replacement)
    with pytest.raises(ValueError, match="post-restore integrity_check"):
        restore_database(backup, target_db, confirm_destructive=True)

    monkeypatch.setattr(backup_module, "integrity_check", original_integrity_check)
    assert integrity_check(target_db)
    reopened = NemaAgoraRepository(target_db)
    assert len(reopened.list_observations(actor_id="target-user", role="submitter")) == 1
    assert reopened.list_observations(actor_id="source-user", role="submitter") == []



@pytest.mark.parametrize("empty_path", ["", "   "])
def test_backup_helpers_reject_empty_path_instead_of_using_current_directory(tmp_path, empty_path):
    from nema_agora.backup import _path

    with pytest.raises(ValueError, match="filesystem path is required"):
        _path(empty_path)


@pytest.mark.parametrize("keep", [0, -1, 3651, True, False, 1.5, "2", None])
def test_prune_rejects_invalid_retention_values(tmp_path, keep):
    with pytest.raises(ValueError, match="retention must be between 1 and 3650"):
        prune_backups(tmp_path / "backups", keep=keep)


def test_backup_rejects_missing_source_without_creating_backup_directory(tmp_path):
    backup_dir = tmp_path / "backups"
    with pytest.raises(FileNotFoundError, match="Database not found"):
        backup_database(tmp_path / "missing.sqlite3", backup_dir)
    assert not backup_dir.exists()


def test_backup_rejects_corrupt_source(tmp_path):
    corrupt = tmp_path / "corrupt.sqlite3"
    corrupt.write_text("not a SQLite database", encoding="utf-8")
    with pytest.raises(ValueError, match="Source database failed"):
        backup_database(corrupt, tmp_path / "backups")
    assert not (tmp_path / "backups").exists()


def test_restore_preserves_rollback_snapshot_when_automatic_rollback_fails(tmp_path, monkeypatch):
    import shutil
    import nema_agora.backup as backup_module

    source_db = tmp_path / "source.sqlite3"
    target_db = tmp_path / "target.sqlite3"
    NemaAgoraRepository(source_db).create_observation(
        record(), actor_id="source-user", role="submitter"
    )
    NemaAgoraRepository(target_db).create_observation(
        record(), actor_id="target-user", role="submitter"
    )
    backup = backup_database(
        source_db,
        tmp_path / "backups",
        now=datetime(2026, 10, 4, 9, tzinfo=timezone.utc),
    )

    original_integrity_check = backup_module.integrity_check
    original_replace = backup_module.os.replace
    calls = {"integrity": 0}

    def fail_post_restore_check(path):
        calls["integrity"] += 1
        if calls["integrity"] == 4:
            return False
        return original_integrity_check(path)

    def fail_only_rollback_replace(src, dst):
        if str(src).endswith(".rollback") and str(dst) == str(target_db):
            raise OSError("simulated rollback filesystem failure")
        return original_replace(src, dst)

    monkeypatch.setattr(backup_module, "integrity_check", fail_post_restore_check)
    monkeypatch.setattr(backup_module.os, "replace", fail_only_rollback_replace)
    with pytest.raises(RuntimeError, match="recovery snapshot preserved"):
        restore_database(backup, target_db, confirm_destructive=True)

    snapshots = list(tmp_path.glob(".target.sqlite3.*.rollback"))
    assert len(snapshots) == 1
    # The retained snapshot is recoverable even though automatic replacement failed.
    shutil.copy2(snapshots[0], target_db)
    monkeypatch.setattr(backup_module, "integrity_check", original_integrity_check)
    assert integrity_check(target_db)
    restored = NemaAgoraRepository(target_db)
    assert len(restored.list_observations(actor_id="target-user", role="submitter")) == 1
    assert restored.list_observations(actor_id="source-user", role="submitter") == []


def test_backup_and_restored_database_permissions_are_restricted_on_posix(tmp_path):
    import os
    import stat

    if os.name == "nt":
        pytest.skip("POSIX file permission bits are not portable to Windows")

    source_db = tmp_path / "source.sqlite3"
    target_db = tmp_path / "restored.sqlite3"
    NemaAgoraRepository(source_db).create_observation(
        record(), actor_id="submitter-1", role="submitter"
    )
    backup = backup_database(
        source_db,
        tmp_path / "backups",
        now=datetime(2026, 10, 4, 9, tzinfo=timezone.utc),
    )
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600

    restore_database(backup, target_db, confirm_destructive=True)
    assert stat.S_IMODE(target_db.stat().st_mode) == 0o600
