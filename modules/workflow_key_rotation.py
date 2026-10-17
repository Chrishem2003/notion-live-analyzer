"""Transactional rotation of the workflow payload encryption key."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from modules.workflow_storage import (
    WorkflowStorageConfigurationError,
    decrypt_storage_text,
    encrypt_storage_text,
    validate_storage_key,
)


class WorkflowKeyRotationError(RuntimeError):
    """Raised when a workflow encryption-key rotation cannot complete safely."""


def rotate_workflow_encryption_key(
    database_path: str | Path,
    backup_path: str | Path,
    old_key: str | bytes,
    new_key: str | bytes,
) -> dict[str, Any]:
    """Back up the SQLite database, then atomically re-encrypt stored payload fields.

    The SQLite online backup API is used so WAL state is included. The backup path
    must not already exist. If any encrypted field cannot be read with the old key,
    the database transaction rolls back and the backup is retained for investigation.
    """
    database = Path(database_path).expanduser().resolve()
    # Normalize the path without following the final symlink: resolve() would turn a dangling
    # backup symlink into its missing target and bypass the lexists overwrite guard below.
    backup = Path(os.path.abspath(os.fspath(Path(backup_path).expanduser())))
    if database == backup:
        raise WorkflowKeyRotationError("backup path must be different from the source database")
    if not database.is_file():
        raise WorkflowKeyRotationError("workflow database does not exist")
    # lexists also catches dangling symlinks. Never follow or overwrite a caller-provided
    # destination, and reserve a new backup atomically with restrictive permissions.
    if os.path.lexists(backup):
        raise WorkflowKeyRotationError("backup path already exists; refusing to overwrite a backup")
    try:
        old = validate_storage_key(old_key)
        new = validate_storage_key(new_key)
    except WorkflowStorageConfigurationError as exc:
        raise WorkflowKeyRotationError(
            "old/new workflow encryption key is invalid; no rotation was attempted"
        ) from exc
    if old == new:
        raise WorkflowKeyRotationError("old and new workflow encryption keys must be different")

    backup.parent.mkdir(parents=True, exist_ok=True)
    # O_EXCL prevents a time-of-check/time-of-use race from overwriting a file or
    # following a symlink created after the initial check. Mode 0600 restricts the
    # backup to the current user on POSIX systems; Windows ACLs still need review.
    try:
        fd = os.open(str(backup), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise WorkflowKeyRotationError(
            "backup path already exists; refusing to overwrite a backup"
        ) from exc
    else:
        os.close(fd)
    reserved_stat = backup.stat()
    source = None
    destination = None
    try:
        source = sqlite3.connect(str(database), timeout=30)
        destination = sqlite3.connect(str(backup), timeout=30)
        source.backup(destination)
        destination.close()
        destination = None
        # Re-assert restrictive mode after SQLite writes; do not change the source DB.
        if os.name == "posix":
            os.chmod(backup, 0o600)
    except Exception as exc:
        # Close handles before cleanup (required on Windows), then remove only the
        # reservation created by this call; never unlink a replacement.
        if destination is not None:
            destination.close()
        if source is not None:
            source.close()
        try:
            current_stat = backup.stat()
            if (current_stat.st_dev, current_stat.st_ino) == (
                reserved_stat.st_dev, reserved_stat.st_ino
            ):
                backup.unlink()
        except OSError:
            pass
        raise WorkflowKeyRotationError("SQLite-aware backup failed; no key rotation was attempted") from exc
    finally:
        if destination is not None:
            destination.close()
        if source is not None:
            source.close()

    fields_updated = 0
    rows_updated = 0
    connection = sqlite3.connect(str(database), timeout=30, isolation_level=None)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("BEGIN IMMEDIATE")
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(workflow_runs)").fetchall()
        }
        required = {"run_id", "input_json", "result_json", "error_message"}
        if not required.issubset(columns):
            raise WorkflowKeyRotationError(
                "workflow_runs schema is incomplete; expected input/result/error payload columns"
            )
        rows = connection.execute(
            "SELECT run_id, input_json, result_json, error_message FROM workflow_runs"
        ).fetchall()
        for row in rows:
            updates: dict[str, str] = {}
            for column in ("input_json", "result_json", "error_message"):
                value = row[column]
                if value is None:
                    continue
                plaintext = decrypt_storage_text(value, old)
                updates[column] = encrypt_storage_text(plaintext, new)
            if updates:
                assignments = ", ".join(f"{column} = ?" for column in updates)
                connection.execute(
                    f"UPDATE workflow_runs SET {assignments} WHERE run_id = ?",
                    (*updates.values(), row["run_id"]),
                )
                rows_updated += 1
                fields_updated += len(updates)
        connection.execute("COMMIT")
    except Exception as exc:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        if isinstance(exc, (WorkflowKeyRotationError, WorkflowStorageConfigurationError)):
            raise
        raise WorkflowKeyRotationError(
            "key rotation failed; the database transaction was rolled back and the backup was retained"
        ) from exc
    finally:
        connection.close()

    return {
        "rows_updated": rows_updated,
        "fields_updated": fields_updated,
        "backup_path": str(backup),
    }
