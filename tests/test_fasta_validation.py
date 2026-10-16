"""Regression tests for deterministic FASTA screening."""
import unittest

from modules.workflow_contract import WorkflowContractError
from modules.fasta_validation import validate_fasta


class FastaValidationTests(unittest.TestCase):
    def test_multiline_nucleotide_record_reports_length_and_gc(self):
        result = validate_fasta({"fasta_text": ">sample-1 training fixture\nACGT\nNN\n"})
        self.assertTrue(result["valid"])
        self.assertEqual(result["record_count"], 1)
        self.assertEqual(result["total_sequence_length"], 6)
        record = result["records"][0]
        self.assertEqual(record["sequence_length"], 6)
        self.assertEqual(record["sequence_type_screen"], "nucleic_acid")
        self.assertEqual(record["gc_percent_of_canonical_nucleic_bases"], 50.0)
        self.assertEqual(record["ambiguous_symbol_count"], 2)

    def test_protein_sequence_is_classified_without_gc_claim(self):
        result = validate_fasta({"fasta_text": ">protein-1\nMKWVTFISLL\n"})
        self.assertTrue(result["valid"])
        self.assertEqual(result["records"][0]["sequence_type_screen"], "protein")
        self.assertIsNone(result["records"][0]["gc_percent_of_canonical_nucleic_bases"])

    def test_sequence_before_first_header_is_rejected(self):
        with self.assertRaisesRegex(WorkflowContractError, "before the first FASTA header"):
            validate_fasta({"fasta_text": "ACGT\n>sample-1\nACGT"})

    def test_duplicate_record_ids_fail_validation(self):
        result = validate_fasta({"fasta_text": ">same desc one\nACGT\n>same desc two\nTGCA\n"})
        self.assertFalse(result["valid"])
        self.assertTrue(any("Duplicate record IDs" in error for error in result["errors"]))
        self.assertTrue(all(not record["valid_record"] for record in result["records"]))

    def test_unsupported_symbols_fail_validation(self):
        result = validate_fasta({"fasta_text": ">bad\nACGT123\n"})
        self.assertFalse(result["valid"])
        self.assertIn("invalid_or_unsupported", result["records"][0]["sequence_type_screen"])
        self.assertTrue(any("Unsupported symbols" in error for error in result["errors"]))

    def test_empty_sequence_is_reported_not_silently_accepted(self):
        result = validate_fasta({"fasta_text": ">empty\n>good\nACGT\n"})
        self.assertFalse(result["valid"])
        self.assertEqual(result["records"][0]["sequence_length"], 0)

    def test_empty_input_and_oversized_input_are_rejected(self):
        with self.assertRaises(WorkflowContractError):
            validate_fasta({"fasta_text": "   "})
        with self.assertRaisesRegex(WorkflowContractError, "byte limit"):
            validate_fasta({"fasta_text": ">seq\n" + "A" * 1_000_001})

    def test_output_discloses_that_sequence_is_not_persisted(self):
        result = validate_fasta({"fasta_text": ">demo\nACGT\n"})
        self.assertTrue(any("does not persist" in note for note in result["limitations"]))
        self.assertTrue(result["human_review_required"])


if __name__ == "__main__":
    unittest.main()
