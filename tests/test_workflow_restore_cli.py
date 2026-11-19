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
)
from tools.verify_workflow_backup import BackupVerificationError, verify_workflow_backup


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
        with sqlite3.connect(self.destination) as connection:
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


if __name__ == "__main__":
    unittest.main()
