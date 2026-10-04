"""SQLite backup, restore, integrity and bounded-retention helpers.

These operations are deployment controls, not a substitute for institutional
backup policy. Restore is deliberately opt-in and validates the source before
replacing the target database.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import sqlite3

_BACKUP_NAME = re.compile(r"^nema_agora_(\d{8}T\d{6}Z)\.sqlite3$")

def _path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not str(path).strip():
        raise ValueError("A filesystem path is required.")
    return path

def integrity_check(database_path: str | Path) -> bool:
    path = _path(database_path)
    if not path.is_file():
        return False
    connection = sqlite3.connect(path)
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()
        return bool(result and result[0] == "ok")
    finally:
        connection.close()

def backup_database(database_path: str | Path, backup_dir: str | Path, *, now: datetime | None = None) -> Path:
    source = _path(database_path)
    destination_dir = _path(backup_dir)
    if not source.is_file():
        raise FileNotFoundError(f"Database not found: {source}")
    if not integrity_check(source):
        raise ValueError("Source database failed SQLite integrity_check.")
    destination_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = destination_dir / f"nema_agora_{stamp}.sqlite3"
    if destination.exists():
        raise FileExistsError(f"Backup already exists: {destination}")
    source_connection = sqlite3.connect(source)
    target_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(target_connection)
        target_connection.commit()
    finally:
        target_connection.close()
        source_connection.close()
    if not integrity_check(destination):
        destination.unlink(missing_ok=True)
        raise ValueError("Created backup failed SQLite integrity_check.")
    return destination

def list_backups(backup_dir: str | Path) -> list[Path]:
    directory = _path(backup_dir)
    if not directory.is_dir():
        return []
    backups = [p for p in directory.iterdir() if p.is_file() and _BACKUP_NAME.match(p.name)]
    return sorted(backups, key=lambda p: p.name, reverse=True)

def prune_backups(backup_dir: str | Path, *, keep: int) -> list[Path]:
    if not isinstance(keep, int) or isinstance(keep, bool) or keep < 1 or keep > 3650:
        raise ValueError("Backup retention must be between 1 and 3650 files.")
    backups = list_backups(backup_dir)
    removed: list[Path] = []
    for path in backups[keep:]:
        path.unlink()
        removed.append(path)
    return removed

def restore_database(backup_path: str | Path, database_path: str | Path, *, confirm_destructive: bool = False) -> None:
    source = _path(backup_path)
    target = _path(database_path)
    if not confirm_destructive:
        raise PermissionError("Destructive restore requires explicit confirmation.")
    if not source.is_file():
        raise FileNotFoundError(f"Backup not found: {source}")
    if source.resolve() == target.resolve():
        raise ValueError("Backup and target database must be different files.")
    if not integrity_check(source):
        raise ValueError("Backup failed SQLite integrity_check.")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.restore-tmp")
    temporary.unlink(missing_ok=True)
    source_connection = sqlite3.connect(source)
    target_connection = sqlite3.connect(temporary)
    try:
        source_connection.backup(target_connection)
        target_connection.commit()
    finally:
        target_connection.close()
        source_connection.close()
    if not integrity_check(temporary):
        temporary.unlink(missing_ok=True)
        raise ValueError("Restored temporary database failed integrity_check.")
    shutil.move(str(temporary), str(target))
    if not integrity_check(target):
        raise ValueError("Restored database failed post-restore integrity_check.")
