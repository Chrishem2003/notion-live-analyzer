import sqlite3

import pytest

from nema_agora.evidence_case import EvidenceReference, build_evidence_case
from nema_agora.evidence_case_store import EvidenceCaseStore


def _case():
    return build_evidence_case(
        case_id="case-1",
        observation={"site": "pilot-A", "value": "synthetic"},
        evidence=[
            EvidenceReference(
                "ev-1", "note", "synthetic-source",
                "2026-01-01T00:00:00Z", "a" * 64
            )
        ],
        created_at="2026-01-01T00:00:00Z",
    )


def test_case_store_persists_and_is_append_only(tmp_path):
    store = EvidenceCaseStore(tmp_path / "cases.db")
    case = _case()
    store.append(case)
    assert store.count() == 1
    assert store.get("case-1")["state"] == "READY_FOR_REVIEW"

    with pytest.raises(sqlite3.IntegrityError, match="APPEND_ONLY"):
        with store._connect() as conn:
            conn.execute("UPDATE evidence_cases SET state='REVIEWED' WHERE case_id='case-1'")


def test_transition_events_reconstruct_effective_case_and_are_append_only(tmp_path):
    store = EvidenceCaseStore(tmp_path / "cases.db")
    case = _case()
    store.append(case)

    reviewed = {
        "decision": "ACKNOWLEDGED",
        "notes": "human review",
        "case_provenance_fingerprint": case.provenance_fingerprint,
    }
    first = store.append_event(
        case_id=case.case_id, event_type="HUMAN_REVIEW",
        state="REVIEWED", actor_id="reviewer-1", role="reviewer",
        event=reviewed, created_at="2026-01-01T01:00:00Z",
    )
    assert store.load_case(case.case_id).state == "REVIEWED"
    assert store.load_case(case.case_id).review.reviewer_id == "reviewer-1"

    second = store.append_event(
        case_id=case.case_id, event_type="EXPORT_AUTHORISED",
        state="EXPORTED", actor_id="reviewer-1", role="reviewer",
        event={
            "official_submission": False,
            "execution_gate": "CLOSED",
            "case_provenance_fingerprint": case.provenance_fingerprint,
        },
        created_at="2026-01-01T02:00:00Z",
    )
    assert (first, second) == (1, 2)
    assert store.load_case(case.case_id).state == "EXPORTED"
    assert [e["event_type"] for e in store.list_events(case.case_id)] == [
        "HUMAN_REVIEW", "EXPORT_AUTHORISED"
    ]
    with pytest.raises(sqlite3.IntegrityError, match="APPEND_ONLY"):
        with store._connect() as conn:
            conn.execute("DELETE FROM evidence_case_events WHERE event_id=1")


def test_events_require_existing_case_and_matching_provenance(tmp_path):
    store = EvidenceCaseStore(tmp_path / "cases.db")
    with pytest.raises(KeyError):
        store.append_event(
            case_id="missing", event_type="HUMAN_REVIEW", state="REVIEWED",
            actor_id="r", role="reviewer",
            event={"case_provenance_fingerprint": "x"}, created_at="2026-01-01T01:00:00Z",
        )

    case = _case()
    store.append(case)
    with pytest.raises(ValueError, match="provenance"):
        store.append_event(
            case_id=case.case_id, event_type="HUMAN_REVIEW", state="REVIEWED",
            actor_id="r", role="reviewer",
            event={"decision": "ACKNOWLEDGED", "case_provenance_fingerprint": "wrong"},
            created_at="2026-01-01T01:00:00Z",
        )


def test_invalid_stored_case_is_rejected(tmp_path):
    store = EvidenceCaseStore(tmp_path / "cases.db")
    case = _case()
    store.append(case)
    with store._connect() as conn:
        conn.execute("DROP TRIGGER evidence_cases_no_update")
        conn.execute(
            "UPDATE evidence_cases SET case_json='{}' WHERE case_id='case-1'"
        )
    with pytest.raises(ValueError, match="integrity"):
        store.load_case("case-1")
