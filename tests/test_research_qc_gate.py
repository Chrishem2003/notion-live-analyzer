"""Regression tests for fail-closed research provenance and QC gates."""
import unittest

from modules.research_qc_gate import (
    QC_ANOMALOUS,
    QC_PENDING,
    QC_VERIFIED,
    evaluate_research_gate,
)


def complete_record(**overrides):
    record = {
        "Record Classification": "Synthetic/Test",
        "Measurement Unit": "mg/L",
        "Protocol": ["protocol-page-id"],
        "Protocol ID/Version": "DEMO-PROT-001 v1.0-demo",
        "Raw Source Reference": "synthetic://fixture/raw-001",
        "Source Dataset Version": "fixture-v1",
        "Analysis Status.": QC_PENDING,
        "QC Reviewer": "reviewer-test-01",
        "QC Review Date": "2026-10-17",
        "QC Evidence": ["synthetic://fixture/qc-check-001"],
    }
    record.update(overrides)
    return record


class ResearchQCGateTests(unittest.TestCase):
    def test_complete_pending_record_can_be_presented_for_human_qc_review(self):
        result = evaluate_research_gate(complete_record(), "approve_qc")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["decision"], "ALLOW")
        self.assertTrue(result["requires_human_review"])

    def test_missing_units_protocol_and_source_block_qc_approval(self):
        result = evaluate_research_gate(
            complete_record(**{
                "Measurement Unit": "",
                "Protocol": [],
                "Protocol ID/Version": None,
                "Raw Source Reference": "",
                "Source Dataset Version": "",
            }),
            "approve_qc",
        )
        self.assertFalse(result["allowed"])
        joined = " ".join(result["blockers"])
        for field in ("Measurement Unit", "Protocol", "Protocol ID/Version",
                      "Raw Source Reference", "Source Dataset Version"):
            self.assertIn(field, joined)

    def test_missing_human_review_evidence_blocks_qc_approval(self):
        result = evaluate_research_gate(
            complete_record(**{"QC Reviewer": "", "QC Review Date": None, "QC Evidence": []}),
            "approve_qc",
        )
        self.assertFalse(result["allowed"])
        self.assertTrue(any("QC Reviewer" in item for item in result["blockers"]))
        self.assertTrue(any("QC Review Date" in item for item in result["blockers"]))
        self.assertTrue(any("QC Evidence" in item for item in result["blockers"]))

    def test_anomalous_record_cannot_be_reported_or_closed(self):
        for action in ("report", "close"):
            result = evaluate_research_gate(complete_record(**{"Analysis Status.": QC_ANOMALOUS}), action)
            self.assertFalse(result["allowed"])
            self.assertTrue(any("Anomalous QC" in item for item in result["blockers"]))

    def test_pending_qc_cannot_be_reported_or_closed(self):
        for action in ("report", "close"):
            result = evaluate_research_gate(complete_record(**{"Analysis Status.": QC_PENDING}), action)
            self.assertFalse(result["allowed"])
            self.assertTrue(any("QC must be Verified" in item for item in result["blockers"]))

    def test_verified_status_without_review_evidence_does_not_allow_release(self):
        result = evaluate_research_gate(
            complete_record(**{"Analysis Status.": QC_VERIFIED, "QC Evidence": []}),
            "report",
        )
        self.assertFalse(result["allowed"])
        self.assertTrue(any("QC Evidence" in item for item in result["blockers"]))

    def test_valid_verified_record_can_pass_report_gate(self):
        result = evaluate_research_gate(complete_record(**{"Analysis Status.": QC_VERIFIED}), "report")
        self.assertTrue(result["allowed"])

    def test_unclassified_record_is_blocked(self):
        result = evaluate_research_gate(complete_record(**{"Record Classification": "Unclassified"}), "approve_qc")
        self.assertFalse(result["allowed"])
        self.assertTrue(any("Record Classification" in item for item in result["blockers"]))

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_research_gate(complete_record(), "publish_everything")


if __name__ == "__main__":
    unittest.main()
