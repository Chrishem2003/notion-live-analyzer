"""Functional tests for the versioned keyed research-manifest fingerprint."""
import unittest

from modules.manifest_fingerprint import (
    ManifestFingerprintError,
    canonical_manifest_bytes,
    manifest_fingerprint,
    verify_manifest_fingerprint,
)


KEY_A = b"A" * 32
KEY_B = b"B" * 32
MANIFEST = {"run_id": "synthetic-run-001", "status": "succeeded", "input": {"b": 2, "a": 1}}


class ManifestFingerprintTests(unittest.TestCase):
    def test_mapping_key_order_does_not_change_fingerprint(self):
        left = {"run_id": "synthetic-run-001", "status": "succeeded", "input": {"b": 2, "a": 1}}
        right = {"input": {"a": 1, "b": 2}, "status": "succeeded", "run_id": "synthetic-run-001"}
        self.assertEqual(canonical_manifest_bytes(left), canonical_manifest_bytes(right))
        self.assertEqual(
            manifest_fingerprint(left, key=KEY_A, key_id="test-v1"),
            manifest_fingerprint(right, key=KEY_A, key_id="test-v1"),
        )

    def test_payload_change_changes_fingerprint(self):
        original = manifest_fingerprint(MANIFEST, key=KEY_A, key_id="test-v1")
        changed = manifest_fingerprint(
            {**MANIFEST, "status": "failed"}, key=KEY_A, key_id="test-v1"
        )
        self.assertNotEqual(original, changed)

    def test_different_keys_produce_different_fingerprints(self):
        self.assertNotEqual(
            manifest_fingerprint(MANIFEST, key=KEY_A, key_id="test-v1"),
            manifest_fingerprint(MANIFEST, key=KEY_B, key_id="test-v1"),
        )

    def test_key_id_is_versioned_and_bound_to_mac(self):
        first = manifest_fingerprint(MANIFEST, key=KEY_A, key_id="tenant-a-v1")
        second = manifest_fingerprint(MANIFEST, key=KEY_A, key_id="tenant-a-v2")
        self.assertTrue(first.startswith("br-hmac-sha256:v1:tenant-a-v1:"))
        self.assertNotEqual(first, second)

    def test_rejects_text_and_short_keys(self):
        for key in ("do-not-use-text-secrets", b"short"):
            with self.subTest(key_type=type(key).__name__):
                with self.assertRaisesRegex(ManifestFingerprintError, "at least 32 bytes"):
                    manifest_fingerprint(MANIFEST, key=key, key_id="test-v1")

    def test_rejects_invalid_key_ids(self):
        for key_id in ("", "tenant:one", "contains spaces", "x" * 65, "é"):
            with self.subTest(key_id=key_id):
                with self.assertRaisesRegex(ManifestFingerprintError, "key_id"):
                    manifest_fingerprint(MANIFEST, key=KEY_A, key_id=key_id)

    def test_rejects_non_finite_numbers(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ManifestFingerprintError, "non-finite"):
                    canonical_manifest_bytes({"nested": [value]})

    def test_rejects_non_json_values_and_non_string_keys(self):
        cases = (
            {"payload": b"raw-bytes"},
            {"payload": {1: "non-string-key"}},
            {"payload": {"nested": object()}},
        )
        for manifest in cases:
            with self.subTest(manifest_type=type(manifest["payload"]).__name__):
                with self.assertRaises(ManifestFingerprintError):
                    canonical_manifest_bytes(manifest)

    def test_verification_is_true_only_for_matching_manifest_and_key(self):
        fingerprint = manifest_fingerprint(MANIFEST, key=KEY_A, key_id="test-v1")
        self.assertTrue(
            verify_manifest_fingerprint(
                MANIFEST, fingerprint, key=KEY_A, key_id="test-v1"
            )
        )
        self.assertFalse(
            verify_manifest_fingerprint(
                {**MANIFEST, "status": "failed"},
                fingerprint,
                key=KEY_A,
                key_id="test-v1",
            )
        )
        self.assertFalse(
            verify_manifest_fingerprint(
                MANIFEST, fingerprint, key=KEY_B, key_id="test-v1"
            )
        )
        self.assertFalse(
            verify_manifest_fingerprint(
                MANIFEST, "not-ascii-snowman-☃", key=KEY_A, key_id="test-v1"
            )
        )


if __name__ == "__main__":
    unittest.main()
