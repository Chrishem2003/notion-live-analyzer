"""Tests for the persistent local workflow runtime."""
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from modules.workflow_runtime import HandlerNotRegistered, WorkflowRuntime
from modules.workflow_store import list_run_events
from modules.workflow_store import list_run_events


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


if __name__ == "__main__":
    unittest.main()
