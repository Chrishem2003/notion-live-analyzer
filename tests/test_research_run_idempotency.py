"""Tests for the shared persistent research-run idempotency ledger."""
from concurrent.futures import ProcessPoolExecutor
import pytest
import sqlite3

from modules.research_run_idempotency import (
    IdempotencyConflictError,
    RunIdempotencyLedger,
)


def _reserve_from_worker(database_path, run_id, payload):
    """Create an independent ledger connection in a worker process."""
    ledger = RunIdempotencyLedger(database_path)
    return ledger.reserve(run_id, payload)["action"]


def _reserve_or_conflict_from_worker(database_path, run_id, payload):
    """Return a conflict marker when concurrent payloads reuse one run ID."""
    ledger = RunIdempotencyLedger(database_path)
    try:
        return ledger.reserve(run_id, payload)["action"]
    except IdempotencyConflictError:
        return "conflict"


def test_reservation_serializes_duplicate_requests_and_reuses_completed_result(tmp_path):
    ledger = RunIdempotencyLedger(str(tmp_path / "shared" / "runs.sqlite3"))
    payload = {"run_name": "Synthetic run", "project": "project-1"}

    assert ledger.reserve("run-1", payload) == {"action": "reserved", "page_id": None}
    assert ledger.reserve("run-1", payload) == {"action": "in_progress", "page_id": None}

    ledger.mark_complete("run-1", "notion-page-1")
    assert ledger.reserve("run-1", payload) == {
        "action": "complete",
        "page_id": "notion-page-1",
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


def test_completed_reservation_survives_ledger_reconstruction(tmp_path):
    """A fresh ledger object must read the committed state from the same file."""
    path = str(tmp_path / "durable" / "runs.sqlite3")
    payload = {"run_name": "Synthetic recovery", "project": "demo-project"}

    first_process_view = RunIdempotencyLedger(path)
    assert first_process_view.reserve("run-reopen", payload) == {
        "action": "reserved",
        "page_id": None,
    }
    first_process_view.mark_complete("run-reopen", "notion-demo-page")

    restarted_process_view = RunIdempotencyLedger(path)
    assert restarted_process_view.reserve("run-reopen", payload) == {
        "action": "complete",
        "page_id": "notion-demo-page",
    }


def test_concurrent_processes_reserve_a_run_id_only_once(tmp_path):
    """Independent processes sharing one SQLite file cannot both reserve a run."""
    path = str(tmp_path / "concurrent" / "runs.sqlite3")
    payload = {"run_name": "Concurrent synthetic reservation"}

    with ProcessPoolExecutor(max_workers=2) as pool:
        actions = list(
            pool.map(
                _reserve_from_worker,
                [path, path],
                ["run-concurrent", "run-concurrent"],
                [payload, payload],
            )
        )

    assert actions.count("reserved") == 1
    assert actions.count("in_progress") == 1


def test_concurrent_different_payloads_cannot_claim_the_same_run_id(tmp_path):
    """A racing payload conflict must be rejected atomically across processes."""
    path = str(tmp_path / "conflicting" / "runs.sqlite3")
    payloads = [
        {"run_name": "First competing payload", "project": "demo-a"},
        {"run_name": "Second competing payload", "project": "demo-b"},
    ]

    with ProcessPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(
                _reserve_or_conflict_from_worker,
                [path, path],
                ["run-conflict-race", "run-conflict-race"],
                payloads,
            )
        )

    assert outcomes.count("reserved") == 1
    assert outcomes.count("conflict") == 1
