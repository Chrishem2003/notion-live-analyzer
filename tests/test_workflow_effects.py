"""Regression tests for durable workflow side-effect idempotency journal."""
import hashlib
import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from modules.workflow_effects import (
    EffectIdentityConflict, EffectJournal, EffectOutcomeUnknown,
    execute_idempotent_effect,
)


class WorkflowEffectJournalTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Path(self.tempdir.name) / "effects.sqlite3"
        self.journal = EffectJournal(self.database)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_confirmed_effect_is_returned_without_replaying_provider(self):
        calls = []
        perform = lambda key: (calls.append(key) or {"remote_id": "synthetic-42"})
        result = execute_idempotent_effect(
            self.journal, effect_key="effect-1", workflow_id="p1", run_id="r1",
            effect_name="publish_result", request={"record": "synthetic"},
            perform=perform,
        )
        replay = execute_idempotent_effect(
            self.journal, effect_key="effect-1", workflow_id="p1", run_id="r1",
            effect_name="publish_result", request={"record": "synthetic"},
            perform=perform,
        )
        self.assertEqual(result, {"remote_id": "synthetic-42"})
        self.assertEqual(replay, result)
        self.assertEqual(calls, ["effect-1"])
        self.assertEqual(self.journal.get("effect-1")["state"], "confirmed")

    def test_ambiguous_provider_failure_is_not_blindly_replayed(self):
        calls = []
        def ambiguous(key):
            calls.append(key)
            raise TimeoutError("synthetic timeout after request may have reached provider")
        with self.assertRaises(TimeoutError):
            execute_idempotent_effect(
                self.journal, effect_key="effect-2", workflow_id="p1", run_id="r2",
                effect_name="notion_create", request={"title": "synthetic"},
                perform=ambiguous,
            )
        with self.assertRaises(EffectOutcomeUnknown):
            self.journal.prepare(
                effect_key="effect-2", workflow_id="p1", run_id="r2",
                effect_name="notion_create", request={"title": "synthetic"},
            )
        self.assertEqual(calls, ["effect-2"])
        self.assertEqual(self.journal.get("effect-2")["state"], "uncertain")

    def test_initial_pending_effect_cannot_be_replayed_without_reconciliation(self):
        self.journal.prepare(
            effect_key="effect-pending", workflow_id="p1", run_id="r-pending",
            effect_name="publish", request={"sample": "synthetic"},
        )
        with self.assertRaises(EffectOutcomeUnknown):
            self.journal.prepare(
                effect_key="effect-pending", workflow_id="p1", run_id="r-pending",
                effect_name="publish", request={"sample": "synthetic"},
            )

    def test_legacy_journal_migration_preserves_pending_rows_as_not_reconciled(self):
        legacy_db = Path(self.tempdir.name) / "legacy-effects.sqlite3"
        request = {"sample": "legacy"}
        encoded = json.dumps(
            request, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        )
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        timestamp = "2026-11-04T00:00:00+00:00"
        with sqlite3.connect(legacy_db) as connection:
            connection.execute(
                """
                CREATE TABLE workflow_effects (
                    effect_key TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    effect_name TEXT NOT NULL,
                    request_digest TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('pending', 'confirmed', 'uncertain')),
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """INSERT INTO workflow_effects
                (effect_key, workflow_id, run_id, effect_name, request_digest,
                 state, result_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'pending', NULL, ?, ?)""",
                ("legacy-effect", "p1", "r-legacy", "publish", digest, timestamp, timestamp),
            )

        migrated = EffectJournal(legacy_db)
        row = migrated.get("legacy-effect")
        self.assertEqual(row["state"], "pending")
        self.assertEqual(row["reconciled"], 0)
        with self.assertRaises(EffectOutcomeUnknown):
            migrated.prepare(
                effect_key="legacy-effect", workflow_id="p1", run_id="r-legacy",
                effect_name="publish", request=request,
            )

    def test_reconciliation_retry_permit_is_consumed_once_under_concurrency(self):
        self.journal.prepare(
            effect_key="effect-concurrent", workflow_id="p1", run_id="r-concurrent",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.journal.mark_uncertain("effect-concurrent")
        self.journal.reconcile("effect-concurrent", confirmed=False)

        barrier = threading.Barrier(3)

        def attempt():
            barrier.wait(timeout=5)
            try:
                result = self.journal.prepare(
                    effect_key="effect-concurrent", workflow_id="p1", run_id="r-concurrent",
                    effect_name="publish", request={"sample": "synthetic"},
                )
                return ("prepared", result)
            except EffectOutcomeUnknown:
                return ("blocked", None)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(attempt) for _ in range(2)]
            barrier.wait(timeout=5)
            results = [future.result(timeout=10) for future in futures]

        self.assertEqual(sum(state == "prepared" for state, _ in results), 1)
        self.assertEqual(sum(state == "blocked" for state, _ in results), 1)
        self.assertEqual(self.journal.get("effect-concurrent")["reconciled"], 0)

    def test_reusing_key_for_different_request_is_rejected(self):
        self.journal.prepare(
            effect_key="effect-3", workflow_id="p1", run_id="r3",
            effect_name="send", request={"message": "one"},
        )
        with self.assertRaises(EffectIdentityConflict):
            self.journal.prepare(
                effect_key="effect-3", workflow_id="p1", run_id="r3",
                effect_name="send", request={"message": "different"},
            )

    def test_uncertain_effect_can_be_reconciled_as_confirmed(self):
        self.journal.prepare(
            effect_key="effect-4", workflow_id="p1", run_id="r4",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.journal.mark_uncertain("effect-4")
        self.journal.reconcile("effect-4", confirmed=True, result={"remote_id": "verified-1"})
        prepared = self.journal.prepare(
            effect_key="effect-4", workflow_id="p1", run_id="r4",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.assertEqual(prepared.state, "confirmed")
        self.assertEqual(prepared.result, {"remote_id": "verified-1"})

    def test_unconfirmed_reconciliation_returns_to_pending_only_after_check(self):
        self.journal.prepare(
            effect_key="effect-5", workflow_id="p1", run_id="r5",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.journal.mark_uncertain("effect-5")
        self.journal.reconcile("effect-5", confirmed=False)
        with self.assertRaises(EffectOutcomeUnknown):
            self.journal.confirm("effect-5", {"remote_id": "not-yet-performed"})
        next_attempt = self.journal.prepare(
            effect_key="effect-5", workflow_id="p1", run_id="r5",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.assertTrue(next_attempt.newly_prepared)
        self.assertEqual(next_attempt.state, "pending")
        with self.assertRaises(EffectOutcomeUnknown):
            self.journal.prepare(
                effect_key="effect-5", workflow_id="p1", run_id="r5",
                effect_name="publish", request={"sample": "synthetic"},
            )
        self.journal.confirm("effect-5", {"remote_id": "verified-after-retry"})
        self.assertEqual(self.journal.get("effect-5")["state"], "confirmed")


    def test_confirmed_result_cannot_be_overwritten_by_reconciliation(self):
        self.journal.prepare(
            effect_key="effect-6", workflow_id="p1", run_id="r6",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.journal.confirm("effect-6", {"remote_id": "verified-original"})
        with self.assertRaises(EffectIdentityConflict):
            self.journal.reconcile(
                "effect-6", confirmed=True, result={"remote_id": "different-result"}
            )
        self.assertEqual(
            self.journal.get("effect-6")["result"], {"remote_id": "verified-original"}
        )


if __name__ == "__main__":
    unittest.main()
