from __future__ import annotations

import hashlib
import unittest

from nema_agora.measurement_idempotency import canonical_payload_sha256
from nema_agora.measurement_write_contract import (
    MeasurementWriteContractError,
    build_measurement_rpc_request,
)


class MeasurementWriteContractTests(unittest.TestCase):
    def setUp(self):
        self.artifact = b"field-survey-evidence-v1"
        self.record = {
            "indicator_id": "community_reports",
            "status": "measured",
            "period_start": "2026-10-01",
            "period_end": "2026-10-26",
            "value": 12,
            "unit": "count",
            "source_record_ids": ["field-log-001"],
            "evidence_reference": "evidence/field-log-001.txt",
            "evidence_sha256": hashlib.sha256(self.artifact).hexdigest(),
            "method_version": "field-count-v1",
            "calculated_at": "2026-10-26T10:00:00+03:00",
            "definition_version": "1.0",
            "reporting_timezone": "Africa/Kampala",
        }
        self.indicator = {"id": "community_reports", "unit": "count", "calculation": "Count records"}

    def build(self, **overrides):
        args = dict(
            measurement_id="measurement-001",
            idempotency_key="submission-001",
            record=self.record,
            indicator=self.indicator,
            evidence_bytes=self.artifact,
            authenticated_actor_id="user-123",
            authenticated_actor_role="submitter",
        )
        args.update(overrides)
        return build_measurement_rpc_request(**args)

    def test_maps_valid_record_and_hashes_exact_rpc_record(self):
        result = self.build()
        self.assertEqual(result["p_record"]["reporting_period_start"], "2026-10-01")
        self.assertEqual(result["p_record"]["source_refs"], ["field-log-001"])
        self.assertEqual(result["p_payload_sha256"], canonical_payload_sha256(result["p_record"]))
        self.assertTrue(result["evidence_artifact_bytes_verified"])
        self.assertFalse(result["evidence_authenticity_verified"])

    def test_rejects_mismatched_evidence_bytes(self):
        with self.assertRaisesRegex(MeasurementWriteContractError, "SHA-256"):
            self.build(evidence_bytes=b"different bytes")

    def test_rejects_verified_state_from_submit_path(self):
        self.record["status"] = "verified"
        self.record.update({
            "reviewer_id": "reviewer-2",
            "reviewed_at": "2026-10-26T11:00:00+03:00",
            "review_outcome": "accepted",
            "reviewer_independent": True,
        })
        with self.assertRaisesRegex(MeasurementWriteContractError, "Only measured"):
            self.build()

    def test_rejects_untrusted_or_unsupported_role_value(self):
        with self.assertRaisesRegex(MeasurementWriteContractError, "role"):
            self.build(authenticated_actor_role="admin\n")

    def test_digest_changes_when_rpc_payload_changes(self):
        first = self.build()
        self.record["value"] = 13
        second = self.build()
        self.assertNotEqual(first["p_payload_sha256"], second["p_payload_sha256"])


if __name__ == "__main__":
    unittest.main()
