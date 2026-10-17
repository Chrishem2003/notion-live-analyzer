"""Regression tests for the versioned workflow hand-off contract."""
import unittest

from modules.workflow_contract import (
    SCHEMA_VERSION,
    WorkflowContractError,
    WorkflowEvent,
    canonical_payload_digest,
    idempotency_key,
    validate_status_transition,
)


def valid_event(**overrides):
    data = {
        "schema_version": SCHEMA_VERSION,
        "event_id": "evt-001",
        "idempotency_key": "idem-001",
        "workflow_id": "project-42",
        "run_id": "run-001",
        "event_type": "analysis.completed",
        "stage": "analysis",
        "status": "succeeded",
        "occurred_at": "2026-10-16T10:30:00+03:00",
        "payload_digest": "a" * 64,
        "evidence_refs": ["https://example.invalid/evidence/1"],
    }
    data.update(overrides)
    return data


class WorkflowContractTests(unittest.TestCase):
    def test_valid_event_normalizes_evidence_refs(self):
        event = WorkflowEvent.from_mapping(valid_event())
        self.assertEqual(event.stage, "analysis")
        self.assertEqual(event.to_dict()["evidence_refs"], ["https://example.invalid/evidence/1"])

    def test_rejects_unknown_schema_version(self):
        with self.assertRaisesRegex(WorkflowContractError, "unsupported schema_version"):
            WorkflowEvent.from_mapping(valid_event(schema_version="99.0"))

    def test_rejects_unknown_stage_and_status(self):
        with self.assertRaisesRegex(WorkflowContractError, "unsupported stage"):
            WorkflowEvent.from_mapping(valid_event(stage="magic"))
        with self.assertRaisesRegex(WorkflowContractError, "unsupported status"):
            WorkflowEvent.from_mapping(valid_event(status="pretend-success"))

    def test_requires_timezone_aware_timestamp(self):
        with self.assertRaisesRegex(WorkflowContractError, "include a timezone"):
            WorkflowEvent.from_mapping(valid_event(occurred_at="2026-10-16T10:30:00"))

    def test_rejects_bad_payload_digest_and_empty_identity(self):
        with self.assertRaisesRegex(WorkflowContractError, "SHA-256"):
            WorkflowEvent.from_mapping(valid_event(payload_digest="not-a-hash"))
        with self.assertRaisesRegex(WorkflowContractError, "run_id"):
            WorkflowEvent.from_mapping(valid_event(run_id="  "))

    def test_payload_digest_is_independent_of_mapping_key_order(self):
        self.assertEqual(
            canonical_payload_digest({"b": 2, "a": 1}),
            canonical_payload_digest({"a": 1, "b": 2}),
        )

    def test_payload_digest_rejects_non_finite_json(self):
        with self.assertRaisesRegex(WorkflowContractError, "finite JSON"):
            canonical_payload_digest({"value": float("nan")})

    def test_idempotency_key_is_stable_and_scoped_to_run(self):
        first = idempotency_key("w1", "r1", "analysis.completed", "a" * 64)
        self.assertEqual(first, idempotency_key("w1", "r1", "analysis.completed", "a" * 64))
        self.assertNotEqual(first, idempotency_key("w1", "r2", "analysis.completed", "a" * 64))

    def test_terminal_status_cannot_be_rewritten(self):
        for terminal in ("succeeded", "blocked", "cancelled"):
            with self.subTest(terminal=terminal):
                with self.assertRaisesRegex(WorkflowContractError, "terminal status"):
                    validate_status_transition(terminal, "failed")
                with self.assertRaisesRegex(WorkflowContractError, "terminal status"):
                    validate_status_transition(terminal, "running")
                validate_status_transition(terminal, terminal)

    def test_failed_attempt_retry_requires_new_run(self):
        with self.assertRaisesRegex(WorkflowContractError, "new run_id"):
            validate_status_transition("failed", "running")
        validate_status_transition("failed", "failed")


if __name__ == "__main__":
    unittest.main()
