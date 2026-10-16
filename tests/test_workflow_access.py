"""Security tests for the workflow execution operator gate."""
import unittest
from unittest.mock import patch

from modules.workflow_access import (
    WorkflowAccessConfigurationError,
    is_workflow_session_valid,
    load_workflow_password,
    verify_workflow_password,
)


class WorkflowAccessTests(unittest.TestCase):
    def test_missing_or_short_secret_fails_closed(self):
        for value in (None, "", "short"):
            with self.subTest(value=value):
                with self.assertRaises(WorkflowAccessConfigurationError):
                    load_workflow_password(
                        {}, {"WORKFLOW_EXECUTION_PASSWORD": value} if value is not None else {}
                    )

    def test_empty_explicit_environment_does_not_fall_back_to_process_environment(self):
        # Configuration passed by the caller must be deterministic and isolated.
        with patch.dict(
            "os.environ", {"WORKFLOW_EXECUTION_PASSWORD": "ambient-secret-that-is-long-enough"}
        ):
            with self.assertRaises(WorkflowAccessConfigurationError):
                load_workflow_password({}, {})

    def test_whitespace_only_secret_is_rejected(self):
        with self.assertRaises(WorkflowAccessConfigurationError):
            load_workflow_password({}, {"WORKFLOW_EXECUTION_PASSWORD": " " * 32})

    def test_secret_can_be_loaded_from_deployment_secret_store(self):
        secret = "a-unique-long-operator-secret-123456"
        self.assertEqual(load_workflow_password({"WORKFLOW_EXECUTION_PASSWORD": secret}, {}), secret)

    def test_secret_store_precedes_environment_and_preserves_exact_secret(self):
        secret = "  an-intentionally-exact-secret-123456  "
        loaded = load_workflow_password(
            {"WORKFLOW_EXECUTION_PASSWORD": secret},
            {"WORKFLOW_EXECUTION_PASSWORD": "environment-secret-that-is-long-enough"},
        )
        self.assertEqual(loaded, secret)

    def test_password_comparison_accepts_only_exact_secret(self):
        secret = "a-unique-long-operator-secret-123456"
        self.assertTrue(verify_workflow_password(secret, secret))
        self.assertFalse(verify_workflow_password(secret + "x", secret))
        self.assertFalse(verify_workflow_password(None, secret))
        self.assertFalse(verify_workflow_password("", secret))

    def test_session_expires_after_fifteen_minutes(self):
        self.assertTrue(is_workflow_session_valid(True, 1000.0, now=1000.0 + 899))
        self.assertFalse(is_workflow_session_valid(True, 1000.0, now=1000.0 + 900))
        self.assertFalse(is_workflow_session_valid(True, 1000.0, now=999.0))
        self.assertFalse(is_workflow_session_valid(False, 1000.0, now=1001.0))
        self.assertFalse(is_workflow_session_valid(True, "1000", now=1001.0))

    def test_session_rejects_boolean_nonfinite_and_malformed_clock_values(self):
        for issued_at, now in (
            (True, 1001.0),
            (float("nan"), 1001.0),
            (float("inf"), 1001.0),
            (1000.0, True),
            (1000.0, float("nan")),
            (1000.0, float("inf")),
        ):
            with self.subTest(issued_at=issued_at, now=now):
                self.assertFalse(is_workflow_session_valid(True, issued_at, now=now))

    def test_session_rejects_invalid_ttl_types(self):
        for ttl in (True, 0, -1, 1.5):
            with self.subTest(ttl=ttl):
                self.assertFalse(is_workflow_session_valid(True, 1000.0, now=1001.0, ttl_seconds=ttl))


    def test_workflow_console_warns_and_gates_synthetic_only_data(self):
        from pathlib import Path
        import ast

        page_path = Path("pages/19_Workflow_Execution_Center.py")
        source = page_path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(page_path))
        self.assertIn("SYNTHETIC / TEST DATA ONLY", source)
        self.assertIn("without database-level encryption", source)
        self.assertIn("if not synthetic_only_confirmed", source)
        self.assertIn("Confirm synthetic/demo-only input before submitting a workflow.", source)


if __name__ == "__main__":
    unittest.main()
