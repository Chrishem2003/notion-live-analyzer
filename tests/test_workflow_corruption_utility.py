"""Safety tests for the repository corruption-repair utility."""
from __future__ import annotations

import contextlib
import io
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.fix_corruption import main


class CorruptionUtilitySafetyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.source = self.root / "sample.py"
        self.original = b"value  42\r\n"
        self.source.write_bytes(self.original)

    def tearDown(self):
        self.tempdir.cleanup()

    def invoke(self, *args):
        output = io.StringIO()
        with patch.object(sys, "argv", ["fix_corruption.py", *map(str, args)]):
            with contextlib.redirect_stdout(output):
                result = main()
        return result, output.getvalue()

    def test_dry_run_never_writes_source_or_backup(self):
        result, output = self.invoke(self.source)
        self.assertEqual(result, 0)
        self.assertIn("WOULD FIX", output)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertFalse(self.source.with_name(self.source.name + ".bak").exists())

    def test_apply_creates_exact_private_backup_and_preserves_line_endings_and_mode(self):
        if os.name == "posix":
            self.source.chmod(0o640)
        result, output = self.invoke("--apply", self.source)
        backup = self.source.with_name(self.source.name + ".bak")
        self.assertEqual(result, 0)
        self.assertIn("FIXED", output)
        self.assertEqual(self.source.read_bytes(), b"value + 42\r\n")
        self.assertEqual(backup.read_bytes(), self.original)
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(self.source.stat().st_mode), 0o640)

    def test_existing_backup_prevents_source_or_backup_overwrite(self):
        backup = self.source.with_name(self.source.name + ".bak")
        backup.write_bytes(b"preserve existing backup")
        result, output = self.invoke("--apply", self.source)
        self.assertEqual(result, 1)
        self.assertIn("backup already exists", output)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(backup.read_bytes(), b"preserve existing backup")

    def test_invalid_utf8_is_skipped_without_replacement_write(self):
        original = b"value  42\n\xff\n"
        self.source.write_bytes(original)
        result, output = self.invoke("--apply", self.source)
        backup = self.source.with_name(self.source.name + ".bak")
        self.assertEqual(result, 1)
        self.assertIn("valid UTF-8", output)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertFalse(backup.exists())

    def test_symlink_is_skipped_without_modifying_target(self):
        target = self.root / "target.py"
        target.write_bytes(self.original)
        link = self.root / "linked.py"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable on this runner")
        result, output = self.invoke("--apply", link)
        self.assertEqual(result, 1)
        self.assertIn("symbolic link", output)
        self.assertTrue(link.is_symlink())
        self.assertEqual(target.read_bytes(), self.original)
        self.assertFalse(link.with_name(link.name + ".bak").exists())

    def test_hard_link_is_skipped_without_replacing_either_name(self):
        alias = self.root / "alias.py"
        try:
            os.link(self.source, alias)
        except (OSError, NotImplementedError):
            self.skipTest("hard links are unavailable on this runner")
        result, output = self.invoke("--apply", self.source)
        self.assertEqual(result, 1)
        self.assertIn("hard-linked", output)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(alias.read_bytes(), self.original)
        self.assertFalse(self.source.with_name(self.source.name + ".bak").exists())

    def test_atomic_replace_failure_keeps_original_and_recovery_backup(self):
        with patch("tools.fix_corruption.os.replace", side_effect=OSError("synthetic replace failure")):
            result, output = self.invoke("--apply", self.source)
        backup = self.source.with_name(self.source.name + ".bak")
        self.assertEqual(result, 1)
        self.assertIn("backup retained", output)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(backup.read_bytes(), self.original)
        self.assertEqual(list(self.root.glob(".fix-corruption-*.tmp")), [])

    def test_paths_are_json_quoted_to_prevent_log_line_injection(self):
        unusual = self.root / "line\n[PASS] forged\x1b.py"
        unusual.write_bytes(b"value  42\n")
        result, output = self.invoke(unusual)
        self.assertEqual(result, 0)
        self.assertNotIn("\x1b", output)
        self.assertIn(r"\n[PASS] forged\u001b.py", output)
        self.assertEqual(len([line for line in output.splitlines() if line]), 3)
        self.assertEqual(unusual.read_bytes(), b"value  42\n")


if __name__ == "__main__":
    unittest.main()
