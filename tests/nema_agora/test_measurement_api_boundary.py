from __future__ import annotations

import hashlib
import unittest

from nema_agora.measurement_api_boundary import (
    MeasurementAuthorizationError,
    prepare_authenticated_measurement_submission,
)
from nema_agora.measurement_write_contract import MeasurementWriteContractError


class AuthenticatedMeasurementBoundaryTests(unittest.TestCase):
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
        self.principal = {"authenticated": True, "subject": "user-123", "role": "submitter"}

    def prepare(self, **overrides):
        args = dict(
            principal=self.principal,
            record=self.record,
            indicator=self.indicator,
            evidence_bytes=self.artifact,
            verified_evidence_object={
                "bucket": "nema-evidence",
                "object_key": f"sha256/{hashlib.sha256(self.artifact).hexdigest()[:2]}/{hashlib.sha256(self.artifact).hexdigest()}",
                "sha256": hashlib.sha256(self.artifact).hexdigest(),
            },
            measurement_id="measurement-001",
            idempotency_key="submission-001",
        )
        args.update(overrides)
        return prepare_authenticated_measurement_submission(**args)

    def test_actor_identity_comes_from_principal_not_record(self):
        self.record["actor_id"] = "attacker"
        self.record["actor_role"] = "admin"
        result = self.prepare()
        self.assertEqual(result["p_actor_id"], "user-123")
        self.assertEqual(result["p_actor_role"], "submitter")

    def test_rejects_unverified_principal(self):
        with self.assertRaises(MeasurementAuthorizationError):
            self.prepare(principal={"authenticated": False, "subject": "user-123", "role": "admin"})

    def test_rejects_role_not_allowed_to_submit(self):
        with self.assertRaises(MeasurementAuthorizationError):
            self.prepare(principal={"authenticated": True, "subject": "user-123", "role": "viewer"})

    def test_rejects_indicator_definition_mismatch(self):
        with self.assertRaisesRegex(MeasurementAuthorizationError, "does not match"):
            self.prepare(indicator={"id": "other-indicator", "unit": "count", "calculation": "Count records"})

    def test_rejects_missing_reporting_timezone_and_definition_version(self):
        self.record.pop("reporting_timezone")
        with self.assertRaises(MeasurementWriteContractError):
            self.prepare()
        self.record["reporting_timezone"] = "Africa/Kampala"
        self.record.pop("definition_version")
        with self.assertRaises(MeasurementWriteContractError):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
