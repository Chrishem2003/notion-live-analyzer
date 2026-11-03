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

def test_run_id_mutations_use_the_same_canonical_identifier(tmp_path):
    """Reservation and state transitions must address the same normalized row."""
    ledger = RunIdempotencyLedger(str(tmp_path / "normalized-id" / "runs.sqlite3"))
    payload = {"run_name": "Synthetic run-ID normalization"}

    assert ledger.reserve("  run-normalized  ", payload) == {
        "action": "reserved",
        "page_id": None,
    }
    ledger.mark_ambiguous("  run-normalized  ")
    assert ledger.reserve("run-normalized", payload)["action"] == "recover"

    ledger.mark_failed("  run-normalized  ")
    assert ledger.reserve("run-normalized", payload) == {
        "action": "reserved",
        "page_id": None,
    }
    ledger.mark_complete("  run-normalized  ", "notion-synthetic-page")
    assert ledger.reserve("run-normalized", payload) == {
        "action": "complete",
        "page_id": "notion-synthetic-page",
    }


@pytest.mark.parametrize("transition", ["mark_ambiguous", "mark_failed"])
def test_ledger_state_transition_rejects_unreserved_run_id(tmp_path, transition):
    """Recovery/failure transitions must not silently succeed without a ledger row."""
    ledger = RunIdempotencyLedger(str(tmp_path / "unreserved" / "runs.sqlite3"))

    with pytest.raises(RuntimeError, match="unreserved run_id"):
        getattr(ledger, transition)("missing-run")

    with sqlite3.connect(ledger.database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM research_run_idempotency"
        ).fetchone()[0]
    assert count == 0


@pytest.mark.parametrize("transition", ["mark_ambiguous", "mark_failed"])
def test_late_transition_cannot_downgrade_completed_run(tmp_path, transition):
    """A late worker result must not erase an already completed ledger entry."""
    ledger = RunIdempotencyLedger(str(tmp_path / "completed" / "runs.sqlite3"))
    payload = {"run_name": "Immutable completed result"}
    ledger.reserve("run-complete", payload)
    ledger.mark_complete("run-complete", "notion-page-original")

    # A stale worker may report a timeout/failure after another worker completed.
    getattr(ledger, transition)("run-complete")

    with sqlite3.connect(ledger.database_path) as connection:
        row = connection.execute(
            "SELECT state, notion_page_id FROM research_run_idempotency WHERE run_id=?",
            ("run-complete",),
        ).fetchone()
    assert row == ("complete", "notion-page-original")
    assert ledger.reserve("run-complete", payload) == {
        "action": "complete",
        "page_id": "notion-page-original",
    }


def test_completed_run_page_id_is_immutable_but_same_result_is_idempotent(tmp_path):
    """Repeated completion may confirm the same page, never replace it."""
    ledger = RunIdempotencyLedger(str(tmp_path / "page-id" / "runs.sqlite3"))
    payload = {"run_name": "Page identity protection"}
    ledger.reserve("run-page-id", payload)
    ledger.mark_complete("run-page-id", "notion-page-original")

    # A duplicate completion for the same external page is safe and idempotent.
    ledger.mark_complete("run-page-id", "notion-page-original")
    with pytest.raises(RuntimeError, match="Cannot replace the Notion page ID"):
        ledger.mark_complete("run-page-id", "notion-page-different")

    with sqlite3.connect(ledger.database_path) as connection:
        row = connection.execute(
            "SELECT state, notion_page_id FROM research_run_idempotency WHERE run_id=?",
            ("run-page-id",),
        ).fetchone()
    assert row == ("complete", "notion-page-original")


def test_mark_complete_rejects_unreserved_run_id_without_creating_row(tmp_path):
    """Completion cannot manufacture a ledger row without a prior reservation."""
    ledger = RunIdempotencyLedger(str(tmp_path / "missing-reservation" / "runs.sqlite3"))

    with pytest.raises(RuntimeError, match="Cannot complete an unreserved run_id"):
        ledger.mark_complete("missing-run", "notion-page-should-not-exist")

    with sqlite3.connect(ledger.database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM research_run_idempotency"
        ).fetchone()[0]
    assert count == 0

@pytest.mark.parametrize("page_id", [None, "", "   ", " notion-page-padded ", 42])
def test_mark_complete_rejects_invalid_page_id_without_changing_reservation(tmp_path, page_id):
    """A malformed external page ID must not create a false completed ledger result."""
    ledger = RunIdempotencyLedger(str(tmp_path / "invalid-page-id" / "runs.sqlite3"))
    ledger.reserve("run-invalid-page-id", {"run_name": "Page ID validation"})

    with pytest.raises(RuntimeError, match="page_id must be a non-empty, unpadded string"):
        ledger.mark_complete("run-invalid-page-id", page_id)

    with sqlite3.connect(ledger.database_path) as connection:
        row = connection.execute(
            "SELECT state, notion_page_id FROM research_run_idempotency WHERE run_id=?",
            ("run-invalid-page-id",),
        ).fetchone()
    assert row == ("pending", None)


def test_concurrent_reservations_share_one_pending_ledger_row(tmp_path):
    """Independent ledger instances must serialize concurrent same-payload reservations."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    path = str(tmp_path / "concurrent-same-payload" / "runs.sqlite3")
    worker_count = 6
    ledgers = [RunIdempotencyLedger(path) for _ in range(worker_count)]
    barrier = Barrier(worker_count)
    payload = {"run_name": "Concurrent synthetic reservation"}

    def reserve(ledger):
        barrier.wait(timeout=10)
        return ledger.reserve("run-concurrent-same", payload)["action"]

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        actions = [future.result(timeout=20) for future in [
            executor.submit(reserve, ledger) for ledger in ledgers
        ]]

    assert actions.count("reserved") == 1
    assert actions.count("in_progress") == worker_count - 1

    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            "SELECT run_id, payload_hash, state, notion_page_id "
            "FROM research_run_idempotency"
        ).fetchall()
    assert rows == [
        (
            "run-concurrent-same",
            RunIdempotencyLedger.fingerprint(payload),
            "pending",
            None,
        )
    ]


def test_concurrent_conflicting_payload_reservations_have_one_winner(tmp_path):
    """Concurrent conflicting payloads must not create competing reservations."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    path = str(tmp_path / "concurrent-conflict" / "runs.sqlite3")
    worker_count = 6
    ledgers = [RunIdempotencyLedger(path) for _ in range(worker_count)]
    barrier = Barrier(worker_count)
    payloads = [{"run_name": f"Concurrent payload {index}"} for index in range(worker_count)]

    def reserve(index):
        barrier.wait(timeout=10)
        try:
            result = ledgers[index].reserve("run-concurrent-conflict", payloads[index])
            return result["action"], payloads[index]
        except IdempotencyConflictError:
            return "conflict", payloads[index]

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        outcomes = [future.result(timeout=20) for future in [
            executor.submit(reserve, index) for index in range(worker_count)
        ]]

    actions = [action for action, _ in outcomes]
    assert actions.count("reserved") == 1
    assert actions.count("conflict") == worker_count - 1

    winner_payload = next(payload for action, payload in outcomes if action == "reserved")
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            "SELECT run_id, payload_hash, state, notion_page_id "
            "FROM research_run_idempotency"
        ).fetchall()
    assert rows == [
        (
            "run-concurrent-conflict",
            RunIdempotencyLedger.fingerprint(winner_payload),
            "pending",
            None,
        )
    ]
