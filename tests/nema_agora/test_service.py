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
    with pytest.raises(ValueError, match="Source observation changed|integrity validation|stale|differs"):
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

    import sqlite3
    with sqlite3.connect(path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE evidence_case_events SET actor_id = 'forged' WHERE case_id = ?",
                (created["case_id"],),
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "DELETE FROM evidence_case_events WHERE case_id = ?",
                (created["case_id"],),
            )

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



def test_persisted_evidence_bundle_tampering_is_detected_after_reopen(tmp_path):
    import sqlite3

    path = tmp_path / "tamper-pilot.sqlite3"
    service = NemaAgoraService(NemaAgoraRepository(path))
    reviewer = principal("tamper-review", "reviewer")
    created = service.create_observation(record(), principal("tamper-submit", "submitter"))
    service.build_governed_evidence_case(created["case_id"], reviewer)

    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE evidence_cases SET bundle_json = replace(bundle_json, 'READY_FOR_REVIEW', 'REVIEWED') WHERE case_id = ?",
            (created["case_id"],),
        )

    reopened = NemaAgoraRepository(path)
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        reopened.get_evidence_case(
            created["case_id"], actor_id=reviewer.subject_key, role=reviewer.role
        )



def test_repeated_evidence_preparation_does_not_duplicate_audit_event(tmp_path):
    import hashlib
    import json

    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "idempotent-pilot.sqlite3"))
    reviewer = principal("idempotent-review", "reviewer")
    admin = principal("idempotent-admin", "admin")
    created = service.create_observation(record(), principal("idempotent-submit", "submitter"))
    prepared = service.build_governed_evidence_case(created["case_id"], reviewer)
    bundle_dict = prepared["evidence_case"].to_dict()
    fingerprint = hashlib.sha256(
        json.dumps(bundle_dict, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()

    with pytest.raises(ValueError, match="ISO 8601 timestamp with timezone"):
        service.repository.create_evidence_case(
            bundle_dict, actor_id=reviewer.subject_key, role=reviewer.role,
            occurred_at="not-a-time", bundle_fingerprint=fingerprint,
        )
    result = service.repository.create_evidence_case(
        bundle_dict, actor_id=reviewer.subject_key, role=reviewer.role,
        occurred_at="2026-10-04T12:30:00+03:00", bundle_fingerprint=fingerprint,
    )
    assert result["already_exists"] is True
    events = service.list_evidence_case_events(created["case_id"], admin)
    assert [event["event_type"] for event in events] == ["evidence_case_prepared"]


def test_export_transition_cannot_be_replayed(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "replay-pilot.sqlite3"))
    reviewer = principal("replay-review", "reviewer")
    coordinator = principal("replay-coord", "coordinator")
    created = service.create_observation(record(), principal("replay-submit", "submitter"))
    bundle = service.build_governed_evidence_case(created["case_id"], reviewer)["evidence_case"]
    reviewed = service.review_governed_evidence_case(
        bundle, reviewer, decision="ACKNOWLEDGED", notes="replay test",
        reviewed_at="2026-10-04T12:40:00+03:00",
    )
    service.export_governed_evidence_case(reviewed, coordinator)
    with pytest.raises(ValueError, match="stale|differs|human-reviewed"):
        service.export_governed_evidence_case(reviewed, coordinator)



def test_source_observation_change_blocks_evidence_review(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "source-drift.sqlite3"))
    reviewer = principal("drift-review", "reviewer")
    created = service.create_observation(record(), principal("drift-submit", "submitter"))
    bundle = service.build_governed_evidence_case(created["case_id"], reviewer)["evidence_case"]

    service.update_review(
        created["case_id"], reviewer, new_status="Under review",
        review_notes="Workflow status changed after evidence snapshot",
        changed_at="2026-10-04T12:50:00+03:00",
    )

    with pytest.raises(ValueError, match="Source observation changed"):
        service.review_governed_evidence_case(
            bundle, reviewer, decision="ACKNOWLEDGED", notes="stale source",
            reviewed_at="2026-10-04T12:51:00+03:00",
        )



def test_source_observation_change_blocks_export_after_review(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "source-drift-export.sqlite3"))
    reviewer = principal("drift-export-review", "reviewer")
    coordinator = principal("drift-export-coord", "coordinator")
    created = service.create_observation(record(), principal("drift-export-submit", "submitter"))
    bundle = service.build_governed_evidence_case(created["case_id"], reviewer)["evidence_case"]
    reviewed = service.review_governed_evidence_case(
        bundle, reviewer, decision="ACKNOWLEDGED", notes="review before source change",
        reviewed_at="2026-10-04T12:55:00+03:00",
    )
    service.update_review(
        created["case_id"], reviewer, new_status="Under review",
        review_notes="Source changed after evidence review",
        changed_at="2026-10-04T12:56:00+03:00",
    )
    with pytest.raises(ValueError, match="Source observation changed"):
        service.export_governed_evidence_case(reviewed, coordinator)


def test_evidence_lifecycle_events_require_audit_read_permission(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "evidence-event-access.sqlite3"))
    submitter = principal("event-access-submit", "submitter")
    reviewer = principal("event-access-review", "reviewer")
    coordinator = principal("event-access-coord", "coordinator")
    created = service.create_observation(record(), submitter)
    service.build_governed_evidence_case(created["case_id"], reviewer)

    with pytest.raises(PermissionError):
        service.list_evidence_case_events(created["case_id"], submitter)
    with pytest.raises(PermissionError):
        service.list_evidence_case_events(created["case_id"], reviewer)

    events = service.list_evidence_case_events(created["case_id"], coordinator)
    assert len(events) == 1
    assert events[0]["event_type"] == "evidence_case_prepared"

def test_failed_evidence_lifecycle_actions_leave_state_and_audit_unchanged(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "evidence-atomicity.sqlite3"))
    submitter = principal("atomic-submit", "submitter")
    reviewer = principal("atomic-review", "reviewer")
    coordinator = principal("atomic-coord", "coordinator")
    created = service.create_observation(record(), submitter)
    case_id = created["case_id"]
    prepared = service.build_governed_evidence_case(case_id, reviewer)["evidence_case"]

    with pytest.raises(ValueError, match="invalid human review decision"):
        service.review_governed_evidence_case(
            prepared, reviewer, decision="AUTO_APPROVE",
            notes="Invalid synthetic test decision",
            reviewed_at="2026-10-04T12:30:00+03:00",
        )

    unchanged = service.repository.get_evidence_case(
        case_id, actor_id=reviewer.subject_key, role=reviewer.role
    )
    assert unchanged["state"] == "READY_FOR_REVIEW"
    events = service.list_evidence_case_events(case_id, coordinator)
    assert [event["event_type"] for event in events] == ["evidence_case_prepared"]

    reviewed = service.review_governed_evidence_case(
        prepared, reviewer, decision="ACKNOWLEDGED",
        notes="Valid human review", reviewed_at="2026-10-04T12:31:00+03:00",
    )
    with pytest.raises(ValueError, match="not awaiting human review|stale|differs"):
        service.review_governed_evidence_case(
            prepared, reviewer, decision="ESCALATED",
            notes="Replay must not create another event",
            reviewed_at="2026-10-04T12:32:00+03:00",
        )
    events = service.list_evidence_case_events(case_id, coordinator)
    assert [event["event_type"] for event in events] == [
        "evidence_case_prepared", "evidence_case_reviewed"
    ]
    assert events[-1]["actor_id"] == reviewer.subject_key

    service.export_governed_evidence_case(reviewed, coordinator)
    with pytest.raises(ValueError, match="stale|differs|human-reviewed"):
        service.export_governed_evidence_case(reviewed, coordinator)
    events = service.list_evidence_case_events(case_id, coordinator)
    assert [event["event_type"] for event in events] == [
        "evidence_case_prepared", "evidence_case_reviewed", "evidence_case_exported"
    ]

def test_evidence_transition_rechecks_source_observation_under_write_lock(tmp_path, monkeypatch):
    repository = NemaAgoraRepository(tmp_path / "evidence-source-race.sqlite3")
    service = NemaAgoraService(repository)
    submitter = principal("source-race-submit", "submitter")
    reviewer = principal("source-race-review", "reviewer")
    coordinator = principal("source-race-coord", "coordinator")
    created = service.create_observation(record(), submitter)
    case_id = created["case_id"]
    prepared = service.build_governed_evidence_case(case_id, reviewer)["evidence_case"]

    original_transition = repository.transition_evidence_case
    injected = {"done": False}

    def change_source_then_transition(*args, **kwargs):
        if not injected["done"]:
            injected["done"] = True
            repository.update_review(
                case_id,
                actor_id=reviewer.subject_key,
                role=reviewer.role,
                new_status="Under review",
                review_notes="Source changed between service precheck and transition",
                changed_at="2026-10-04T12:40:00+03:00",
            )
        return original_transition(*args, **kwargs)

    monkeypatch.setattr(repository, "transition_evidence_case", change_source_then_transition)
    with pytest.raises(ValueError, match="Observation changed since evidence preparation"):
        service.review_governed_evidence_case(
            prepared,
            reviewer,
            decision="ACKNOWLEDGED",
            notes="Must fail when source changes during transition",
            reviewed_at="2026-10-04T12:41:00+03:00",
        )

    persisted = repository.get_evidence_case(
        case_id, actor_id=reviewer.subject_key, role=reviewer.role
    )
    assert persisted["state"] == "READY_FOR_REVIEW"
    events = service.list_evidence_case_events(case_id, coordinator)
    assert [event["event_type"] for event in events] == ["evidence_case_prepared"]

