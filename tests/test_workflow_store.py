"""Tests for the durable workflow event store."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from modules.workflow_contract import SCHEMA_VERSION
from modules.workflow_store import IdempotencyConflict, append_event, initialize_store, list_run_events


def event(**overrides):
    value = {
        "schema_version": SCHEMA_VERSION,
        "event_id": "event-1",
        "idempotency_key": "key-1",
        "workflow_id": "project-1",
        "run_id": "run-1",
        "event_type": "analysis.started",
        "stage": "analysis",
        "status": "running",
        "occurred_at": "2026-10-16T10:30:00+03:00",
        "payload_digest": "a" * 64,
        "evidence_refs": [],
    }
    value.update(overrides)
    return value


class WorkflowStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Path(self.tempdir.name) / "workflow.sqlite3"
        initialize_store(self.database)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_append_and_read_back_persisted_event(self):
        self.assertTrue(append_event(self.database, event()))
        rows = list_run_events(self.database, "project-1", "run-1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event"]["event_id"], "event-1")
        self.assertEqual(rows[0]["status"], "running")

    def test_identical_retry_is_idempotent(self):
        self.assertTrue(append_event(self.database, event()))
        self.assertFalse(append_event(self.database, event()))
        self.assertEqual(len(list_run_events(self.database, "project-1", "run-1")), 1)

    def test_reusing_key_for_different_payload_fails_closed(self):
        self.assertTrue(append_event(self.database, event()))
        with self.assertRaises(IdempotencyConflict):
            append_event(self.database, event(payload_digest="b" * 64))
        self.assertEqual(len(list_run_events(self.database, "project-1", "run-1")), 1)

    def test_event_id_cannot_be_reused_for_another_key(self):
        self.assertTrue(append_event(self.database, event()))
        with self.assertRaises(sqlite3.IntegrityError):
            append_event(self.database, event(idempotency_key="key-2", event_type="analysis.finished"))

    def test_events_are_returned_in_append_order_and_scoped_to_run(self):
        append_event(self.database, event())
        append_event(
            self.database,
            event(
                event_id="event-2", idempotency_key="key-2",
                event_type="analysis.finished", status="succeeded",
                occurred_at="2026-10-16T10:31:00+03:00", payload_digest="b" * 64,
            ),
        )
        append_event(
            self.database,
            event(
                event_id="event-other-run", idempotency_key="key-other",
                run_id="run-2", payload_digest="c" * 64,
            ),
        )
        rows = list_run_events(self.database, "project-1", "run-1")
        self.assertEqual([row["event_id"] for row in rows], ["event-1", "event-2"])

    def test_initialize_is_safe_to_repeat_without_erasing_history(self):
        append_event(self.database, event())
        initialize_store(self.database)
        self.assertEqual(len(list_run_events(self.database, "project-1", "run-1")), 1)


if __name__ == "__main__":
    unittest.main()
