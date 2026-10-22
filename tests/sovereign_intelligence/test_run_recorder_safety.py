from __future__ import annotations

import json

import pytest

from sovereign_intelligence.observability.run_models import IntelligenceRun
from sovereign_intelligence.observability.run_recorder import (
    MAX_EVENTS_PER_RUN,
    RunRecorder,
)


def test_recorder_redacts_sensitive_fields_and_common_secret_patterns(tmp_path):
    recorder = RunRecorder(str(tmp_path / "runs.jsonl"))
    run = IntelligenceRun(metadata={
        "OPENAI_API_KEY": "never-store-this",
        "note": "Authorization: Bearer abcdefghijklmnop secret follows",
        "diagnostic": "api_key=another-secret-value",
    })
    run.add_event("provider", "failed", {"access_token": "never-store-this-either"})
    recorder.record(run)

    text = (tmp_path / "runs.jsonl").read_text(encoding="utf-8")
    assert "never-store-this" not in text
    assert "another-secret-value" not in text
    assert "abcdefghijklmnop" not in text
    assert "never-store-this-either" not in text
    record = recorder.read_recent()[0]
    assert record["metadata"]["OPENAI_API_KEY"] == "[REDACTED]"
    assert record["events"][0]["data"]["access_token"] == "[REDACTED]"


def test_read_recent_rejects_invalid_limits(tmp_path):
    recorder = RunRecorder(str(tmp_path / "runs.jsonl"))
    for limit in (0, -1, True, 1001, 1.5):
        with pytest.raises(ValueError, match="limit"):
            recorder.read_recent(limit)


def test_recorder_rejects_too_many_events(tmp_path):
    recorder = RunRecorder(str(tmp_path / "runs.jsonl"))
    run = IntelligenceRun()
    run.events = [run.add_event("event", "ok") for _ in range(MAX_EVENTS_PER_RUN + 1)]
    with pytest.raises(ValueError, match="at most"):
        recorder.record(run)
    assert not (tmp_path / "runs.jsonl").exists()


def test_recorder_rejects_oversized_run_evidence(tmp_path):
    recorder = RunRecorder(str(tmp_path / "runs.jsonl"))
    run = IntelligenceRun(metadata={"large": "x" * 270_000})
    with pytest.raises(ValueError, match="262144-byte"):
        recorder.record(run)
    assert not (tmp_path / "runs.jsonl").exists()


def test_recent_reads_only_last_requested_records(tmp_path):
    recorder = RunRecorder(str(tmp_path / "runs.jsonl"))
    for index in range(4):
        recorder.record(IntelligenceRun(metadata={"index": index}))
    assert [item["metadata"]["index"] for item in recorder.read_recent(2)] == [2, 3]


def test_corrupt_recent_line_has_line_number_without_echoing_contents(tmp_path):
    path = tmp_path / "runs.jsonl"
    path.write_text('{"ok": true}\nSECRET_DO_NOT_ECHO\n', encoding="utf-8")
    recorder = RunRecorder(str(path))
    with pytest.raises(ValueError, match="line 2") as error:
        recorder.read_recent()
    assert "SECRET_DO_NOT_ECHO" not in str(error.value)
