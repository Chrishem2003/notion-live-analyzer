"""Tests for the NEMA-AGORA audited transition service."""
import pytest

from nema_agora.workflow import apply_case_transition


def case(**updates):
    record = {"case_id": "NA-TEST001", "status": "Received", "review_notes": "keep"}
    record.update(updates)
    return record


def test_transition_returns_copy_and_audit_event_without_mutating_input():
    original = case()
    updated, event = apply_case_transition(
        original,
        new_status="Under review",
        actor="reviewer-17",
        changed_at="2026-10-22T16:00:00+03:00",
    )
    assert original["status"] == "Received"
    assert updated is not original
    assert updated["status"] == "Under review"
    assert updated["review_notes"] == "keep"
    assert event == {
        "event_type": "case_status_transition",
        "case_id": "NA-TEST001",
        "from_status": "Received",
        "to_status": "Under review",
        "actor": "reviewer-17",
        "changed_at": "2026-10-22T16:00:00+03:00",
        "reason": "",
    }


def test_same_status_is_a_no_op_without_an_audit_event():
    updated, event = apply_case_transition(
        case(status="Under review"),
        new_status="Under review",
        actor="reviewer-17",
        changed_at="2026-10-22T13:00:00Z",
    )
    assert updated["status"] == "Under review"
    assert event is None


def test_closed_case_reopening_records_reason():
    updated, event = apply_case_transition(
        case(status="Closed"),
        new_status="Under review",
        actor="supervisor-2",
        changed_at="2026-10-22T13:00:00Z",
        reason="New evidence received",
    )
    assert updated["status"] == "Under review"
    assert event["reason"] == "New evidence received"


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"actor": " "}, "actor"),
        ({"changed_at": "2026-10-22T13:00:00"}, "timezone"),
        ({"changed_at": "not-a-date"}, "ISO-8601"),
        ({"new_status": "Auto-enforced"}, "not recognised"),
    ],
)
def test_invalid_transition_metadata_or_status_fails_closed(kwargs, match):
    values = {
        "new_status": "Under review",
        "actor": "reviewer-17",
        "changed_at": "2026-10-22T13:00:00Z",
    }
    values.update(kwargs)
    with pytest.raises(ValueError, match=match):
        apply_case_transition(case(), **values)


def test_closed_case_cannot_be_reopened_without_meaningful_reason():
    with pytest.raises(ValueError, match="reason"):
        apply_case_transition(
            case(status="Closed"),
            new_status="Under review",
            actor="supervisor-2",
            changed_at="2026-10-22T13:00:00Z",
            reason="oops",
        )


def test_invalid_record_and_missing_case_id_fail_closed():
    with pytest.raises(ValueError, match="mapping"):
        apply_case_transition(None, new_status="Under review", actor="a", changed_at="2026-10-22T13:00:00Z")
    with pytest.raises(ValueError, match="case ID"):
        apply_case_transition({"status": "Received"}, new_status="Under review", actor="a", changed_at="2026-10-22T13:00:00Z")
