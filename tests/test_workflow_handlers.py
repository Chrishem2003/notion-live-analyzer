"""Tests for built-in deterministic workflow handlers."""
import unittest

from modules.workflow_contract import WorkflowContractError
from modules.workflow_handlers import data_quality_profile, default_handlers, numeric_summary, research_problem_triage


class WorkflowHandlerTests(unittest.TestCase):
    def test_numeric_summary_computes_sample_statistics(self):
        result = numeric_summary({"values": [1, 2, 3, 4]})
        self.assertEqual(result["n"], 4)
        self.assertEqual(result["mean"], 2.5)
        self.assertEqual(result["median"], 2.5)
        self.assertAlmostEqual(result["sample_standard_deviation"], 1.2909944487)

    def test_numeric_summary_rejects_nan_and_empty_input(self):
        with self.assertRaises(WorkflowContractError):
            numeric_summary({"values": [1, float("nan")]})
        with self.assertRaises(WorkflowContractError):
            numeric_summary({"values": []})

    def test_data_quality_profile_counts_missing_and_duplicate_rows(self):
        result = data_quality_profile({
            "rows": [
                {"id": "A", "value": 1},
                {"id": "A", "value": 1},
                {"id": "B", "value": None},
            ]
        })
        self.assertEqual(result["row_count"], 3)
        self.assertEqual(result["column_count"], 2)
        self.assertEqual(result["duplicate_row_count"], 1)
        self.assertEqual(result["missing_values_by_column"]["value"], 1)

    def test_data_quality_profile_handles_nested_unhashable_values(self):
        result = data_quality_profile({"rows": [{"x": [1, 2]}, {"x": [1, 2]}]})
        self.assertEqual(result["duplicate_row_count"], 1)

    def test_fasta_validator_is_in_the_explicit_handler_allow_list(self):
        handlers = default_handlers()
        self.assertIn("fasta_validate", handlers)
        result = handlers["fasta_validate"]({"fasta_text": ">demo\nACGT\n"})
        self.assertTrue(result["valid"])
        self.assertTrue(result["human_review_required"])

    def test_problem_triage_adds_domain_evidence_and_human_review(self):
        result = research_problem_triage({
            "problem": "Assess whether water quality data shows a safety concern",
            "context": "Field measurements",
        })
        self.assertTrue(result["human_review_required"])
        self.assertTrue(any("Qualified human review" in item for item in result["evidence_needed"]))
        self.assertGreaterEqual(len(result["acceptance_checks"]), 3)

    def test_problem_triage_rejects_vague_input(self):
        with self.assertRaises(WorkflowContractError):
            research_problem_triage({"problem": "help me"})


if __name__ == "__main__":
    unittest.main()
