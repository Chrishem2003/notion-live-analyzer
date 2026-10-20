"""Tests for the shared persistent research-run idempotency ledger."""
import pytest
import sqlite3

from modules.research_run_idempotency import (
    IdempotencyConflictError,
    RunIdempotencyLedger,
)


def test_reservation_serializes_duplicate_requests_and_reuses_completed_result(tmp_path):
    ledger = RunIdempotencyLedger(str(tmp_path / "shared" / "runs.sqlite3"))
    payload = {"run_name": "Synthetic run", "project": "project-1"}

    assert ledger.reserve("run-1", payload) == {"action": "reserved", "page_id": None}
    assert ledger.reserve("run-1", payload) == {"action": "in_progress", "page_id": None}

    ledger.mark_complete("run-1", "notion-page-1")
    assert ledger.reserve("run-1", payload) == {
        "action": "complete", "page_id": "notion-page-1"
    }


def test_same_run_id_with_different_payload_is_rejected(tmp_path):
    ledger = RunIdempotencyLedger(str(tmp_path / "runs.sqlite3"))
    ledger.reserve("run-2", {"run_name": "First"})
    with pytest.raises(IdempotencyConflictError, match="different payload"):
        ledger.reserve("run-2", {"run_name": "Changed"})


def test_ambiguous_and_failed_runs_have_explicit_recovery_states(tmp_path):
    ledger = RunIdempotencyLedger(str(tmp_path / "runs.sqlite3"))
    payload = {"run_name": "Retryable"}
    ledger.reserve("run-3", payload)
    ledger.mark_ambiguous("run-3")
    assert ledger.reserve("run-3", payload)["action"] == "recover"

    ledger.mark_failed("run-3")
    assert ledger.reserve("run-3", payload)["action"] == "reserved"


def test_requires_persistent_database_path():
    with pytest.raises(ValueError, match="persistent idempotency"):
        RunIdempotencyLedger("")


def test_stale_pending_reservation_moves_to_recovery_state(tmp_path):
    path = str(tmp_path / "runs.sqlite3")
    ledger = RunIdempotencyLedger(path)
    payload = {"run_name": "Worker-crash simulation"}
    ledger.reserve("run-stale", payload)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE research_run_idempotency "
            "SET updated_at=datetime('now', '-10 minutes') WHERE run_id=?",
            ("run-stale",),
        )
    assert ledger.reserve("run-stale", payload)["action"] == "recover"
