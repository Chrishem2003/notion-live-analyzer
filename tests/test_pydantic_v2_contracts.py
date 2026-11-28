"""Pydantic v2 compatibility and validation-contract regression tests.

These tests use synthetic payloads only and do not contact Notion, Supabase,
AI providers, job repositories, or deployed services.
"""
import pytest
from pydantic import ValidationError

from api_server import ResearchRunWriteRequest
from platform_jobs.api import JobCreateRequest
from platform_jobs.user_api import UserJobCreateRequest
from shared_ai_gateway import AutomationDraft


def _research_run_payload(**overrides):
    payload = {
        "run_id": "synthetic-pydantic-v2-run",
        "run_name": "Synthetic Pydantic v2 contract",
        "project_page_id": "synthetic-project",
        "protocol_page_id": "synthetic-protocol",
        "parameters_json": "{\"synthetic\": true}",
    }
    payload.update(overrides)
    return payload


def _workflow_step(index=1):
    return {
        "id": f"step_{index}",
        "type": "manual_approval",
        "description": "Review synthetic workflow step",
    }


def _automation_draft(**overrides):
    payload = {
        "title": "Synthetic approval workflow",
        "trigger": "A synthetic request is submitted",
        "steps": [_workflow_step()],
        "risk_level": "low",
    }
    payload.update(overrides)
    return payload


def test_research_run_model_uses_v2_dump_and_preserves_defaults():
    model = ResearchRunWriteRequest.model_validate(_research_run_payload())
    dumped = model.model_dump()

    assert dumped["run_id"] == "synthetic-pydantic-v2-run"
    assert dumped["parameters_json"] == "{\"synthetic\": true}"
    assert dumped["input_sample_page_ids"] == []
    assert dumped["input_data_record_page_ids"] == []
    assert dumped["source_evidence_page_ids"] == []


@pytest.mark.parametrize("value", ["{malformed", "[]", '"scalar"', "42", "null"])
def test_research_run_parameters_json_still_requires_an_object(value):
    with pytest.raises(ValidationError):
        ResearchRunWriteRequest.model_validate(
            _research_run_payload(parameters_json=value)
        )


def test_research_run_parameters_json_still_allows_empty_legacy_value():
    model = ResearchRunWriteRequest.model_validate(
        _research_run_payload(parameters_json="")
    )
    assert model.parameters_json == ""


def test_service_job_prompt_validator_rejects_whitespace():
    with pytest.raises(ValidationError):
        JobCreateRequest.model_validate({"prompt": " \t\n"})


def test_service_job_prompt_validator_accepts_nonblank_value():
    model = JobCreateRequest.model_validate({"prompt": " synthetic job "})
    assert model.prompt == " synthetic job "


@pytest.mark.parametrize(
    "payload",
    [
        {"prompt": " \t"},
        {"prompt": "synthetic", "provider": " "},
        {"prompt": "synthetic", "model": "\n"},
        {"prompt": "synthetic", "strategy": " "},
    ],
)
def test_user_job_validators_reject_blank_prompt_or_routing_values(payload):
    with pytest.raises(ValidationError):
        UserJobCreateRequest.model_validate(payload)


def test_user_job_model_still_forbids_client_supplied_ownership_fields():
    with pytest.raises(ValidationError):
        UserJobCreateRequest.model_validate(
            {"prompt": "synthetic", "tenant_id": "another-user"}
        )


def test_user_job_model_accepts_valid_synthetic_request():
    model = UserJobCreateRequest.model_validate(
        {"prompt": "synthetic request", "provider": "ollama", "model": "local-test"}
    )
    assert model.prompt == "synthetic request"
    assert model.strategy == "direct"


def test_automation_draft_requires_at_least_one_step():
    with pytest.raises(ValidationError):
        AutomationDraft.model_validate(_automation_draft(steps=[]))


def test_automation_draft_accepts_maximum_step_count():
    model = AutomationDraft.model_validate(
        _automation_draft(steps=[_workflow_step(i) for i in range(1, 41)])
    )
    assert len(model.steps) == 40


def test_automation_draft_rejects_more_than_maximum_step_count():
    with pytest.raises(ValidationError):
        AutomationDraft.model_validate(
            _automation_draft(steps=[_workflow_step(i) for i in range(1, 42)])
        )


@pytest.mark.parametrize(
    ("field", "limit"),
    [
        ("error_handling", 20),
        ("permissions_required", 30),
        ("test_plan", 20),
        ("assumptions", 20),
    ],
)
def test_automation_draft_preserves_list_maximums(field, limit):
    accepted = AutomationDraft.model_validate(
        _automation_draft(**{field: ["synthetic"] * limit})
    )
    assert len(getattr(accepted, field)) == limit

    with pytest.raises(ValidationError):
        AutomationDraft.model_validate(
            _automation_draft(**{field: ["synthetic"] * (limit + 1)})
        )
