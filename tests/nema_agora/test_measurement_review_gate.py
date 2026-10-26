from __future__ import annotations

import pytest

from nema_agora.measurement_review_gate import (
    MeasurementReviewError,
    prepare_measurement_review,
)


@pytest.fixture
def principal():
    return {"authenticated": True, "subject": "reviewer-7", "role": "reviewer"}


@pytest.fixture
def measurement():
    return {
        "measurement_id": "m-001",
        "status": "measured",
        "submitted_by": "submitter-2",
        "evidence_refs": [{"reference": "field-note-1", "sha256": "a" * 64}],
    }


def test_independent_acceptance_recommends_verification_without_verifying(principal, measurement):
    result = prepare_measurement_review(
        principal=principal,
        measurement=measurement,
        decision="accept_for_verification",
        reviewed_at="2026-10-27T09:30:00+03:00",
        notes="Evidence references present; separate verification is still required.",
    )
    assert result["decision"] == "accept_for_verification"
    assert result["measurement_status_before"] == result["measurement_status_after"] == "measured"
    assert result["verification_performed"] is False
    assert result["evidence_authenticity_verified"] is False
    assert result["persistence_performed"] is False


def test_submitter_cannot_review_own_measurement(principal, measurement):
    principal["subject"] = "submitter-2"
    with pytest.raises(MeasurementReviewError, match="cannot review their own"):
        prepare_measurement_review(
            principal=principal, measurement=measurement, decision="reject",
            reviewed_at="2026-10-27T09:30:00+03:00", notes="Not independently reviewed",
        )


def test_unverified_principal_is_denied(principal, measurement):
    principal["authenticated"] = False
    with pytest.raises(MeasurementReviewError, match="authenticated reviewer"):
        prepare_measurement_review(
            principal=principal, measurement=measurement, decision="reject",
            reviewed_at="2026-10-27T09:30:00+03:00", notes="Reason",
        )


def test_submitter_role_cannot_review(principal, measurement):
    principal["role"] = "submitter"
    with pytest.raises(MeasurementReviewError, match="cannot review"):
        prepare_measurement_review(
            principal=principal, measurement=measurement, decision="reject",
            reviewed_at="2026-10-27T09:30:00+03:00", notes="Reason",
        )


def test_rejection_requires_reason(principal, measurement):
    with pytest.raises(MeasurementReviewError, match="reason is required"):
        prepare_measurement_review(
            principal=principal, measurement=measurement, decision="reject",
            reviewed_at="2026-10-27T09:30:00+03:00", notes=" ",
        )


def test_acceptance_requires_evidence_refs(principal, measurement):
    measurement["evidence_refs"] = []
    with pytest.raises(MeasurementReviewError, match="Evidence references"):
        prepare_measurement_review(
            principal=principal, measurement=measurement, decision="accept_for_verification",
            reviewed_at="2026-10-27T09:30:00+03:00",
        )


def test_naive_timestamp_is_rejected(principal, measurement):
    with pytest.raises(MeasurementReviewError, match="include a timezone"):
        prepare_measurement_review(
            principal=principal, measurement=measurement, decision="reject",
            reviewed_at="2026-10-27T09:30:00", notes="Reason",
        )


def test_review_cannot_skip_measured_state(principal, measurement):
    measurement["status"] = "verified"
    with pytest.raises(MeasurementReviewError, match="Only measured records"):
        prepare_measurement_review(
            principal=principal, measurement=measurement, decision="accept_for_verification",
            reviewed_at="2026-10-27T09:30:00+03:00",
        )
