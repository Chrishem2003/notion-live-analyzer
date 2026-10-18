from datetime import date

import pytest

from nema_agora.core import CATEGORIES, make_observation
from nema_agora.identity import Principal
from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository


def principal(subject: str, role: str | None) -> Principal:
    return Principal(
        subject_key=f"https://issuer|{subject}",
        issuer="https://issuer",
        subject=subject,
        role=role,
    )


def record():
    return make_observation(
        observation_date=date(2026, 10, 4),
        category=CATEGORIES[0],
        severity="Moderate",
        site="Pilot A",
        description="Synthetic test observation",
        latitude=2.5,
        longitude=32.1,
        consent_confirmed=True,
        created_at="2026-10-04T12:00:00+03:00",
    )


def test_service_uses_principal_for_creation_and_read(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    created = service.create_observation(record(), principal("submitter-1", "submitter"))
    assert service.get_observation(created["case_id"], principal("submitter-1", "submitter")) == created
    with pytest.raises(PermissionError):
        service.get_observation(created["case_id"], principal("submitter-2", "submitter"))


def test_unprovisioned_principal_cannot_touch_repository(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    with pytest.raises(PermissionError):
        service.create_observation(record(), principal("unknown", None))


def test_submitter_cannot_export(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    with pytest.raises(PermissionError):
        service.export_csv(principal("submitter-1", "submitter"), [record()])


def test_coordinator_can_export(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    data = service.export_csv(principal("coord-1", "coordinator"), [record()])
    assert data.startswith(b"\xef\xbb\xbf")
    assert b"case_id" in data


def test_admin_operation_audit_is_principal_bound(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    admin = principal("admin-1", "admin")
    service.record_operation(admin, operation="backup_created", occurred_at="2026-10-04T12:00:00+03:00", details={"backup": "x.sqlite3"})
    events = service.list_operation_events(admin)
    assert events[0]["operation"] == "backup_created"
    assert events[0]["actor_id"] == "https://issuer|admin-1"
    with pytest.raises(PermissionError):
        service.record_operation(principal("coord-1", "coordinator"), operation="backup_created", occurred_at="now")


def test_service_cannot_accept_caller_supplied_owner_id(tmp_path):
    repo = NemaAgoraRepository(tmp_path / "pilot.sqlite3")
    service = NemaAgoraService(repo)
    owner = principal("owner-1", "submitter")
    record = make_observation(
        observation_date=date(2026, 10, 4), category=CATEGORIES[0], severity="Low",
        site="Pilot A", description="Synthetic", latitude=2.5, longitude=32.1,
        consent_confirmed=True, created_at="2026-10-04T12:00:00+03:00",
    )
    record["owner_id"] = "attacker-2"
    service.create_observation(record, owner)
    assert repo.get_observation(record["case_id"], actor_id=owner.subject_key, role="submitter")["owner_id"] == owner.subject_key


def test_intelligence_requires_reviewer_permission(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    owner = principal("submitter-1", "submitter")
    reviewer = principal("reviewer-1", "reviewer")
    rec = record()
    with pytest.raises(PermissionError):
        service.analyze_observation(rec, owner)
    result = service.analyze_observation(rec, reviewer, peer_records=[])
    assert result["human_review_required"] is True


def test_reviewer_copilot_and_feedback_are_principal_bound(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    reviewer = principal("reviewer-1", "reviewer")
    rec = service.create_observation(record(), principal("submitter-1", "submitter"))
    copilot = service.build_reviewer_copilot(rec, reviewer, peer_records=[rec])
    assert copilot["source_case_id"] == rec["case_id"]
    service.record_intelligence_feedback(
        rec["case_id"],
        reviewer,
        feedback={
            "feedback_type": "accepted",
            "copilot_version": copilot["copilot_version"],
            "notes": "Synthetic reviewer feedback",
        },
        occurred_at="2026-10-04T12:05:00+03:00",
    )
    events = service.list_intelligence_events(rec["case_id"], principal("admin-1", "admin"))
    assert [e["event_type"] for e in events] == ["analysis_run", "feedback_recorded"]


def test_submitter_cannot_record_copilot_feedback(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    rec = service.create_observation(record(), principal("submitter-1", "submitter"))
    with pytest.raises(PermissionError):
        service.record_intelligence_feedback(
            rec["case_id"], principal("submitter-1", "submitter"),
            feedback={"feedback_type": "accepted"},
            occurred_at="2026-10-04T12:05:00+03:00",
        )


def test_model_admission_binds_approver_to_authenticated_principal(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    coordinator = principal("coord-1", "coordinator")
    from nema_agora.admission import ModelCandidate
    candidate = ModelCandidate(
        provider="provider-a",
        model_version="model-1",
        adapter_name="adapter-a",
        intended_use="advisory classification",
        data_handling="synthetic only",
        retention_policy="controlled",
        processing_location="local",
        failure_behaviour="fail closed",
    )
    with pytest.raises(PermissionError):
        service.evaluate_model_admission(
            candidate=candidate,
            dataset={"dataset_version":"v1","manifest_hash":"0"*64,"cases":25},
            annotation_readiness={},
            comparison={},
            comparison_run_id="CMP-1",
            principal=coordinator,
            approver_id="different-person",
            rationale="Review.",
        )



def test_governed_evidence_workflow_requires_review_and_export_permission(tmp_path):
    from dataclasses import replace

    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    submitter = principal("submitter-flow", "submitter")
    reviewer = principal("reviewer-flow", "reviewer")
    coordinator = principal("coordinator-flow", "coordinator")
    created = service.create_observation(record(), submitter)

    with pytest.raises(PermissionError):
        service.build_governed_evidence_case(created["case_id"], submitter)

    prepared = service.build_governed_evidence_case(created["case_id"], reviewer)
    evidence_case = prepared["evidence_case"]
    assert prepared["integrity"]["valid"] is True
    assert prepared["durable"] is True
    assert prepared["quality_assessment"]["human_review_required"] is True
    assert prepared["environmental_truth_claim"] is False

    with pytest.raises(ValueError, match="human-reviewed"):
        service.export_governed_evidence_case(evidence_case, coordinator)

    reviewed = service.review_governed_evidence_case(
        evidence_case, reviewer, decision="ACKNOWLEDGED",
        notes="Reviewed synthetic pilot evidence",
        reviewed_at="2026-10-04T12:10:00+03:00",
    )
    with pytest.raises(PermissionError):
        service.export_governed_evidence_case(reviewed, reviewer)

    export_bytes = service.export_governed_evidence_case(reviewed, coordinator)
    import json
    payload = json.loads(export_bytes)
    assert payload["case"]["state"] == "EXPORTED"
    assert payload["integrity"]["valid"] is True
    assert payload["human_governed"] is True
    assert payload["durable"] is True
    assert payload["nema_authorization"] is False

    tampered = replace(reviewed, observation_fingerprint="tampered")
    with pytest.raises(ValueError, match="integrity validation"):
        service.export_governed_evidence_case(tampered, coordinator)


def test_observation_quality_workflow_preserves_explicit_consent_flag():
    rec = record()
    assert rec["consent_confirmed"] is True



def test_evidence_case_survives_repository_reopen_and_records_transitions(tmp_path):
    import json
    from nema_agora.evidence_case import evidence_case_from_dict

    path = tmp_path / "durable-pilot.sqlite3"
    service = NemaAgoraService(NemaAgoraRepository(path))
    submitter = principal("durable-submit", "submitter")
    reviewer = principal("durable-review", "reviewer")
    coordinator = principal("durable-coord", "coordinator")
    admin = principal("durable-admin", "admin")
    created = service.create_observation(record(), submitter)

    prepared = service.build_governed_evidence_case(created["case_id"], reviewer)
    case = prepared["evidence_case"]
    reviewed = service.review_governed_evidence_case(
        case, reviewer, decision="ACKNOWLEDGED",
        notes="Durable synthetic test", reviewed_at="2026-10-04T12:15:00+03:00",
    )

    reopened = NemaAgoraService(NemaAgoraRepository(path))
    stored = reopened.repository.get_evidence_case(
        created["case_id"], actor_id=coordinator.subject_key, role=coordinator.role
    )
    assert stored is not None
    restored = evidence_case_from_dict(stored["bundle"])
    assert restored.to_dict() == reviewed.to_dict()
    assert stored["state"] == "REVIEWED"

    export_payload = json.loads(reopened.export_governed_evidence_case(restored, coordinator))
    assert export_payload["case"]["state"] == "EXPORTED"
    assert export_payload["durable"] is True

    events = reopened.list_evidence_case_events(created["case_id"], admin)
    assert [event["event_type"] for event in events] == [
        "evidence_case_prepared", "evidence_case_reviewed", "evidence_case_exported"
    ]
    assert [event["to_state"] for event in events] == [
        "READY_FOR_REVIEW", "REVIEWED", "EXPORTED"
    ]
    assert events[1]["actor_id"] == reviewer.subject_key
    assert events[2]["actor_id"] == coordinator.subject_key


def test_repeated_or_stale_evidence_review_is_rejected(tmp_path):
    from dataclasses import replace

    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "stale-pilot.sqlite3"))
    reviewer = principal("stale-review", "reviewer")
    created = service.create_observation(record(), principal("stale-submit", "submitter"))
    first = service.build_governed_evidence_case(created["case_id"], reviewer)["evidence_case"]
    second = service.build_governed_evidence_case(created["case_id"], reviewer)["evidence_case"]
    reviewed = service.review_governed_evidence_case(
        first, reviewer, decision="ACKNOWLEDGED", notes="first review",
        reviewed_at="2026-10-04T12:20:00+03:00",
    )
    assert reviewed.state == "REVIEWED"
    with pytest.raises(ValueError, match="stale|not awaiting"):
        service.review_governed_evidence_case(
            second, reviewer, decision="ESCALATED", notes="duplicate attempt",
            reviewed_at="2026-10-04T12:21:00+03:00",
        )
