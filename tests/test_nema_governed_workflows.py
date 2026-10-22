from __future__ import annotations

import pytest

from modules.governed_automation_runtime import (
    AutomationAuthorizationError,
    GovernedAutomationRuntime,
)
from nema_agora.workflows import (
    build_case_review_packet,
    register_nema_readonly_workflows,
)


def _response(case_id="NEMA-001"):
    return {
        "record": {
            "case_id": case_id,
            "district_or_site": "Gulu",
            "category": "wetland",
            "severity": "high",
            "status": "open",
            "observation_date": "2026-10-20",
            "description": "Possible wetland encroachment reported for review.",
            "latitude": 2.7746,
            "longitude": 32.2990,
        },
        "version": 3,
        "audit": [
            {"event_type": "case_created"},
            {"event_type": "case_reviewed"},
        ],
        "mode": "read_only",
    }


def test_review_packet_is_deterministic_and_requires_human_review():
    packet = build_case_review_packet("NEMA-001", _response())
    assert packet["workflow"] == "nema.case_review_packet"
    assert packet["review_status"] == "human_review_required"
    assert packet["source_mode"] == "read_only"
    assert packet["record_version"] == 3
    assert packet["data_quality"]["required_fields_complete"] is True
    assert packet["coordinate_state"] == "present_with_valid_ranges"
    assert packet["audit_summary"] == {
        "event_count_returned": 2,
        "latest_event_type": "case_reviewed",
    }
    assert "No case data was changed by this workflow." in packet["limitations"]


def test_review_packet_flags_missing_fields_and_bad_coordinates():
    response = _response()
    response["record"]["description"] = " "
    response["record"]["latitude"] = 999
    packet = build_case_review_packet("NEMA-001", response)
    assert "description" in packet["data_quality"]["missing_required_fields"]
    assert packet["data_quality"]["required_fields_complete"] is False
    assert packet["coordinate_state"] == "incomplete_or_invalid"


def test_review_packet_rejects_mismatched_case_and_invalid_version():
    with pytest.raises(ValueError, match="different case"):
        build_case_review_packet("NEMA-001", _response("NEMA-002"))
    response = _response()
    response["version"] = True
    with pytest.raises(ValueError, match="version"):
        build_case_review_packet("NEMA-001", response)


def test_runtime_registers_only_an_authorized_readonly_workflow(tmp_path):
    calls = []
    runtime = GovernedAutomationRuntime(
        tmp_path / "automation.sqlite3",
        authorize=lambda actor, workflow: actor == "reviewer-1" and workflow == "nema.case_review_packet",
    )
    try:
        register_nema_readonly_workflows(
            runtime,
            read_case=lambda case_id: calls.append(case_id) or _response(case_id),
        )
        result = runtime.execute(
            "nema.case_review_packet",
            {"case_id": "NEMA-001"},
            actor="reviewer-1",
            idempotency_key="review:NEMA-001:v1",
        )
        assert result["status"] == "succeeded"
        assert result["output"]["review_status"] == "human_review_required"
        assert calls == ["NEMA-001"]
        audit = runtime.list_audit(result["job_id"], actor="reviewer-1")
        assert [item["event_type"] for item in audit] == ["job_started", "job_succeeded"]
    finally:
        runtime.close()


def test_unauthorized_runtime_cannot_call_case_reader(tmp_path):
    calls = []
    runtime = GovernedAutomationRuntime(
        tmp_path / "automation.sqlite3",
        authorize=lambda actor, workflow: False,
    )
    try:
        register_nema_readonly_workflows(
            runtime,
            read_case=lambda case_id: calls.append(case_id) or _response(case_id),
        )
        with pytest.raises(AutomationAuthorizationError):
            runtime.execute(
                "nema.case_review_packet",
                {"case_id": "NEMA-001"},
                actor="untrusted",
                idempotency_key="denied",
            )
        assert calls == []
    finally:
        runtime.close()


def test_invalid_input_does_not_call_case_reader(tmp_path):
    calls = []
    runtime = GovernedAutomationRuntime(
        tmp_path / "automation.sqlite3",
        authorize=lambda actor, workflow: True,
    )
    try:
        register_nema_readonly_workflows(
            runtime,
            read_case=lambda case_id: calls.append(case_id) or _response(case_id),
        )
        with pytest.raises(ValueError):
            runtime.execute(
                "nema.case_review_packet",
                {"case_id": " NEMA-001 "},
                actor="reviewer",
                idempotency_key="bad-input",
            )
        assert calls == []
    finally:
        runtime.close()
