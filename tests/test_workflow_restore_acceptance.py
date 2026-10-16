"""End-to-end restore acceptance tests for encrypted workflow runtime backups.

These tests exercise local SQLite backup/restore mechanics only. They do not
replace authenticated staging verification of host storage, secrets, or Notion.
"""
from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet

from modules.workflow_runtime import WorkflowRuntime
from modules.workflow_storage import WorkflowStorageError
from modules.workflow_store import list_run_events


class WorkflowRestoreAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.source = self.root / "source.sqlite3"
        self.backup = self.root / "backup.sqlite3"
        self.restored = self.root / "restored.sqlite3"
        self.key = Fernet.generate_key()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_sqlite_backup_restore_preserves_encrypted_payload_and_event_order(self):
        runtime = WorkflowRuntime(
            self.source,
            handlers={"echo": lambda payload: {"echo": payload["value"]}},
            encryption_key=self.key,
        )
        run_id = runtime.submit(
            workflow_id="synthetic-restore-acceptance",
            task_type="echo",
            payload={"value": "restore-fixture-only"},
        )
        completed = runtime.execute_run(run_id)
        self.assertEqual(completed["status"], "succeeded")

        with sqlite3.connect(self.source) as source_connection:
            with sqlite3.connect(self.backup) as backup_connection:
                source_connection.backup(backup_connection)

        with sqlite3.connect(self.backup) as backup_connection:
            with sqlite3.connect(self.restored) as restored_connection:
                backup_connection.backup(restored_connection)

        restored_runtime = WorkflowRuntime(
            self.restored,
            handlers={"echo": lambda payload: {"echo": payload["value"]}},
            encryption_key=self.key,
        )
        restored_run = restored_runtime.get_run(run_id)
        self.assertEqual(restored_run["status"], "succeeded")
        self.assertEqual(restored_run["input"], {"value": "restore-fixture-only"})
        self.assertEqual(restored_run["result"], {"echo": "restore-fixture-only"})
        events = list_run_events(self.restored, "synthetic-restore-acceptance", run_id)
        self.assertEqual(
            [event["status"] for event in events],
            ["queued", "running", "succeeded"],
        )

        # Confirm stored payloads are encrypted at rest, not merely decrypted on read.
        with sqlite3.connect(self.restored) as connection:
            stored_input = connection.execute(
                "SELECT input_json FROM workflow_runs WHERE run_id = ?", (run_id,)
            ).fetchone()[0]
        self.assertTrue(stored_input.startswith("enc:v1:"))
        self.assertNotIn("restore-fixture-only", stored_input)

    def test_wrong_key_restore_fails_closed_without_mutating_restored_file(self):
        runtime = WorkflowRuntime(
            self.source,
            handlers={"echo": lambda payload: {"echo": payload["value"]}},
            encryption_key=self.key,
        )
        runtime.submit(
            workflow_id="synthetic-restore-acceptance",
            task_type="echo",
            payload={"value": "restore-fixture-only"},
        )
        with sqlite3.connect(self.source) as source_connection:
            with sqlite3.connect(self.restored) as restored_connection:
                source_connection.backup(restored_connection)

        before = hashlib.sha256(self.restored.read_bytes()).hexdigest()
        with self.assertRaises(WorkflowStorageError):
            WorkflowRuntime(
                self.restored,
                handlers={"echo": lambda payload: {"echo": payload["value"]}},
                encryption_key=Fernet.generate_key(),
            )
        after = hashlib.sha256(self.restored.read_bytes()).hexdigest()
        self.assertEqual(after, before, "wrong-key startup must not mutate the restored database")


if __name__ == "__main__":
    unittest.main()
