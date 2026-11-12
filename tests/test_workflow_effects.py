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
    EffectIdentityConflict, EffectJournal, EffectJournalError, EffectOutcomeUnknown,
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
        self.assertEqual(row["attempt"], 1)
        with self.assertRaises(EffectOutcomeUnknown):
            migrated.prepare(
                effect_key="legacy-effect", workflow_id="p1", run_id="r-legacy",
                effect_name="publish", request=request,
            )

    def test_reconciliation_retry_permit_is_consumed_once_under_concurrency(self):
        initial = self.journal.prepare(
            effect_key="effect-concurrent", workflow_id="p1", run_id="r-concurrent",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.journal.mark_uncertain("effect-concurrent", attempt=initial.attempt)
        self.journal.reconcile(
            "effect-concurrent", attempt=initial.attempt, confirmed=False
        )

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
        initial = self.journal.prepare(
            effect_key="effect-4", workflow_id="p1", run_id="r4",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.journal.mark_uncertain("effect-4", attempt=initial.attempt)
        self.journal.reconcile(
            "effect-4", attempt=initial.attempt,
            confirmed=True, result={"remote_id": "verified-1"},
        )
        prepared = self.journal.prepare(
            effect_key="effect-4", workflow_id="p1", run_id="r4",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.assertEqual(prepared.state, "confirmed")
        self.assertEqual(prepared.result, {"remote_id": "verified-1"})

    def test_unconfirmed_reconciliation_returns_to_pending_only_after_check(self):
        first_attempt = self.journal.prepare(
            effect_key="effect-5", workflow_id="p1", run_id="r5",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.journal.mark_uncertain("effect-5", attempt=first_attempt.attempt)
        self.journal.reconcile(
            "effect-5", attempt=first_attempt.attempt, confirmed=False
        )
        with self.assertRaises(EffectOutcomeUnknown):
            self.journal.confirm(
                "effect-5", {"remote_id": "not-yet-performed"}, attempt=first_attempt.attempt
            )
        next_attempt = self.journal.prepare(
            effect_key="effect-5", workflow_id="p1", run_id="r5",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.assertTrue(next_attempt.newly_prepared)
        self.assertEqual(next_attempt.state, "pending")
        self.assertEqual(next_attempt.attempt, first_attempt.attempt + 1)
        with self.assertRaises(EffectOutcomeUnknown):
            self.journal.prepare(
                effect_key="effect-5", workflow_id="p1", run_id="r5",
                effect_name="publish", request={"sample": "synthetic"},
            )
        with self.assertRaisesRegex(EffectOutcomeUnknown, "stale effect attempt"):
            self.journal.confirm(
                "effect-5", {"remote_id": "late-first-attempt"}, attempt=first_attempt.attempt
            )
        self.assertEqual(self.journal.get("effect-5")["state"], "pending")
        self.journal.confirm(
            "effect-5", {"remote_id": "verified-after-retry"}, attempt=next_attempt.attempt
        )
        self.assertEqual(self.journal.get("effect-5")["state"], "confirmed")


    def test_late_worker_cannot_confirm_or_downgrade_a_reconciled_retry(self):
        effect_key = "effect-late-worker"
        request = {"sample": "synthetic"}
        started = threading.Event()
        release = threading.Event()

        def slow_first_attempt(_key):
            started.set()
            if not release.wait(timeout=5):
                raise TimeoutError("synthetic first attempt was not released")
            return {"remote_id": "late-first-attempt"}

        def fast_retry(_key):
            return {"remote_id": "second-attempt"}

        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(
                execute_idempotent_effect,
                self.journal,
                effect_key=effect_key,
                workflow_id="p1",
                run_id="r-late-worker",
                effect_name="publish",
                request=request,
                perform=slow_first_attempt,
            )
            self.assertTrue(started.wait(timeout=5))
            try:
                self.journal.mark_uncertain(effect_key, attempt=1)
                self.journal.reconcile(effect_key, attempt=1, confirmed=False)
                retry_future = executor.submit(
                    execute_idempotent_effect,
                    self.journal,
                    effect_key=effect_key,
                    workflow_id="p1",
                    run_id="r-late-worker",
                    effect_name="publish",
                    request=request,
                    perform=fast_retry,
                )
                self.assertEqual(
                    retry_future.result(timeout=10), {"remote_id": "second-attempt"}
                )
            finally:
                release.set()

            with self.assertRaisesRegex(EffectOutcomeUnknown, "stale effect attempt"):
                first_future.result(timeout=10)

        row = self.journal.get(effect_key)
        self.assertEqual(row["state"], "confirmed")
        self.assertEqual(row["attempt"], 2)
        self.assertEqual(row["result"], {"remote_id": "second-attempt"})

    def test_stale_worker_cannot_mark_newer_attempt_uncertain(self):
        first = self.journal.prepare(
            effect_key="effect-fence-uncertain", workflow_id="p1", run_id="r-fence",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.journal.mark_uncertain("effect-fence-uncertain", attempt=first.attempt)
        self.journal.reconcile(
            "effect-fence-uncertain", attempt=first.attempt, confirmed=False
        )
        retry = self.journal.prepare(
            effect_key="effect-fence-uncertain", workflow_id="p1", run_id="r-fence",
            effect_name="publish", request={"sample": "synthetic"},
        )

        with self.assertRaisesRegex(EffectOutcomeUnknown, "stale effect attempt"):
            self.journal.mark_uncertain("effect-fence-uncertain", attempt=first.attempt)

        row = self.journal.get("effect-fence-uncertain")
        self.assertEqual(row["state"], "pending")
        self.assertEqual(row["attempt"], retry.attempt)
        self.assertEqual(row["reconciled"], 0)

    def test_stale_reconciliation_cannot_mutate_newer_attempt(self):
        first = self.journal.prepare(
            effect_key="effect-fence-reconcile", workflow_id="p1", run_id="r-fence",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.journal.mark_uncertain("effect-fence-reconcile", attempt=first.attempt)
        self.journal.reconcile(
            "effect-fence-reconcile", attempt=first.attempt, confirmed=False
        )
        retry = self.journal.prepare(
            effect_key="effect-fence-reconcile", workflow_id="p1", run_id="r-fence",
            effect_name="publish", request={"sample": "synthetic"},
        )

        with self.assertRaisesRegex(EffectOutcomeUnknown, "stale reconciliation"):
            self.journal.reconcile(
                "effect-fence-reconcile", attempt=first.attempt, confirmed=False
            )

        row = self.journal.get("effect-fence-reconcile")
        self.assertEqual(row["state"], "pending")
        self.assertEqual(row["attempt"], retry.attempt)
        self.assertEqual(row["reconciled"], 0)

    def test_confirmed_result_cannot_be_overwritten_by_reconciliation(self):
        prepared = self.journal.prepare(
            effect_key="effect-6", workflow_id="p1", run_id="r6",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.journal.confirm(
            "effect-6", {"remote_id": "verified-original"}, attempt=prepared.attempt
        )
        with self.assertRaises(EffectIdentityConflict):
            self.journal.reconcile(
                "effect-6", attempt=prepared.attempt,
                confirmed=True, result={"remote_id": "different-result"},
            )
        self.assertEqual(
            self.journal.get("effect-6")["result"], {"remote_id": "verified-original"}
        )


    def test_prepare_rejects_unpaired_surrogate_in_effect_identity_before_insert(self):
        valid = {
            "effect_key": "effect-unicode",
            "workflow_id": "project-unicode",
            "run_id": "run-unicode",
            "effect_name": "publish",
        }
        for field in valid:
            with self.subTest(field=field):
                values = dict(valid)
                values[field] = "bad-\ud800"
                with self.assertRaisesRegex(ValueError, "valid Unicode scalar values"):
                    self.journal.prepare(
                        **values,
                        request={"value": "synthetic"},
                    )
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM workflow_effects").fetchone()[0],
                0,
            )

    def test_prepare_rejects_unpaired_surrogate_request_before_insert(self):
        with self.assertRaisesRegex(ValueError, "valid Unicode scalar values"):
            self.journal.prepare(
                effect_key="effect-unicode-request",
                workflow_id="p1",
                run_id="r-unicode-request",
                effect_name="publish",
                request={"note": "bad-\ud800"},
            )
        self.assertIsNone(self.journal.get("effect-unicode-request"))

    def test_confirm_rejects_malformed_result_without_changing_pending_state(self):
        prepared = self.journal.prepare(
            effect_key="effect-unicode-confirm",
            workflow_id="p1",
            run_id="r-unicode-confirm",
            effect_name="publish",
            request={"value": "synthetic"},
        )
        with self.assertRaisesRegex(ValueError, "valid Unicode scalar values"):
            self.journal.confirm(
                "effect-unicode-confirm",
                {"note": "bad-\ud800"},
                attempt=prepared.attempt,
            )
        self.assertEqual(self.journal.get("effect-unicode-confirm")["state"], "pending")

    def test_reconcile_rejects_malformed_result_without_changing_uncertain_state(self):
        prepared = self.journal.prepare(
            effect_key="effect-unicode-reconcile",
            workflow_id="p1",
            run_id="r-unicode-reconcile",
            effect_name="publish",
            request={"value": "synthetic"},
        )
        self.journal.mark_uncertain(
            "effect-unicode-reconcile", attempt=prepared.attempt
        )
        with self.assertRaisesRegex(ValueError, "valid Unicode scalar values"):
            self.journal.reconcile(
                "effect-unicode-reconcile",
                attempt=prepared.attempt,
                confirmed=True,
                result={"note": "bad-\ud800"},
            )
        self.assertEqual(
            self.journal.get("effect-unicode-reconcile")["state"], "uncertain"
        )

    def test_provider_result_with_malformed_unicode_is_marked_uncertain(self):
        calls = []
        def provider(key):
            calls.append(key)
            return {"note": "bad-\ud800"}

        with self.assertRaisesRegex(ValueError, "valid Unicode scalar values"):
            execute_idempotent_effect(
                self.journal,
                effect_key="effect-unicode-provider",
                workflow_id="p1",
                run_id="r-unicode-provider",
                effect_name="publish",
                request={"value": "synthetic"},
                perform=provider,
            )
        self.assertEqual(calls, ["effect-unicode-provider"])
        self.assertEqual(
            self.journal.get("effect-unicode-provider")["state"], "uncertain"
        )

    def test_get_rejects_corrupted_or_non_object_persisted_result(self):
        prepared = self.journal.prepare(
            effect_key="effect-corrupt-result",
            workflow_id="p1",
            run_id="r-corrupt-result",
            effect_name="publish",
            request={"value": "synthetic"},
        )
        self.journal.confirm(
            "effect-corrupt-result",
            {"remote_id": "synthetic-1"},
            attempt=prepared.attempt,
        )
        for stored in ("not-json", "[]"):
            with self.subTest(stored=stored):
                with sqlite3.connect(self.database) as connection:
                    connection.execute(
                        "UPDATE workflow_effects SET result_json = ? WHERE effect_key = ?",
                        (stored, "effect-corrupt-result"),
                    )
                with self.assertRaises(EffectJournalError):
                    self.journal.get("effect-corrupt-result")

    def test_confirm_and_reconcile_require_result_mappings(self):
        prepared = self.journal.prepare(
            effect_key="effect-result-type",
            workflow_id="p1",
            run_id="r-result-type",
            effect_name="publish",
            request={"value": "synthetic"},
        )
        with self.assertRaisesRegex(ValueError, "result must be a mapping"):
            self.journal.confirm(
                "effect-result-type", ["not", "a", "mapping"], attempt=prepared.attempt
            )
        self.journal.mark_uncertain("effect-result-type", attempt=prepared.attempt)
        with self.assertRaisesRegex(ValueError, "result mapping is required"):
            self.journal.reconcile(
                "effect-result-type",
                attempt=prepared.attempt,
                confirmed=True,
                result=["not", "a", "mapping"],
            )
        self.assertEqual(self.journal.get("effect-result-type")["state"], "uncertain")


    def test_confirmed_effect_missing_result_fails_closed_on_read_and_replay(self):
        prepared = self.journal.prepare(
            effect_key="effect-missing-confirmed-result",
            workflow_id="p1",
            run_id="r-missing-confirmed-result",
            effect_name="publish",
            request={"value": "synthetic"},
        )
        self.journal.confirm(
            "effect-missing-confirmed-result",
            {"remote_id": "synthetic-1"},
            attempt=prepared.attempt,
        )
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "UPDATE workflow_effects SET result_json = NULL WHERE effect_key = ?",
                ("effect-missing-confirmed-result",),
            )
        with self.assertRaisesRegex(EffectJournalError, "missing its recorded result"):
            self.journal.get("effect-missing-confirmed-result")
        with self.assertRaisesRegex(EffectJournalError, "missing its recorded result"):
            self.journal.prepare(
                effect_key="effect-missing-confirmed-result",
                workflow_id="p1",
                run_id="r-missing-confirmed-result",
                effect_name="publish",
                request={"value": "synthetic"},
            )

    def test_unconfirmed_effect_with_result_fails_closed(self):
        self.journal.prepare(
            effect_key="effect-unconfirmed-result",
            workflow_id="p1",
            run_id="r-unconfirmed-result",
            effect_name="publish",
            request={"value": "synthetic"},
        )
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "UPDATE workflow_effects SET result_json = ? WHERE effect_key = ?",
                ("{}", "effect-unconfirmed-result"),
            )
        with self.assertRaisesRegex(EffectJournalError, "unconfirmed effect"):
            self.journal.get("effect-unconfirmed-result")
        with self.assertRaisesRegex(EffectJournalError, "unconfirmed effect"):
            self.journal.prepare(
                effect_key="effect-unconfirmed-result",
                workflow_id="p1",
                run_id="r-unconfirmed-result",
                effect_name="publish",
                request={"value": "synthetic"},
            )

    def test_empty_persisted_result_is_not_treated_as_absent(self):
        prepared = self.journal.prepare(
            effect_key="effect-empty-result",
            workflow_id="p1",
            run_id="r-empty-result",
            effect_name="publish",
            request={"value": "synthetic"},
        )
        self.journal.confirm(
            "effect-empty-result",
            {"remote_id": "synthetic-1"},
            attempt=prepared.attempt,
        )
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "UPDATE workflow_effects SET result_json = ? WHERE effect_key = ?",
                ("", "effect-empty-result"),
            )
        with self.assertRaisesRegex(EffectJournalError, "result JSON is invalid"):
            self.journal.get("effect-empty-result")


if __name__ == "__main__":
    unittest.main()
