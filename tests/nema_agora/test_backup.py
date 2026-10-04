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
