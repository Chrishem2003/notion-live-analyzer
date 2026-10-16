"""Tests for the read-only workflow SQLite backup verifier."""
from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools.verify_workflow_backup import BackupVerificationError, verify_workflow_backup


class WorkflowBackupVerificationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.backup = Path(self.tempdir.name) / "workflow-backup.sqlite3"

    def tearDown(self):
        self.tempdir.cleanup()

    def make_valid_backup(self):
        with sqlite3.connect(self.backup) as connection:
            connection.executescript(
                """
                CREATE TABLE workflow_runs (
                    run_id TEXT PRIMARY KEY,
                    input_json TEXT,
                    result_json TEXT,
                    error_message TEXT
                );
                CREATE TABLE workflow_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    status TEXT NOT NULL
                );
                INSERT INTO workflow_runs VALUES
                    ('run-1', 'enc:v1:input', 'enc:v1:result', NULL),
                    ('run-2', '{"synthetic": true}', NULL, 'enc:v1:error');
                INSERT INTO workflow_events (event_id, idempotency_key, workflow_id, run_id, status)
                    VALUES ('evt-1', 'idem-1', 'demo', 'run-1', 'queued'),
                           ('evt-2', 'idem-2', 'demo', 'run-1', 'succeeded');
                """
            )

    def digest(self):
        return hashlib.sha256(self.backup.read_bytes()).hexdigest()

    def test_valid_backup_is_verified_read_only_and_reports_counts(self):
        self.make_valid_backup()
        before = self.digest()
        result = verify_workflow_backup(self.backup)
        self.assertTrue(result["verified"])
        self.assertEqual(result["sqlite_integrity"], "ok")
        self.assertEqual(result["workflow_runs"], 2)
        self.assertEqual(result["workflow_events"], 2)
        self.assertEqual(result["encrypted_payload_field_counts"]["input_json"], 1)
        self.assertEqual(result["encrypted_payload_field_counts"]["result_json"], 1)
        self.assertEqual(result["encrypted_payload_field_counts"]["error_message"], 1)
        self.assertEqual(self.digest(), before, "verification must not modify the backup")

    def test_missing_backup_fails_without_creating_file(self):
        with self.assertRaisesRegex(BackupVerificationError, "does not exist"):
            verify_workflow_backup(self.backup)
        self.assertFalse(self.backup.exists())

    def test_missing_required_table_fails_closed(self):
        with sqlite3.connect(self.backup) as connection:
            connection.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY)")
        with self.assertRaisesRegex(BackupVerificationError, "missing required workflow tables"):
            verify_workflow_backup(self.backup)

    def test_incomplete_workflow_schema_fails_closed(self):
        with sqlite3.connect(self.backup) as connection:
            connection.execute("CREATE TABLE workflow_runs (run_id TEXT)")
            connection.execute(
                "CREATE TABLE workflow_events (event_id TEXT, idempotency_key TEXT, "
                "workflow_id TEXT, run_id TEXT, status TEXT)"
            )
        with self.assertRaisesRegex(BackupVerificationError, "workflow_runs schema is incomplete"):
            verify_workflow_backup(self.backup)

    def test_non_sqlite_file_fails_with_safe_error(self):
        self.backup.write_text("not a sqlite database", encoding="utf-8")
        with self.assertRaisesRegex(BackupVerificationError, "could not be verified safely"):
            verify_workflow_backup(self.backup)


    def test_real_runtime_backup_passes_verifier_after_sqlite_backup(self):
        from cryptography.fernet import Fernet
        from modules.workflow_runtime import WorkflowRuntime

        source = Path(self.tempdir.name) / "runtime-source.sqlite3"
        key = Fernet.generate_key()
        runtime = WorkflowRuntime(
            source,
            handlers={"echo": lambda payload: {"echo": payload["value"]}},
            encryption_key=key,
        )
        run_id = runtime.submit(
            workflow_id="synthetic-verification",
            task_type="echo",
            payload={"value": "synthetic-backup-fixture"},
        )
        runtime.execute_run(run_id)

        with sqlite3.connect(source) as source_connection:
            with sqlite3.connect(self.backup) as backup_connection:
                source_connection.backup(backup_connection)

        result = verify_workflow_backup(self.backup)
        self.assertTrue(result["verified"])
        self.assertGreaterEqual(result["workflow_runs"], 1)
        self.assertGreaterEqual(result["workflow_events"], 3)
        self.assertEqual(
            result["encrypted_payload_field_counts"]["input_json"],
            result["workflow_runs"],
        )
        self.assertEqual(
            result["encrypted_payload_field_counts"]["result_json"],
            result["workflow_runs"],
        )


if __name__ == "__main__":
    unittest.main()
