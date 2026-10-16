"""Tests for required workflow encryption configuration and storage encoding."""
import os
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet

from modules.workflow_storage import (
    WorkflowStorageConfigurationError,
    WorkflowStorageError,
    decode_storage_json,
    decrypt_storage_text,
    encode_storage_json,
    encrypt_storage_text,
    load_workflow_storage_key,
)


class WorkflowStorageTests(unittest.TestCase):
    def test_missing_key_fails_closed_with_explicit_empty_environment(self):
        with patch.dict(os.environ, {"WORKFLOW_RUNTIME_ENCRYPTION_KEY": Fernet.generate_key().decode()}):
            with self.assertRaises(WorkflowStorageConfigurationError):
                load_workflow_storage_key({}, {})

    def test_invalid_fernet_key_is_rejected(self):
        with self.assertRaises(WorkflowStorageConfigurationError):
            load_workflow_storage_key({}, {"WORKFLOW_RUNTIME_ENCRYPTION_KEY": "not-a-fernet-key"})

    def test_secret_store_precedes_environment(self):
        secret_key = Fernet.generate_key()
        environment_key = Fernet.generate_key()
        loaded = load_workflow_storage_key(
            {"WORKFLOW_RUNTIME_ENCRYPTION_KEY": secret_key.decode()},
            {"WORKFLOW_RUNTIME_ENCRYPTION_KEY": environment_key.decode()},
        )
        self.assertEqual(loaded, secret_key)

    def test_json_round_trip_is_encrypted_and_legacy_plaintext_remains_readable(self):
        key = Fernet.generate_key()
        payload = {"classification": "Synthetic/Test", "token": "not-a-real-secret"}
        encrypted = encode_storage_json(payload, key)
        self.assertTrue(encrypted.startswith("enc:v1:"))
        self.assertNotIn("not-a-real-secret", encrypted)
        self.assertEqual(decode_storage_json(encrypted, key), payload)
        self.assertEqual(decode_storage_json('{"legacy": true}', key), {"legacy": True})

    def test_encrypted_data_without_key_or_with_wrong_key_fails_closed(self):
        key = Fernet.generate_key()
        ciphertext = encrypt_storage_text("payload", key)
        with self.assertRaises(WorkflowStorageConfigurationError):
            decrypt_storage_text(ciphertext, None)
        with self.assertRaises(WorkflowStorageError):
            decrypt_storage_text(ciphertext, Fernet.generate_key())


if __name__ == "__main__":
    unittest.main()
