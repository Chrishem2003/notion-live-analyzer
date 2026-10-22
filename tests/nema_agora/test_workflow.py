import pytest

from nema_agora.workflow import apply_status_update


def sample_record(status="Received"):
    return {
        "case_id": "NA-1234ABCD",
        "status": status,
        "review_notes": "",
        "updated_at": "",
    }


def test_received_can_move_to_under_review_and_emits_event():
    original = sample_record()
    updated, event = apply_status_update(
        original,
        new_status="Under review",
        review_notes="Initial triage complete",
        changed_at="2026-10-04T10:00:00+03:00",
    )
    assert updated["status"] == "Under review"
    assert updated["review_notes"] == "Initial triage complete"
    assert event == {
        "case_id": "NA-1234ABCD",
        "from_status": "Received",
        "to_status": "Under review",
        "changed_at": "2026-10-04T10:00:00+03:00",
    }
    assert original["status"] == "Received"


def test_invalid_shortcut_transition_is_rejected():
    with pytest.raises(ValueError, match="cannot move directly"):
        apply_status_update(
            sample_record(),
            new_status="Closed",
            review_notes="",
            changed_at="now",
        )


def test_closed_case_can_be_reopened_for_review():
    updated, event = apply_status_update(
        sample_record("Closed"),
        new_status="Under review",
        review_notes="Reopened for correction",
        changed_at="now",
    )
    assert updated["status"] == "Under review"
    assert event["from_status"] == "Closed"


def test_notes_only_update_does_not_create_status_event():
    updated, event = apply_status_update(
        sample_record("Under review"),
        new_status="Under review",
        review_notes="Updated reviewer note",
        changed_at="now",
    )
    assert updated["review_notes"] == "Updated reviewer note"
    assert event is None


def test_reviewer_notes_are_limited():
    with pytest.raises(ValueError, match="1,000 characters"):
        apply_status_update(
            sample_record("Under review"),
            new_status="Under review",
            review_notes="x" * 1001,
            changed_at="now",
        )
