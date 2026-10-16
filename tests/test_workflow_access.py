"""Security tests for the workflow execution operator gate."""
import unittest

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
                    load_workflow_password({}, {"WORKFLOW_EXECUTION_PASSWORD": value} if value is not None else {})

    def test_secret_can_be_loaded_from_deployment_secret_store(self):
        secret = "a-unique-long-operator-secret-123456"
        self.assertEqual(load_workflow_password({"WORKFLOW_EXECUTION_PASSWORD": secret}, {}), secret)

    def test_password_comparison_accepts_only_exact_secret(self):
        secret = "a-unique-long-operator-secret-123456"
        self.assertTrue(verify_workflow_password(secret, secret))
        self.assertFalse(verify_workflow_password(secret + "x", secret))
        self.assertFalse(verify_workflow_password(None, secret))

    def test_session_expires_after_fifteen_minutes(self):
        self.assertTrue(is_workflow_session_valid(True, 1000.0, now=1000.0 + 899))
        self.assertFalse(is_workflow_session_valid(True, 1000.0, now=1000.0 + 900))
        self.assertFalse(is_workflow_session_valid(True, 1000.0, now=999.0))
        self.assertFalse(is_workflow_session_valid(False, 1000.0, now=1001.0))
        self.assertFalse(is_workflow_session_valid(True, "1000", now=1001.0))


if __name__ == "__main__":
    unittest.main()
