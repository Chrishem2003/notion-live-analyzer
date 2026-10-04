import sqlite3

import pytest

from nema_agora.evidence_case import EvidenceReference, build_evidence_case
from nema_agora.evidence_case_store import EvidenceCaseStore


def _case():
    return build_evidence_case(
        case_id="case-1",
        observation={"site": "pilot-A", "value": "synthetic"},
        evidence=[
            EvidenceReference("ev-1", "note", "synthetic-source", "2026-01-01T00:00:00Z", "a" * 64)
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


def test_transition_events_are_append_only_and_ordered(tmp_path):
    store = EvidenceCaseStore(tmp_path / "cases.db")
    case = _case()
    store.append(case)
    first = store.append_event(
        case_id=case.case_id, event_type="HUMAN_REVIEW",
        state="REVIEWED", actor_id="reviewer-1", role="reviewer",
        event={"decision": "ACKNOWLEDGED"}, created_at="2026-01-01T01:00:00Z",
    )
    second = store.append_event(
        case_id=case.case_id, event_type="EXPORT_AUTHORISED",
        state="EXPORTED", actor_id="reviewer-1", role="reviewer",
        event={"official_submission": False}, created_at="2026-01-01T02:00:00Z",
    )
    assert (first, second) == (1, 2)
    assert [e["event_type"] for e in store.list_events(case.case_id)] == [
        "HUMAN_REVIEW", "EXPORT_AUTHORISED"
    ]
    with pytest.raises(sqlite3.IntegrityError, match="APPEND_ONLY"):
        with store._connect() as conn:
            conn.execute("DELETE FROM evidence_case_events WHERE event_id=1")


def test_invalid_cases_are_rejected(tmp_path):
    store = EvidenceCaseStore(tmp_path / "cases.db")
    case = _case()
    bad = type(case)(case.case_id, case.created_at, "REVIEWED", case.observation_fingerprint,
                     case.evidence, case.findings, None, case.provenance_fingerprint)
    with pytest.raises(ValueError):
        store.append(bad)
