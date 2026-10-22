"""Tests for bounded GitHub webhook body handling."""
import asyncio

import pytest
from fastapi import HTTPException

from api_server import MAX_GITHUB_WEBHOOK_BYTES, read_limited_webhook_body


class FakeRequest:
    def __init__(self, chunks):
        self._chunks = chunks

    async def stream(self):
        for chunk in self._chunks:
            yield chunk


def test_webhook_body_within_limit_is_returned_unchanged():
    result = asyncio.run(read_limited_webhook_body(FakeRequest([b'{"ok":', b'true}'])))
    assert result == b'{"ok":true}'


def test_webhook_body_over_limit_is_rejected_while_streaming():
    request = FakeRequest([b"x" * (MAX_GITHUB_WEBHOOK_BYTES - 4), b"12345"])
    with pytest.raises(HTTPException) as error:
        asyncio.run(read_limited_webhook_body(request))
    assert error.value.status_code == 413
    assert "1 MiB" in error.value.detail


def test_webhook_limit_can_be_lowered_for_boundary_tests():
    result = asyncio.run(read_limited_webhook_body(FakeRequest([b"1234"]), max_bytes=4))
    assert result == b"1234"
