"""Regression tests for durable workflow side-effect idempotency journal."""
import tempfile
import unittest
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
        next_attempt = self.journal.prepare(
            effect_key="effect-5", workflow_id="p1", run_id="r5",
            effect_name="publish", request={"sample": "synthetic"},
        )
        self.assertTrue(next_attempt.newly_prepared)
        self.assertEqual(next_attempt.state, "pending")


if __name__ == "__main__":
    unittest.main()
