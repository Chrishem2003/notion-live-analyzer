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
        if index == 2:
            # SQLite may legitimately update the WAL-index shared-memory contents
            # while readers coordinate; track its identity, not mutable metadata.
            signature.append((info.st_dev, info.st_ino))
        else:
            signature.append((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns))
    return tuple(signature)


def _directory_identity(path: Path, label: str) -> tuple[int, int]:
    """Return the identity of a real directory, rejecting a symlink at this path."""
    try:
        info = path.lstat()
    except OSError as exc:
        raise WorkflowBackupRestoreError(
            f"{label} parent directory could not be inspected safely"
        ) from exc
    if not stat.S_ISDIR(info.st_mode):
        raise WorkflowBackupRestoreError(
            f"{label} parent must be a real directory, not a symbolic link or special path"
        )
    return (info.st_dev, info.st_ino)


def _assert_directory_identity(
    path: Path,
    expected: tuple[int, int],
    label: str,
) -> None:
    """Fail closed if a source or destination parent was replaced during restore."""
    if _directory_identity(path, label) != expected:
        raise WorkflowBackupRestoreError(
            f"{label} parent directory changed during restore"
        )


def _is_owned_regular_file(path: Path, identity: tuple[int, int] | None) -> bool:
    """Check that a path still names the regular-file inode created by this invocation."""
    if identity is None:
        return False
    try:
        current = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISREG(current.st_mode) and (current.st_dev, current.st_ino) == identity


def _unlink_if_owned(
    path: Path,
    identity: tuple[int, int] | None,
    directory_fd: int | None = None,
) -> None:
    """Remove only this invocation's file, using the opened parent directory when possible."""
    if identity is None:
        return
    if directory_fd is not None and os.name == "posix":
        try:
            current = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
            if (
                stat.S_ISREG(current.st_mode)
                and (current.st_dev, current.st_ino) == identity
            ):
                os.unlink(path.name, dir_fd=directory_fd)
                return
        except FileNotFoundError:
            pass
        except (OSError, TypeError, NotImplementedError):
            pass
    if _is_owned_regular_file(path, identity):
        path.unlink()


def _sidecar_names(path: Path) -> tuple[str, str]:
    return (f"{path.name}-wal", f"{path.name}-shm")


def _sidecar_info(
    path: Path,
    name: str,
    directory_fd: int | None = None,
) -> os.stat_result | None:
    try:
        if directory_fd is not None and os.name == "posix":
            return os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        return (path.parent / name).lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise WorkflowBackupRestoreError(
            "SQLite restore sidecars could not be inspected safely"
        ) from exc


def _assert_sidecars_absent(
    path: Path,
    label: str,
    directory_fd: int | None = None,
) -> None:
    for name in _sidecar_names(path):
        if _sidecar_info(path, name, directory_fd) is not None:
            raise WorkflowBackupRestoreError(
                f"{label} SQLite sidecar path already exists or appeared unexpectedly"
            )


def _capture_owned_sidecars(
    path: Path,
    directory_fd: int | None = None,
) -> dict[str, tuple[int, int]]:
    """Capture only regular, single-link WAL/SHM inodes at an operation-owned path."""
    captured: dict[str, tuple[int, int]] = {}
    for name in _sidecar_names(path):
        info = _sidecar_info(path, name, directory_fd)
        if info is None:
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise WorkflowBackupRestoreError(
                "SQLite restore sidecar must be a single-link regular file"
            )
        captured[name] = (info.st_dev, info.st_ino)
    return captured


def _remove_owned_sidecars(
    path: Path,
    identities: dict[str, tuple[int, int]],
    directory_fd: int | None = None,
) -> None:
    for name, identity in identities.items():
        _unlink_if_owned(path.parent / name, identity, directory_fd)


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
        source_parent_candidate = source_candidate.parent
        source_parent_initial = _directory_identity(source_parent_candidate, "source")
        source_parent = source_parent_candidate.resolve(strict=True)
        source_parent_identity = _directory_identity(source_parent, "source")
        if source_parent_identity != source_parent_initial:
            raise WorkflowBackupRestoreError("source parent directory changed during path resolution")
        source = source_parent / source_candidate.name
        source_lstat = source.lstat()
        if stat.S_ISLNK(source_lstat.st_mode):
            raise WorkflowBackupRestoreError("source backup must not be a symbolic link")
        source = source.resolve(strict=True)
        source_info = source.stat()
        if not stat.S_ISREG(source_info.st_mode):
            raise WorkflowBackupRestoreError("source backup must be an existing regular file")

        destination_candidate = Path(destination_path).expanduser()
        if destination_candidate.name in {"", ".", ".."}:
            raise WorkflowBackupRestoreError("destination must name a new file")
        destination_parent_candidate = destination_candidate.parent
        destination_parent_initial = _directory_identity(
            destination_parent_candidate, "destination"
        )
        destination_parent = destination_parent_candidate.resolve(strict=True)
        destination_parent_identity = _directory_identity(
            destination_parent, "destination"
        )
        if destination_parent_identity != destination_parent_initial:
            raise WorkflowBackupRestoreError(
                "destination parent directory changed during path resolution"
            )
        destination = destination_parent / destination_candidate.name
        _assert_sidecars_absent(destination, "destination")
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
    _assert_directory_identity(source.parent, source_parent_identity, "source")
    _assert_directory_identity(destination_parent, destination_parent_identity, "destination")
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
    temporary_sidecars: dict[str, tuple[int, int]] = {}
    destination_sidecars: dict[str, tuple[int, int]] = {}
    source_connection: sqlite3.Connection | None = None
    destination_connection: sqlite3.Connection | None = None
    completed = False
    destination_directory_fd: int | None = None

    try:
        _assert_directory_identity(source.parent, source_parent_identity, "source")
        _assert_directory_identity(destination_parent, destination_parent_identity, "destination")
        if os.name == "posix" and hasattr(os, "O_DIRECTORY"):
            directory_flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
            destination_directory_fd = os.open(str(destination_parent), directory_flags)
            directory_info = os.fstat(destination_directory_fd)
            if (
                not stat.S_ISDIR(directory_info.st_mode)
                or (directory_info.st_dev, directory_info.st_ino) != destination_parent_identity
            ):
                raise WorkflowBackupRestoreError(
                    "destination parent directory changed while it was opened"
                )

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
        _assert_directory_identity(destination_parent, destination_parent_identity, "destination")
        _assert_directory_identity(source.parent, source_parent_identity, "source")
        _assert_sidecars_absent(temporary_path, "temporary restore", destination_directory_fd)

        # Read-only source connection sees committed WAL state. The operator must
        # stop submissions/workers so the pre/post source signatures remain stable.
        source_connection = sqlite3.connect(
            source.as_uri() + "?mode=ro",
            uri=True,
            timeout=10,
        )
        source_connection.execute("PRAGMA query_only = ON")
        _assert_directory_identity(source.parent, source_parent_identity, "source")
        _assert_directory_identity(destination_parent, destination_parent_identity, "destination")
        destination_connection = sqlite3.connect(str(temporary_path), timeout=10)
        source_connection.backup(destination_connection)
        destination_connection.commit()
        destination_connection.close()
        destination_connection = None
        source_connection.close()
        source_connection = None
        _assert_directory_identity(source.parent, source_parent_identity, "source")
        _assert_directory_identity(destination_parent, destination_parent_identity, "destination")

        if os.name == "posix":
            os.chmod(temporary_path, 0o600)
        sync_fd = os.open(str(temporary_path), os.O_RDONLY)
        try:
            os.fsync(sync_fd)
        finally:
            os.close(sync_fd)

        restored_report = verify_workflow_backup(temporary_path)
        temporary_sidecars.update(
            _capture_owned_sidecars(temporary_path, destination_directory_fd)
        )
        _assert_directory_identity(destination_parent, destination_parent_identity, "destination")
        _assert_directory_identity(source.parent, source_parent_identity, "source")
        if _report_signature(restored_report) != source_signature:
            raise WorkflowBackupRestoreError(
                "restored copy does not match the verified source snapshot"
            )

        source_after_report = verify_workflow_backup(source)
        _assert_directory_identity(source.parent, source_parent_identity, "source")
        _assert_directory_identity(destination_parent, destination_parent_identity, "destination")
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

        # Recheck immediately before publication. The opened directory descriptor
        # is retained for identity-safe cleanup if the pathname is replaced mid-run.
        _assert_directory_identity(destination_parent, destination_parent_identity, "destination")
        _assert_sidecars_absent(destination, "destination", destination_directory_fd)
        # link() is atomic and fails if destination appeared after the earlier check.
        # It never replaces an existing file or follows a destination symlink.
        os.link(str(temporary_path), str(destination))
        destination_published = True
        _assert_directory_identity(destination_parent, destination_parent_identity, "destination")
        destination_info = destination.lstat()
        if (
            not stat.S_ISREG(destination_info.st_mode)
            or (destination_info.st_dev, destination_info.st_ino) != temporary_identity
        ):
            raise WorkflowBackupRestoreError(
                "published destination identity could not be verified"
            )

        _assert_directory_identity(destination_parent, destination_parent_identity, "destination")
        destination_report = verify_workflow_backup(destination)
        destination_sidecars.update(
            _capture_owned_sidecars(destination, destination_directory_fd)
        )
        _assert_directory_identity(destination_parent, destination_parent_identity, "destination")
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
        _assert_directory_identity(destination_parent, destination_parent_identity, "destination")
        _remove_owned_sidecars(destination, destination_sidecars, destination_directory_fd)
        _remove_owned_sidecars(temporary_path, temporary_sidecars, destination_directory_fd)
        _assert_sidecars_absent(destination, "destination", destination_directory_fd)
        _assert_sidecars_absent(temporary_path, "temporary restore", destination_directory_fd)
        _unlink_if_owned(temporary_path, temporary_identity, destination_directory_fd)
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
                    destination_sidecars.update(
                        _capture_owned_sidecars(destination, destination_directory_fd)
                    )
                    _remove_owned_sidecars(destination, destination_sidecars, destination_directory_fd)
                    _unlink_if_owned(destination, temporary_identity, destination_directory_fd)
            except (OSError, WorkflowBackupRestoreError):
                pass
            try:
                if temporary_path is not None:
                    temporary_sidecars.update(
                        _capture_owned_sidecars(temporary_path, destination_directory_fd)
                    )
                    _remove_owned_sidecars(temporary_path, temporary_sidecars, destination_directory_fd)
                    _unlink_if_owned(temporary_path, temporary_identity, destination_directory_fd)
            except (OSError, WorkflowBackupRestoreError):
                pass
        if destination_directory_fd is not None:
            try:
                os.close(destination_directory_fd)
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
