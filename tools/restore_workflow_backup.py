"""Restore a workflow SQLite backup to a new, isolated file without overwriting.

The command verifies the source and the restored copy, uses SQLite's online
backup API (including WAL state), and publishes only through a no-overwrite
same-directory hard link. It does not decrypt payloads or change the source.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

from tools.verify_workflow_backup import BackupVerificationError, verify_workflow_backup


class WorkflowBackupRestoreError(RuntimeError):
    """Raised when a backup cannot be restored safely to a new destination."""


def _report_signature(report: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(report["workflow_runs"]),
        int(report["workflow_events"]),
        tuple(sorted(report["result_integrity_counts"].items())),
        tuple(sorted(report["encrypted_payload_field_counts"].items())),
    )


def _sqlite_file_signature(path: Path) -> tuple[Any, ...]:
    """Capture main/WAL/SHM identity and reject unsafe SQLite sidecar aliases."""
    signature: list[Any] = []
    candidates = (path, Path(f"{path}-wal"), Path(f"{path}-shm"))
    for index, candidate in enumerate(candidates):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            signature.append(None)
            continue
        if not stat.S_ISREG(info.st_mode):
            kind = "database" if index == 0 else "sidecar"
            raise WorkflowBackupRestoreError(
                f"SQLite source {kind} must be a regular file, not a symbolic link or special file"
            )
        if index > 0 and info.st_nlink != 1:
            raise WorkflowBackupRestoreError(
                "SQLite source sidecar must not be hard-linked to another path"
            )
        signature.append((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns))
    return tuple(signature)


def _is_owned_regular_file(path: Path, identity: tuple[int, int] | None) -> bool:
    """Check that a path still names the regular-file inode created by this invocation."""
    if identity is None:
        return False
    try:
        current = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISREG(current.st_mode) and (current.st_dev, current.st_ino) == identity


def _unlink_if_owned(path: Path, identity: tuple[int, int] | None) -> None:
    """Remove only a regular file whose inode was created by this invocation."""
    if _is_owned_regular_file(path, identity):
        path.unlink()


def restore_workflow_backup(
    source_path: str | Path,
    destination_path: str | Path,
) -> dict[str, Any]:
    """Create a verified restore copy at a new path; never overwrite an existing path.

    The destination directory must already exist. A temporary database is built
    in that directory, verified, then published with os.link so a concurrently
    created destination cannot be overwritten. Hosts without same-directory
    hard-link support fail closed rather than falling back to an overwrite.
    """
    try:
        source_candidate = Path(source_path).expanduser()
        source_lstat = source_candidate.lstat()
        if stat.S_ISLNK(source_lstat.st_mode):
            raise WorkflowBackupRestoreError("source backup must not be a symbolic link")
        source = source_candidate.resolve(strict=True)
        source_info = source.stat()
        if not stat.S_ISREG(source_info.st_mode):
            raise WorkflowBackupRestoreError("source backup must be an existing regular file")

        destination_candidate = Path(destination_path).expanduser()
        if destination_candidate.name in {"", ".", ".."}:
            raise WorkflowBackupRestoreError("destination must name a new file")
        destination_parent = destination_candidate.parent.resolve(strict=True)
        if not destination_parent.is_dir():
            raise WorkflowBackupRestoreError("destination directory must already exist")
        destination = destination_parent / destination_candidate.name
        if source == destination:
            raise WorkflowBackupRestoreError("source and destination must be different files")
        if os.path.lexists(destination):
            raise WorkflowBackupRestoreError(
                "destination already exists; existing files and symbolic links are never overwritten"
            )
    except WorkflowBackupRestoreError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError, UnicodeError) as exc:
        raise WorkflowBackupRestoreError("source or destination path could not be resolved safely") from exc

    # Inspect SQLite sidecars before opening the source through SQLite so a
    # symlinked or hard-linked WAL/SHM file is rejected before it is followed.
    try:
        _sqlite_file_signature(source)
    except WorkflowBackupRestoreError:
        raise
    except OSError as exc:
        raise WorkflowBackupRestoreError(
            "SQLite source files could not be inspected safely"
        ) from exc

    try:
        source_report = verify_workflow_backup(source)
    except BackupVerificationError as exc:
        raise WorkflowBackupRestoreError(
            "source backup failed read-only integrity verification"
        ) from exc

    source_signature = _report_signature(source_report)
    try:
        source_files_before = _sqlite_file_signature(source)
    except WorkflowBackupRestoreError:
        raise
    except OSError as exc:
        raise WorkflowBackupRestoreError(
            "SQLite source files could not be inspected safely"
        ) from exc
    source_identity_before = (source_info.st_dev, source_info.st_ino)

    temporary_path: Path | None = None
    temporary_identity: tuple[int, int] | None = None
    destination_published = False
    temporary_fd: int | None = None
    source_connection: sqlite3.Connection | None = None
    destination_connection: sqlite3.Connection | None = None
    completed = False

    try:
        temporary_fd, temporary_name = tempfile.mkstemp(
            prefix=".workflow-restore-",
            suffix=".sqlite3.tmp",
            dir=str(destination_parent),
        )
        temporary_path = Path(temporary_name)
        temporary_stat = os.fstat(temporary_fd)
        temporary_identity = (temporary_stat.st_dev, temporary_stat.st_ino)
        os.close(temporary_fd)
        temporary_fd = None

        # Read-only source connection sees committed WAL state. The operator must
        # stop submissions/workers so the pre/post source signatures remain stable.
        source_connection = sqlite3.connect(
            source.as_uri() + "?mode=ro",
            uri=True,
            timeout=10,
        )
        source_connection.execute("PRAGMA query_only = ON")
        destination_connection = sqlite3.connect(str(temporary_path), timeout=10)
        source_connection.backup(destination_connection)
        destination_connection.commit()
        destination_connection.close()
        destination_connection = None
        source_connection.close()
        source_connection = None

        if os.name == "posix":
            os.chmod(temporary_path, 0o600)
        sync_fd = os.open(str(temporary_path), os.O_RDONLY)
        try:
            os.fsync(sync_fd)
        finally:
            os.close(sync_fd)

        restored_report = verify_workflow_backup(temporary_path)
        if _report_signature(restored_report) != source_signature:
            raise WorkflowBackupRestoreError(
                "restored copy does not match the verified source snapshot"
            )

        source_after_report = verify_workflow_backup(source)
        source_info_after = source.stat()
        source_identity_after = (source_info_after.st_dev, source_info_after.st_ino)
        if (
            _report_signature(source_after_report) != source_signature
            or _sqlite_file_signature(source) != source_files_before
            or source_identity_after != source_identity_before
        ):
            raise WorkflowBackupRestoreError(
                "source changed during restore; stop writers and retry with a stable snapshot"
            )

        # link() is atomic and fails if destination appeared after the earlier check.
        # It never replaces an existing file or follows a destination symlink.
        os.link(str(temporary_path), str(destination))
        destination_published = True
        destination_info = destination.lstat()
        if (
            not stat.S_ISREG(destination_info.st_mode)
            or (destination_info.st_dev, destination_info.st_ino) != temporary_identity
        ):
            raise WorkflowBackupRestoreError(
                "published destination identity could not be verified"
            )

        destination_report = verify_workflow_backup(destination)
        if _report_signature(destination_report) != source_signature:
            raise WorkflowBackupRestoreError(
                "published destination failed post-publication verification"
            )

        # Verification opens the destination by path. Recheck both links after
        # that read so a concurrent path replacement cannot be accepted as the
        # published copy or removed as though it were our temporary file.
        if not _is_owned_regular_file(destination, temporary_identity):
            raise WorkflowBackupRestoreError(
                "published destination changed during post-publication verification"
            )
        if not _is_owned_regular_file(temporary_path, temporary_identity):
            raise WorkflowBackupRestoreError(
                "temporary restore file changed during post-publication verification"
            )
        _unlink_if_owned(temporary_path, temporary_identity)
        if os.path.lexists(temporary_path):
            raise WorkflowBackupRestoreError(
                "temporary restore link could not be removed safely"
            )
        temporary_path = None
        completed = True
        return {
            "restored": True,
            "source_verified": True,
            "destination_verified": True,
            "workflow_runs": int(destination_report["workflow_runs"]),
            "workflow_events": int(destination_report["workflow_events"]),
            "result_integrity_counts": destination_report["result_integrity_counts"],
            "encrypted_payload_field_counts": destination_report["encrypted_payload_field_counts"],
            "publication": "no-overwrite same-directory hard link",
            "payload_decryption": "not performed; verify with the approved key in isolated staging",
        }
    except WorkflowBackupRestoreError:
        raise
    except (BackupVerificationError, OSError, sqlite3.Error, RuntimeError, TypeError, ValueError, UnicodeError) as exc:
        raise WorkflowBackupRestoreError(
            "backup restore failed safely; source was not modified"
        ) from exc
    finally:
        if source_connection is not None:
            try:
                source_connection.close()
            except sqlite3.Error:
                pass
        if destination_connection is not None:
            try:
                destination_connection.close()
            except sqlite3.Error:
                pass
        if temporary_fd is not None:
            try:
                os.close(temporary_fd)
            except OSError:
                pass
        if not completed:
            try:
                if destination_published:
                    _unlink_if_owned(destination, temporary_identity)
            except OSError:
                pass
            try:
                if temporary_path is not None:
                    _unlink_if_owned(temporary_path, temporary_identity)
            except OSError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore a verified workflow SQLite backup to a new, non-existing file."
    )
    parser.add_argument("backup", help="Existing workflow SQLite backup")
    parser.add_argument("destination", help="New destination file in an existing directory")
    args = parser.parse_args()
    try:
        result = restore_workflow_backup(args.backup, args.destination)
    except WorkflowBackupRestoreError as exc:
        print(json.dumps({"restored": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
