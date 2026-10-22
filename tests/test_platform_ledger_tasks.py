from __future__ import annotations

import pytest

from modules.platform_ledger_tasks import _execute


class HashOnlyLedger:
    @staticmethod
    def request_hash(payload):
        return "synthetic-hash"


def test_synthetic_handler_does_not_echo_payload():
    result = _execute(
        "platform.synthetic.validate",
        {"private_note": "must not be echoed"},
        HashOnlyLedger(),
    )
    assert result == {
        "validated": True,
        "mode": "synthetic",
        "payload_sha256": "synthetic-hash",
    }
    assert "private_note" not in str(result)


def test_unregistered_job_types_are_rejected():
    with pytest.raises(ValueError, match="unsupported_job_type"):
        _execute("notion.write_real_record", {"x": 1}, HashOnlyLedger())
