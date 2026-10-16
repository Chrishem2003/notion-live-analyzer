"""Regression tests for the non-mutating workflow configuration preflight."""
import contextlib
import io
import os
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
from tools.check_workflow_configuration import main


class WorkflowConfigurationPreflightTests(unittest.TestCase):
    def test_missing_secrets_fail_without_disclosing_values(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(output):
            result = main()
        self.assertEqual(result, 1)
        self.assertIn("[FAIL] Operator password", output.getvalue())
        self.assertIn("[FAIL] Payload encryption key", output.getvalue())
        self.assertNotIn("WORKFLOW_EXECUTION_PASSWORD=", output.getvalue())
        self.assertNotIn("WORKFLOW_RUNTIME_ENCRYPTION_KEY=", output.getvalue())

    def test_valid_secrets_pass_and_are_never_printed(self):
        password = "synthetic-test-operator-secret-123456"
        key = Fernet.generate_key().decode("ascii")
        output = io.StringIO()
        with patch.dict(
            os.environ,
            {
                "WORKFLOW_EXECUTION_PASSWORD": password,
                "WORKFLOW_RUNTIME_ENCRYPTION_KEY": key,
                "WORKFLOW_RUNTIME_DB": ".streamlit/staging-test.sqlite3",
            },
            clear=True,
        ), contextlib.redirect_stdout(output):
            result = main()
        rendered = output.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("[PASS] Operator password", rendered)
        self.assertIn("[PASS] Payload encryption key", rendered)
        self.assertNotIn(password, rendered)
        self.assertNotIn(key, rendered)
        self.assertIn("staging-test.sqlite3", rendered)
        self.assertIn("does not test staging delivery", rendered)


    def test_invalid_values_fail_and_preflight_does_not_create_database(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tempdir:
            database = Path(tempdir) / "must-not-be-created.sqlite3"
            output = io.StringIO()
            with patch.dict(
                os.environ,
                {
                    "WORKFLOW_EXECUTION_PASSWORD": "short",
                    "WORKFLOW_RUNTIME_ENCRYPTION_KEY": "not-a-fernet-key",
                    "WORKFLOW_RUNTIME_DB": str(database),
                },
                clear=True,
            ), contextlib.redirect_stdout(output):
                result = main()
            self.assertEqual(result, 1)
            self.assertFalse(database.exists())
            self.assertIn("[FAIL] Operator password", output.getvalue())
            self.assertIn("[FAIL] Payload encryption key", output.getvalue())
            self.assertNotIn("not-a-fernet-key", output.getvalue())


if __name__ == "__main__":
    unittest.main()
