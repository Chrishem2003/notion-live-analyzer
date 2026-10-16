"""Tests for the persistent local workflow runtime."""
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from modules.workflow_runtime import HandlerNotRegistered, WorkflowRuntime
from modules.workflow_store import list_run_events
from modules.workflow_storage import WorkflowStorageError
from modules.workflow_key_rotation import WorkflowKeyRotationError, rotate_workflow_encryption_key
from cryptography.fernet import Fernet


class WorkflowRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Path(self.tempdir.name) / "runtime.sqlite3"

    def tearDown(self):
        self.tempdir.cleanup()

    def test_submit_persists_queued_run_and_input(self):
        runtime = WorkflowRuntime(self.database, handlers={"echo": lambda data: {"echo": data["value"]}})
        run_id = runtime.submit(workflow_id="project-1", task_type="echo", payload={"value": 7})
        loaded = WorkflowRuntime(self.database, handlers={"echo": lambda data: {"echo": data["value"]}}).get_run(run_id)
        self.assertEqual(loaded["status"], "queued")
        self.assertEqual(loaded["input"], {"value": 7})
        self.assertEqual(loaded["attempt"], 0)

    def test_unregistered_task_type_is_rejected_before_enqueue(self):
        runtime = WorkflowRuntime(self.database)
        with self.assertRaises(HandlerNotRegistered):
            runtime.submit(workflow_id="p1", task_type="arbitrary_import", payload={})
        self.assertEqual(runtime.list_runs(), [])

    def test_registered_handler_executes_and_persists_result(self):
        runtime = WorkflowRuntime(self.database, handlers={"sum": lambda data: {"total": sum(data["values"])}})
        run_id = runtime.submit(workflow_id="p1", task_type="sum", payload={"values": [2, 3, 5]})
        completed = runtime.execute_next()
        self.assertEqual(completed["run_id"], run_id)
        self.assertEqual(completed["status"], "succeeded")
        self.assertEqual(completed["result"], {"total": 10})
        self.assertEqual(completed["attempt"], 1)

    def test_failed_attempt_is_requeued_then_preserved_as_failed(self):
        calls = {"count": 0}

        def always_fails(_payload):
            calls["count"] += 1
            raise RuntimeError("deliberate test failure")

        runtime = WorkflowRuntime(self.database, handlers={"unstable": always_fails})
        run_id = runtime.submit(workflow_id="p1", task_type="unstable", payload={}, max_attempts=2)
        first = runtime.execute_next()
        self.assertEqual(first["status"], "queued")
        self.assertEqual(first["attempt"], 1)
        second = runtime.execute_next()
        self.assertEqual(second["status"], "failed")
        self.assertEqual(second["attempt"], 2)
        self.assertIn("deliberate test failure", second["error_message"])
        self.assertEqual(calls["count"], 2)
        history = list_run_events(self.database, "p1", run_id)
        self.assertEqual([item["status"] for item in history], ["queued", "running", "queued", "running", "failed"])

    def test_no_queued_work_returns_none(self):
        runtime = WorkflowRuntime(self.database, handlers={"echo": lambda data: dict(data)})
        self.assertIsNone(runtime.execute_next())

    def test_attempt_limit_is_bounded(self):
        runtime = WorkflowRuntime(self.database, handlers={"echo": lambda data: dict(data)})
        with self.assertRaises(ValueError):
            runtime.submit(workflow_id="p1", task_type="echo", payload={}, max_attempts=99)

    def test_oversized_input_is_rejected_before_persistence(self):
        runtime = WorkflowRuntime(self.database, handlers={"echo": lambda data: dict(data)})
        with self.assertRaisesRegex(ValueError, "payload exceeds"):
            runtime.submit(workflow_id="p1", task_type="echo", payload={"text": "x" * 1_000_001})
        self.assertEqual(runtime.list_runs(), [])

    def test_oversized_handler_result_fails_with_bounded_error(self):
        runtime = WorkflowRuntime(
            self.database,
            handlers={"large_result": lambda data: {"text": "x" * 1_000_001}},
        )
        run_id = runtime.submit(workflow_id="p1", task_type="large_result", payload={}, max_attempts=1)
        result = runtime.execute_run(run_id)
        self.assertEqual(result["status"], "failed")
        self.assertIn("result exceeds", result["error_message"])
        self.assertIsNone(result["result"])

    def test_submit_rolls_back_run_if_event_append_fails(self):
        runtime = WorkflowRuntime(self.database, handlers={"echo": lambda data: dict(data)})
        with patch("modules.workflow_runtime._event_payload", return_value={"invalid": "event"}):
            with self.assertRaises(Exception):
                runtime.submit(workflow_id="p1", task_type="echo", payload={"x": 1})
        self.assertEqual(runtime.list_runs(), [])

    def test_execution_event_and_state_are_committed_together(self):
        runtime = WorkflowRuntime(self.database, handlers={"echo": lambda data: {"ok": True}})
        run_id = runtime.submit(workflow_id="p1", task_type="echo", payload={})
        with patch("modules.workflow_runtime._event_payload", return_value={"invalid": "event"}):
            with self.assertRaises(Exception):
                runtime.execute_run(run_id)
        # The claim and its running event are one transaction: a rejected event
        # must not leave the run falsely marked as running.
        self.assertEqual(runtime.get_run(run_id)["status"], "queued")
        self.assertEqual(
            [event["status"] for event in list_run_events(self.database, "p1", run_id)],
            ["queued"],
        )

    def test_recover_stale_running_attempt_requeues_when_attempts_remain(self):
        runtime = WorkflowRuntime(self.database, handlers={"echo": lambda data: dict(data)})
        run_id = runtime.submit(workflow_id="p1", task_type="echo", payload={}, max_attempts=3)
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "UPDATE workflow_runs SET status='running', attempt=1, claimed_at=? WHERE run_id=?",
                ("2000-01-01T00:00:00+00:00", run_id),
            )
        recovered = runtime.recover_stale_runs(older_than_seconds=60)
        self.assertEqual(recovered, [{"run_id": run_id, "status": "queued", "attempt": 1}])
        self.assertEqual(runtime.get_run(run_id)["status"], "queued")
        self.assertEqual(list_run_events(self.database, "p1", run_id)[-1]["status"], "queued")

    def test_recover_stale_run_fails_when_attempt_budget_is_exhausted(self):
        runtime = WorkflowRuntime(self.database, handlers={"echo": lambda data: dict(data)})
        run_id = runtime.submit(workflow_id="p1", task_type="echo", payload={}, max_attempts=1)
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "UPDATE workflow_runs SET status='running', attempt=1, claimed_at=? WHERE run_id=?",
                ("2000-01-01T00:00:00+00:00", run_id),
            )
        recovered = runtime.recover_stale_runs(older_than_seconds=60)
        self.assertEqual(recovered[0]["status"], "failed")
        self.assertEqual(runtime.get_run(run_id)["status"], "failed")


    def test_encrypted_payloads_round_trip_and_are_not_plaintext_in_sqlite(self):
        key = Fernet.generate_key()
        secret_value = "synthetic-secret-fixture-not-for-production"
        runtime = WorkflowRuntime(
            self.database,
            handlers={"echo": lambda data: {"echo": data["value"]}},
            encryption_key=key,
        )
        run_id = runtime.submit(
            workflow_id="demo-project",
            task_type="echo",
            payload={"value": secret_value},
        )
        runtime.execute_run(run_id)

        with sqlite3.connect(self.database) as connection:
            input_value, result_value = connection.execute(
                "SELECT input_json, result_json FROM workflow_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        self.assertTrue(input_value.startswith("enc:v1:"))
        self.assertTrue(result_value.startswith("enc:v1:"))
        self.assertNotIn(secret_value, input_value)
        self.assertNotIn(secret_value, result_value)

        reopened = WorkflowRuntime(
            self.database,
            handlers={"echo": lambda data: {"echo": data["value"]}},
            encryption_key=key,
        )
        saved = reopened.get_run(run_id)
        self.assertEqual(saved["input"], {"value": secret_value})
        self.assertEqual(saved["result"], {"echo": secret_value})

    def test_configured_key_migrates_legacy_plaintext_rows(self):
        legacy = WorkflowRuntime(
            self.database,
            handlers={"echo": lambda data: {"echo": data["value"]}},
        )
        run_id = legacy.submit(
            workflow_id="demo-project",
            task_type="echo",
            payload={"value": "legacy-synthetic-value"},
        )
        legacy.execute_run(run_id)
        with sqlite3.connect(self.database) as connection:
            raw_input = connection.execute(
                "SELECT input_json FROM workflow_runs WHERE run_id = ?", (run_id,)
            ).fetchone()[0]
        self.assertNotIn("enc:v1:", raw_input)

        key = Fernet.generate_key()
        migrated = WorkflowRuntime(
            self.database,
            handlers={"echo": lambda data: {"echo": data["value"]}},
            encryption_key=key,
        )
        with sqlite3.connect(self.database) as connection:
            migrated_input, migrated_result = connection.execute(
                "SELECT input_json, result_json FROM workflow_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        self.assertTrue(migrated_input.startswith("enc:v1:"))
        self.assertTrue(migrated_result.startswith("enc:v1:"))
        self.assertEqual(migrated.get_run(run_id)["input"], {"value": "legacy-synthetic-value"})

    def test_wrong_key_fails_closed_when_reading_encrypted_payload(self):
        key = Fernet.generate_key()
        runtime = WorkflowRuntime(
            self.database,
            handlers={"echo": lambda data: dict(data)},
            encryption_key=key,
        )
        run_id = runtime.submit(workflow_id="p1", task_type="echo", payload={"value": "demo"})
        with self.assertRaises(WorkflowStorageError):
            WorkflowRuntime(
                self.database,
                handlers={"echo": lambda data: dict(data)},
                encryption_key=Fernet.generate_key(),
            ).get_run(run_id)


    def test_key_rotation_creates_backup_and_preserves_readback(self):
        old_key = Fernet.generate_key()
        new_key = Fernet.generate_key()
        runtime = WorkflowRuntime(
            self.database,
            handlers={"echo": lambda data: {"echo": data["value"]}},
            encryption_key=old_key,
        )
        run_id = runtime.submit(
            workflow_id="demo-project",
            task_type="echo",
            payload={"value": "rotation-fixture"},
        )
        runtime.execute_run(run_id)
        backup = Path(self.tempdir.name) / "runtime-before-rotation.sqlite3"

        outcome = rotate_workflow_encryption_key(self.database, backup, old_key, new_key)
        self.assertTrue(backup.is_file())
        self.assertEqual(outcome["rows_updated"], 1)
        self.assertGreaterEqual(outcome["fields_updated"], 2)

        rotated = WorkflowRuntime(
            self.database,
            handlers={"echo": lambda data: {"echo": data["value"]}},
            encryption_key=new_key,
        )
        self.assertEqual(rotated.get_run(run_id)["input"], {"value": "rotation-fixture"})
        self.assertEqual(rotated.get_run(run_id)["result"], {"echo": "rotation-fixture"})

        backed_up = WorkflowRuntime(
            backup,
            handlers={"echo": lambda data: {"echo": data["value"]}},
            encryption_key=old_key,
        )
        self.assertEqual(backed_up.get_run(run_id)["input"], {"value": "rotation-fixture"})

    def test_failed_key_rotation_rolls_back_and_retains_backup(self):
        old_key = Fernet.generate_key()
        runtime = WorkflowRuntime(
            self.database,
            handlers={"echo": lambda data: dict(data)},
            encryption_key=old_key,
        )
        run_id = runtime.submit(workflow_id="p1", task_type="echo", payload={"value": "preserve-me"})
        before = sqlite3.connect(self.database).execute(
            "SELECT input_json FROM workflow_runs WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        backup = Path(self.tempdir.name) / "runtime-safe-backup.sqlite3"

        with self.assertRaises(WorkflowKeyRotationError):
            rotate_workflow_encryption_key(
                self.database, backup, Fernet.generate_key(), Fernet.generate_key()
            )
        self.assertTrue(backup.is_file())
        after = sqlite3.connect(self.database).execute(
            "SELECT input_json FROM workflow_runs WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        self.assertEqual(after, before)
        self.assertEqual(
            WorkflowRuntime(
                self.database,
                handlers={"echo": lambda data: dict(data)},
                encryption_key=old_key,
            ).get_run(run_id)["input"],
            {"value": "preserve-me"},
        )


if __name__ == "__main__":
    unittest.main()
