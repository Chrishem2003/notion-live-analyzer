"""Functional tests for the non-overwriting workflow backup restore CLI."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import sqlite3
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet

from modules.workflow_runtime import WorkflowRuntime
from modules.workflow_store import list_run_events
from tools.restore_workflow_backup import (
    WorkflowBackupRestoreError,
    main as restore_main,
    restore_workflow_backup,
    _unlink_if_owned,
)
from tools.verify_workflow_backup import BackupVerificationError, verify_workflow_backup


@contextlib.contextmanager
def _closed_sqlite_connection(path):
    """Commit successful fixture work and always close the handle (including on Windows)."""
    connection = sqlite3.connect(path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


class WorkflowBackupRestoreCliTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.source = self.root / "source # café.sqlite3"
        self.destination = self.root / "restored # café.sqlite3"
        self.key = Fernet.generate_key()
        self.anchor = sqlite3.connect(self.source)
        self.anchor.execute("PRAGMA journal_mode=WAL")
        runtime = WorkflowRuntime(
            self.source,
            handlers={"echo": lambda payload: {"echo": payload["value"]}},
            encryption_key=self.key,
        )
        self.run_id = runtime.submit(
            workflow_id="synthetic-restore-cli",
            task_type="echo",
            payload={"value": "restore-cli-fixture-only"},
        )
        completed = runtime.execute_run(self.run_id)
        self.assertEqual(completed["status"], "succeeded")

    def tearDown(self):
        try:
            self.anchor.close()
        finally:
            self.tempdir.cleanup()

    def _source_digest(self):
        digest = hashlib.sha256()
        for path in (self.source, Path(f"{self.source}-wal")):
            if path.exists():
                digest.update(path.name.encode("utf-8"))
                digest.update(path.read_bytes())
        return digest.hexdigest()

    def test_restore_creates_verified_wal_aware_copy_and_runtime_readback(self):
        self.anchor.execute("PRAGMA journal_mode=WAL")
        self.anchor.execute("PRAGMA wal_autocheckpoint=0")
        self.anchor.execute("CREATE TABLE IF NOT EXISTS restore_wal_probe (value TEXT NOT NULL)")
        self.anchor.execute("INSERT INTO restore_wal_probe (value) VALUES ('wal-fixture-only')")
        self.anchor.commit()
        self.assertEqual(
            self.anchor.execute("PRAGMA journal_mode").fetchone()[0].lower(),
            "wal",
        )
        self.assertTrue(Path(f"{self.source}-wal").exists(), "fixture should retain committed WAL state")
        source_before = self._source_digest()
        report = restore_workflow_backup(self.source, self.destination)
        self.assertTrue(report["restored"])
        self.assertTrue(report["source_verified"])
        self.assertTrue(report["destination_verified"])
        self.assertFalse(Path(f"{self.destination}-wal").exists())
        self.assertFalse(Path(f"{self.destination}-shm").exists())
        self.assertEqual(list(self.root.glob(".workflow-restore-*.sqlite3.tmp-wal")), [])
        self.assertEqual(list(self.root.glob(".workflow-restore-*.sqlite3.tmp-shm")), [])
        self.assertEqual(report["workflow_runs"], 1)
        self.assertEqual(report["workflow_events"], 3)
        self.assertEqual(report["publication"], "no-overwrite same-directory hard link")
        self.assertEqual(self._source_digest(), source_before, "restore must not mutate the source")

        verified = verify_workflow_backup(self.destination)
        self.assertTrue(verified["verified"])
        restored_runtime = WorkflowRuntime(
            self.destination,
            handlers={"echo": lambda payload: {"echo": payload["value"]}},
            encryption_key=self.key,
        )
        restored_run = restored_runtime.get_run(self.run_id)
        self.assertEqual(restored_run["status"], "succeeded")
        self.assertEqual(restored_run["input"], {"value": "restore-cli-fixture-only"})
        self.assertEqual(restored_run["result"], {"echo": "restore-cli-fixture-only"})
        events = list_run_events(self.destination, "synthetic-restore-cli", self.run_id)
        self.assertEqual([event["status"] for event in events], ["queued", "running", "succeeded"])
        with _closed_sqlite_connection(self.destination) as connection:
            stored = connection.execute(
                "SELECT input_json FROM workflow_runs WHERE run_id = ?", (self.run_id,)
            ).fetchone()[0]
        self.assertTrue(stored.startswith("enc:v1:"))
        self.assertNotIn("restore-cli-fixture-only", stored)
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.destination.stat().st_mode), 0o600)

    def test_existing_destination_is_never_overwritten(self):
        self.destination.write_bytes(b"preserve-existing-destination")
        before_source = self._source_digest()
        with self.assertRaises(WorkflowBackupRestoreError):
            restore_workflow_backup(self.source, self.destination)
        self.assertEqual(self.destination.read_bytes(), b"preserve-existing-destination")
        self.assertEqual(self._source_digest(), before_source)

    def test_dangling_destination_symlink_is_rejected_without_target_creation(self):
        target = self.root / "not-created.sqlite3"
        try:
            self.destination.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {type(exc).__name__}")
        with self.assertRaises(WorkflowBackupRestoreError):
            restore_workflow_backup(self.source, self.destination)
        self.assertTrue(self.destination.is_symlink())
        self.assertFalse(target.exists())

    def test_source_symlink_is_rejected(self):
        source_link = self.root / "source-link.sqlite3"
        try:
            source_link.symlink_to(self.source)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {type(exc).__name__}")
        with self.assertRaises(WorkflowBackupRestoreError):
            restore_workflow_backup(source_link, self.destination)
        self.assertFalse(self.destination.exists())

    def test_source_wal_symlink_is_rejected_before_sqlite_verification(self):
        self.anchor.close()
        wal_path = Path(f"{self.source}-wal")
        if wal_path.exists() or wal_path.is_symlink():
            wal_path.unlink()
        target = self.root / "external-wal-target"
        target.write_bytes(b"synthetic-wal-target")
        try:
            wal_path.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {type(exc).__name__}")

        with patch("tools.restore_workflow_backup.verify_workflow_backup") as verifier:
            with self.assertRaisesRegex(WorkflowBackupRestoreError, "regular file"):
                restore_workflow_backup(self.source, self.destination)
            verifier.assert_not_called()
        self.assertEqual(target.read_bytes(), b"synthetic-wal-target")
        self.assertFalse(self.destination.exists())

    def test_source_shm_symlink_is_rejected_before_sqlite_verification(self):
        self.anchor.close()
        shm_path = Path(f"{self.source}-shm")
        if shm_path.exists() or shm_path.is_symlink():
            shm_path.unlink()
        target = self.root / "external-shm-target"
        target.write_bytes(b"synthetic-shm-target")
        try:
            shm_path.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {type(exc).__name__}")

        with patch("tools.restore_workflow_backup.verify_workflow_backup") as verifier:
            with self.assertRaisesRegex(WorkflowBackupRestoreError, "regular file"):
                restore_workflow_backup(self.source, self.destination)
            verifier.assert_not_called()
        self.assertEqual(target.read_bytes(), b"synthetic-shm-target")
        self.assertFalse(self.destination.exists())

    def test_source_wal_hardlink_is_rejected_before_sqlite_verification(self):
        self.anchor.close()
        wal_path = Path(f"{self.source}-wal")
        if wal_path.exists() or wal_path.is_symlink():
            wal_path.unlink()
        target = self.root / "external-wal-hardlink-target"
        target.write_bytes(b"synthetic-wal-hardlink-target")
        try:
            os.link(target, wal_path)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"hard-link creation unavailable: {type(exc).__name__}")

        self.assertEqual(target.stat().st_nlink, 2)
        with patch("tools.restore_workflow_backup.verify_workflow_backup") as verifier:
            with self.assertRaisesRegex(WorkflowBackupRestoreError, "must not be hard-linked"):
                restore_workflow_backup(self.source, self.destination)
            verifier.assert_not_called()
        self.assertEqual(target.read_bytes(), b"synthetic-wal-hardlink-target")
        self.assertFalse(self.destination.exists())

    def test_missing_destination_parent_is_not_created(self):
        parent = self.root / "missing-parent"
        destination = parent / "restore.sqlite3"
        with self.assertRaises(WorkflowBackupRestoreError):
            restore_workflow_backup(self.source, destination)
        self.assertFalse(parent.exists())

    def test_corrupt_source_is_not_modified_and_destination_is_not_created(self):
        corrupt = self.root / "corrupt.sqlite3"
        corrupt.write_bytes(b"not-a-sqlite-database")
        before = hashlib.sha256(corrupt.read_bytes()).hexdigest()
        destination = self.root / "corrupt-restore.sqlite3"
        with self.assertRaises(WorkflowBackupRestoreError):
            restore_workflow_backup(corrupt, destination)
        self.assertEqual(hashlib.sha256(corrupt.read_bytes()).hexdigest(), before)
        self.assertFalse(destination.exists())

    def test_failed_copy_verification_cleans_only_temporary_restore_file(self):
        real_verify = verify_workflow_backup
        calls = 0

        def fail_on_temporary(path):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise BackupVerificationError("synthetic verification failure")
            return real_verify(path)

        with patch("tools.restore_workflow_backup.verify_workflow_backup", side_effect=fail_on_temporary):
            with self.assertRaises(WorkflowBackupRestoreError):
                restore_workflow_backup(self.source, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.root.glob(".workflow-restore-*.sqlite3.tmp")), [])

    def test_destination_created_during_publish_is_not_overwritten(self):
        original_link = os.link
        concurrent_bytes = b"concurrent-destination"

        def create_destination_then_link(source, destination):
            Path(destination).write_bytes(concurrent_bytes)
            return original_link(source, destination)

        with patch("tools.restore_workflow_backup.os.link", side_effect=create_destination_then_link):
            with self.assertRaises(WorkflowBackupRestoreError):
                restore_workflow_backup(self.source, self.destination)
        self.assertEqual(self.destination.read_bytes(), concurrent_bytes)
        self.assertEqual(list(self.root.glob(".workflow-restore-*.sqlite3.tmp")), [])

    def test_destination_replaced_during_post_publish_verification_is_preserved(self):
        real_verify = verify_workflow_backup
        calls = 0
        replacement = b"unowned-destination-replacement"

        def replace_after_destination_verification(candidate):
            nonlocal calls
            calls += 1
            report = real_verify(candidate)
            if calls == 4:
                self.destination.unlink()
                self.destination.write_bytes(replacement)
            return report

        with patch(
            "tools.restore_workflow_backup.verify_workflow_backup",
            side_effect=replace_after_destination_verification,
        ):
            with self.assertRaisesRegex(
                WorkflowBackupRestoreError,
                "published destination changed during post-publication verification",
            ):
                restore_workflow_backup(self.source, self.destination)

        self.assertEqual(calls, 4)
        self.assertEqual(self.destination.read_bytes(), replacement)
        self.assertEqual(list(self.root.glob(".workflow-restore-*.sqlite3.tmp")), [])

    def test_temporary_restore_path_replacement_is_not_deleted_as_owned(self):
        real_verify = verify_workflow_backup
        original_link = os.link
        calls = 0
        captured = {}
        replacement = b"unowned-temporary-path-replacement"

        def capture_temporary_link(source, destination):
            captured["temporary_path"] = Path(source)
            return original_link(source, destination)

        def replace_temporary_after_destination_verification(candidate):
            nonlocal calls
            calls += 1
            report = real_verify(candidate)
            if calls == 4:
                temporary_path = captured["temporary_path"]
                temporary_path.unlink()
                temporary_path.write_bytes(replacement)
            return report

        with (
            patch("tools.restore_workflow_backup.os.link", side_effect=capture_temporary_link),
            patch(
                "tools.restore_workflow_backup.verify_workflow_backup",
                side_effect=replace_temporary_after_destination_verification,
            ),
        ):
            with self.assertRaisesRegex(
                WorkflowBackupRestoreError,
                "temporary restore file changed during post-publication verification",
            ):
                restore_workflow_backup(self.source, self.destination)

        self.assertEqual(calls, 4)
        self.assertFalse(self.destination.exists())
        temporary_path = captured["temporary_path"]
        self.assertEqual(temporary_path.read_bytes(), replacement)

    def test_source_and_destination_must_be_different(self):
        before = self._source_digest()
        with self.assertRaises(WorkflowBackupRestoreError):
            restore_workflow_backup(self.source, self.source)
        self.assertEqual(self._source_digest(), before)

    def test_cli_json_does_not_disclose_source_or_destination_paths(self):
        destination = self.root / "restore # café.sqlite3"
        output = io.StringIO()
        with patch.object(
            sys,
            "argv",
            ["restore_workflow_backup.py", str(self.source), str(destination)],
        ):
            with contextlib.redirect_stdout(output):
                exit_code = restore_main()
        rendered = output.getvalue()
        report = json.loads(rendered)
        self.assertEqual(exit_code, 0)
        self.assertTrue(report["restored"])
        self.assertNotIn(str(self.source), rendered)
        self.assertNotIn(str(destination), rendered)


    def test_source_change_during_restore_fails_closed_and_cleans_temporary_copy(self):
        real_verify = verify_workflow_backup
        calls = 0

        def mutate_source_before_postcheck(candidate):
            nonlocal calls
            calls += 1
            if calls == 3:
                with _closed_sqlite_connection(self.source) as connection:
                    connection.execute(
                        "CREATE TABLE restore_source_change_probe (value TEXT NOT NULL)"
                    )
                    connection.execute(
                        "INSERT INTO restore_source_change_probe (value) VALUES ('synthetic-change')"
                    )
            return real_verify(candidate)

        with patch(
            "tools.restore_workflow_backup.verify_workflow_backup",
            side_effect=mutate_source_before_postcheck,
        ):
            with self.assertRaisesRegex(WorkflowBackupRestoreError, "source changed during restore"):
                restore_workflow_backup(self.source, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.root.glob(".workflow-restore-*.sqlite3.tmp")), [])
        with _closed_sqlite_connection(self.source) as connection:
            probe = connection.execute(
                "SELECT value FROM restore_source_change_probe"
            ).fetchone()
        self.assertEqual(probe[0], "synthetic-change")

    def test_cli_error_json_does_not_disclose_paths_or_terminal_controls(self):
        missing_source = self.root / "missing\\nsource\\x1b\\u202e.sqlite3"
        destination = self.root / "restore\\npath\\x1b\\u202e.sqlite3"
        output = io.StringIO()
        with patch.object(
            sys,
            "argv",
            ["restore_workflow_backup.py", str(missing_source), str(destination)],
        ):
            with contextlib.redirect_stderr(output):
                exit_code = restore_main()
        rendered = output.getvalue()
        report = json.loads(rendered)
        self.assertEqual(exit_code, 2)
        self.assertFalse(report["restored"])
        self.assertNotIn(str(missing_source), rendered)
        self.assertNotIn(str(destination), rendered)
        self.assertNotIn("\\x1b", rendered)
        self.assertNotIn("\\u202e", rendered)
        self.assertEqual(len(rendered.strip().splitlines()), 1)



    def test_symlink_destination_parent_is_rejected_before_verification(self):
        parent_link = self.root / "destination-parent-link"
        try:
            parent_link.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {type(exc).__name__}")
        destination = parent_link / "restore-through-link.sqlite3"
        with patch("tools.restore_workflow_backup.verify_workflow_backup") as verifier:
            with self.assertRaisesRegex(
                WorkflowBackupRestoreError,
                "parent must be a real directory",
            ):
                restore_workflow_backup(self.source, destination)
            verifier.assert_not_called()
        self.assertFalse((self.root / destination.name).exists())

    def test_symlink_source_parent_is_rejected_before_verification(self):
        parent_link = self.root / "source-parent-link"
        try:
            parent_link.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {type(exc).__name__}")
        linked_source = parent_link / self.source.name
        with patch("tools.restore_workflow_backup.verify_workflow_backup") as verifier:
            with self.assertRaisesRegex(
                WorkflowBackupRestoreError,
                "parent must be a real directory",
            ):
                restore_workflow_backup(linked_source, self.destination)
            verifier.assert_not_called()
        self.assertFalse(self.destination.exists())

    def test_destination_parent_replacement_fails_closed_and_cleans_via_open_directory(self):
        if os.name != "posix":
            self.skipTest("requires POSIX directory-descriptor cleanup")
        parent = self.root / "restore-parent"
        parent.mkdir()
        destination = parent / "restored.sqlite3"
        moved_parent = self.root / "restore-parent-original"
        source_before_run = WorkflowRuntime(
            self.source,
            handlers={"echo": lambda payload: {"echo": payload["value"]}},
            encryption_key=self.key,
        ).get_run(self.run_id)
        source_before_events = list_run_events(
            self.source, "synthetic-restore-cli", self.run_id
        )
        real_verify = verify_workflow_backup
        calls = 0

        def replace_parent_after_temporary_verification(candidate):
            nonlocal calls
            report = real_verify(candidate)
            calls += 1
            if calls == 2:
                parent.rename(moved_parent)
                parent.mkdir()
            return report

        with patch(
            "tools.restore_workflow_backup.verify_workflow_backup",
            side_effect=replace_parent_after_temporary_verification,
        ):
            with self.assertRaisesRegex(
                WorkflowBackupRestoreError,
                "destination parent directory changed during restore",
            ):
                restore_workflow_backup(self.source, destination)

        self.assertEqual(calls, 2)
        self.assertFalse(destination.exists())
        self.assertEqual(list(parent.glob(".workflow-restore-*.sqlite3.tmp")), [])
        self.assertEqual(list(moved_parent.glob(".workflow-restore-*.sqlite3.tmp")), [])
        source_after_run = WorkflowRuntime(
            self.source,
            handlers={"echo": lambda payload: {"echo": payload["value"]}},
            encryption_key=self.key,
        ).get_run(self.run_id)
        source_after_events = list_run_events(
            self.source, "synthetic-restore-cli", self.run_id
        )
        self.assertEqual(source_after_run, source_before_run)
        self.assertEqual(source_after_events, source_before_events)



    def test_source_parent_replacement_after_verification_fails_closed(self):
        source_parent = self.root / "source-parent-race"
        source_parent.mkdir()
        source_copy = source_parent / "source.sqlite3"
        with _closed_sqlite_connection(self.source) as source_connection, _closed_sqlite_connection(source_copy) as copy_connection:
            source_connection.backup(copy_connection)
        moved_parent = self.root / "source-parent-original"
        source_before_run = WorkflowRuntime(
            source_copy,
            handlers={"echo": lambda payload: {"echo": payload["value"]}},
            encryption_key=self.key,
        ).get_run(self.run_id)
        source_before_events = list_run_events(
            source_copy, "synthetic-restore-cli", self.run_id
        )
        real_verify = verify_workflow_backup
        calls = 0

        def replace_source_parent_after_initial_verification(candidate):
            nonlocal calls
            report = real_verify(candidate)
            calls += 1
            if calls == 1:
                source_parent.rename(moved_parent)
                source_parent.mkdir()
            return report

        try:
            with patch(
                "tools.restore_workflow_backup.verify_workflow_backup",
                side_effect=replace_source_parent_after_initial_verification,
            ):
                with self.assertRaisesRegex(
                    WorkflowBackupRestoreError,
                    "source parent directory changed during restore",
                ):
                    restore_workflow_backup(source_copy, self.destination)
            self.assertEqual(calls, 1)
            self.assertFalse(self.destination.exists())
            self.assertEqual(list(self.root.glob(".workflow-restore-*.sqlite3.tmp")), [])
            self.assertEqual(list(source_parent.iterdir()), [])
        finally:
            if source_parent.exists():
                source_parent.rmdir()
            moved_parent.rename(source_parent)

        source_after_run = WorkflowRuntime(
            source_copy,
            handlers={"echo": lambda payload: {"echo": payload["value"]}},
            encryption_key=self.key,
        ).get_run(self.run_id)
        source_after_events = list_run_events(
            source_copy, "synthetic-restore-cli", self.run_id
        )
        self.assertEqual(source_after_run, source_before_run)
        self.assertEqual(source_after_events, source_before_events)

    def test_wal_symlink_replacement_after_preflight_fails_without_destination(self):
        source_parent = self.root / "sidecar-race"
        source_parent.mkdir()
        source_copy = source_parent / "source.sqlite3"
        with _closed_sqlite_connection(self.source) as source_connection, _closed_sqlite_connection(source_copy) as copy_connection:
            source_connection.backup(copy_connection)
        wal_path = Path(f"{source_copy}-wal")
        if wal_path.exists() or wal_path.is_symlink():
            wal_path.unlink()
        target = self.root / "external-wal-race-target"
        target.write_bytes(b"synthetic-wal-race-target")
        target_before = target.read_bytes()
        real_verify = verify_workflow_backup
        calls = 0

        def replace_wal_after_preflight(candidate):
            nonlocal calls
            calls += 1
            if calls == 1:
                wal_path.symlink_to(target)
            return real_verify(candidate)

        try:
            with patch(
                "tools.restore_workflow_backup.verify_workflow_backup",
                side_effect=replace_wal_after_preflight,
            ):
                with self.assertRaises(WorkflowBackupRestoreError):
                    restore_workflow_backup(source_copy, self.destination)
            self.assertEqual(calls, 1)
            self.assertTrue(wal_path.is_symlink())
            self.assertEqual(target.read_bytes(), target_before)
            self.assertFalse(self.destination.exists())
        finally:
            if wal_path.is_symlink():
                wal_path.unlink()



    def test_destination_parent_replacement_after_publish_cleans_both_owned_links(self):
        if os.name != "posix":
            self.skipTest("requires POSIX directory-descriptor cleanup")
        parent = self.root / "restore-publish-parent"
        parent.mkdir()
        destination = parent / "restored.sqlite3"
        moved_parent = self.root / "restore-publish-parent-original"
        source_before_run = WorkflowRuntime(
            self.source,
            handlers={"echo": lambda payload: {"echo": payload["value"]}},
            encryption_key=self.key,
        ).get_run(self.run_id)
        source_before_events = list_run_events(
            self.source, "synthetic-restore-cli", self.run_id
        )
        real_verify = verify_workflow_backup
        calls = 0

        def replace_parent_after_published_verification(candidate):
            nonlocal calls
            report = real_verify(candidate)
            calls += 1
            if calls == 4:
                parent.rename(moved_parent)
                parent.mkdir()
            return report

        with patch(
            "tools.restore_workflow_backup.verify_workflow_backup",
            side_effect=replace_parent_after_published_verification,
        ):
            with self.assertRaisesRegex(
                WorkflowBackupRestoreError,
                "destination parent directory changed during restore",
            ):
                restore_workflow_backup(self.source, destination)

        self.assertEqual(calls, 4)
        self.assertFalse(destination.exists())
        self.assertEqual(list(parent.iterdir()), [])
        self.assertEqual(list(moved_parent.iterdir()), [])
        parent.rmdir()
        moved_parent.rename(parent)

        source_after_run = WorkflowRuntime(
            self.source,
            handlers={"echo": lambda payload: {"echo": payload["value"]}},
            encryption_key=self.key,
        ).get_run(self.run_id)
        source_after_events = list_run_events(
            self.source, "synthetic-restore-cli", self.run_id
        )
        self.assertEqual(source_after_run, source_before_run)
        self.assertEqual(source_after_events, source_before_events)


    def test_failed_restore_reports_operation_owned_temp_file_when_cleanup_cannot_remove_it(self):
        real_verify = verify_workflow_backup
        calls = 0

        def fail_temporary_verification(candidate):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise BackupVerificationError("synthetic temporary verification failure")
            return real_verify(candidate)

        with patch(
            "tools.restore_workflow_backup.verify_workflow_backup",
            side_effect=fail_temporary_verification,
        ), patch("tools.restore_workflow_backup._unlink_if_owned"):
            with self.assertRaisesRegex(
                WorkflowBackupRestoreError,
                "operation-owned artifacts could not be confirmed clean",
            ):
                restore_workflow_backup(self.source, self.destination)

        leftovers = list(self.root.glob(".workflow-restore-*.sqlite3.tmp"))
        self.assertEqual(len(leftovers), 1, "the injected cleanup failure should leave one owned temp file")
        self.assertFalse(self.destination.exists())
        leftovers[0].unlink()


    @unittest.skipUnless(os.name == "nt", "requires Windows path-based cleanup")
    def test_windows_parent_replacement_after_temp_verification_preserves_owned_temp(self):
        original_parent = self.root / "windows-temp-original"
        replacement_parent = self.root / "windows-temp-replacement"
        moved_parent = self.root / "windows-temp-original-moved"
        original_parent.mkdir()
        replacement_parent.mkdir()
        destination = original_parent / "restored.sqlite3"
        real_verify = verify_workflow_backup
        replaced = False

        def verify_then_replace(candidate):
            nonlocal replaced
            report = real_verify(candidate)
            candidate_path = Path(candidate)
            if not replaced and candidate_path.name.startswith(".workflow-restore-"):
                original_parent.rename(moved_parent)
                replacement_parent.rename(original_parent)
                replaced = True
            return report

        try:
            with patch(
                "tools.restore_workflow_backup.verify_workflow_backup",
                side_effect=verify_then_replace,
            ):
                with self.assertRaisesRegex(
                    WorkflowBackupRestoreError,
                    "operation-owned artifacts could not be confirmed clean",
                ):
                    restore_workflow_backup(self.source, destination)

            self.assertTrue(replaced, "the temporary restore verification hook must run")
            leftovers = list(moved_parent.glob(".workflow-restore-*.sqlite3.tmp"))
            self.assertEqual(
                len(leftovers),
                1,
                "path-based cleanup must be skipped after the destination parent changes",
            )
            self.assertFalse(destination.exists(), "the replacement parent must not receive a destination")
            self.assertEqual(
                list(original_parent.iterdir()),
                [],
                "the replacement directory must remain untouched",
            )
        finally:
            if moved_parent.exists():
                for artifact in list(moved_parent.iterdir()):
                    if artifact.is_file() or artifact.is_symlink():
                        artifact.unlink()
                moved_parent.rmdir()

    @unittest.skipUnless(os.name == "nt", "requires Windows path-based cleanup")
    def test_windows_parent_replacement_after_publish_preserves_owned_links(self):
        original_parent = self.root / "windows-published-original"
        replacement_parent = self.root / "windows-published-replacement"
        moved_parent = self.root / "windows-published-original-moved"
        original_parent.mkdir()
        replacement_parent.mkdir()
        destination = original_parent / "restored.sqlite3"
        real_verify = verify_workflow_backup
        replaced = False

        def verify_then_replace(candidate):
            nonlocal replaced
            report = real_verify(candidate)
            if not replaced and Path(candidate) == destination:
                original_parent.rename(moved_parent)
                replacement_parent.rename(original_parent)
                replaced = True
            return report

        try:
            with patch(
                "tools.restore_workflow_backup.verify_workflow_backup",
                side_effect=verify_then_replace,
            ):
                with self.assertRaisesRegex(
                    WorkflowBackupRestoreError,
                    "operation-owned artifacts could not be confirmed clean",
                ):
                    restore_workflow_backup(self.source, destination)

            self.assertTrue(replaced, "the published-destination verification hook must run")
            temporary_links = list(moved_parent.glob(".workflow-restore-*.sqlite3.tmp"))
            self.assertEqual(len(temporary_links), 1)
            published = moved_parent / destination.name
            self.assertTrue(published.is_file())
            temporary_info = temporary_links[0].stat()
            published_info = published.stat()
            self.assertEqual(
                (temporary_info.st_dev, temporary_info.st_ino),
                (published_info.st_dev, published_info.st_ino),
                "the moved original directory must retain only the two owned hard links",
            )
            self.assertEqual(
                list(original_parent.iterdir()),
                [],
                "the replacement directory must remain untouched",
            )
        finally:
            if moved_parent.exists():
                for artifact in list(moved_parent.iterdir()):
                    if artifact.is_file() or artifact.is_symlink():
                        artifact.unlink()
                moved_parent.rmdir()

    @unittest.skipUnless(os.name == "posix", "requires POSIX directory-descriptor cleanup")
    def test_dirfd_unlink_failure_never_falls_back_to_replaced_parent_path(self):
        original_parent = self.root / "dirfd-original"
        replacement_parent = self.root / "dirfd-replacement"
        moved_parent = self.root / "dirfd-original-moved"
        original_parent.mkdir()
        replacement_parent.mkdir()
        owned_path = original_parent / "owned.tmp"
        owned_path.write_bytes(b"synthetic-owned-artifact")
        owned_stat = owned_path.stat()
        identity = (owned_stat.st_dev, owned_stat.st_ino)
        directory_fd = os.open(
            original_parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        replacement_alias: Path | None = None
        try:
            original_parent.rename(moved_parent)
            replacement_parent.rename(original_parent)
            replacement_alias = original_parent / owned_path.name
            os.link(moved_parent / owned_path.name, replacement_alias)

            real_unlink = os.unlink

            def fail_anchored_unlink(path, *, dir_fd=None):
                if dir_fd == directory_fd:
                    raise PermissionError("synthetic anchored unlink failure")
                return real_unlink(path, dir_fd=dir_fd)

            with patch(
                "tools.restore_workflow_backup.os.unlink",
                side_effect=fail_anchored_unlink,
            ):
                _unlink_if_owned(replacement_alias, identity, directory_fd)

            self.assertTrue((moved_parent / owned_path.name).exists())
            self.assertTrue(
                replacement_alias.exists(),
                "failed dirfd cleanup must not fall back and unlink a same-inode alias via the replaced path",
            )
            self.assertEqual(
                (replacement_alias.stat().st_dev, replacement_alias.stat().st_ino),
                identity,
            )
        finally:
            os.close(directory_fd)
            if replacement_alias is not None and replacement_alias.exists():
                replacement_alias.unlink()
            moved_owned = moved_parent / owned_path.name
            if moved_owned.exists():
                moved_owned.unlink()


if __name__ == "__main__":
    unittest.main()
