import time

import pytest

from nema_agora.core import CATEGORIES, make_observation
from nema_agora.identity import Principal
from nema_agora.service import NemaAgoraService
from nema_agora.shadow import DeterministicShadowAdapter, run_shadow
from nema_agora.storage import NemaAgoraRepository


def sample():
    return make_observation(
        observation_date=__import__("datetime").date(2026, 10, 4),
        category=CATEGORIES[0],
        severity="Moderate",
        site="Pilot A",
        description="Synthetic shadow observation",
        latitude=2.5,
        longitude=32.1,
        consent_confirmed=True,
        created_at="2026-10-04T12:00:00+03:00",
    )


class UnsafeAdapter:
    provider = "test-provider"
    model_version = "unsafe-v1"

    def analyse(self, record):
        return {
            "source_case_id": record["case_id"],
            "human_review_required": True,
            "enforcement_action": "dispatch",
        }


class SlowAdapter:
    provider = "test-provider"
    model_version = "slow-v1"

    def analyse(self, record):
        time.sleep(0.001)
        return {"source_case_id": record["case_id"], "human_review_required": True}


def principal(subject, role):
    return Principal(f"https://issuer|{subject}", "https://issuer", subject, role)


def test_shadow_deterministic_adapter_is_advisory_and_bound():
    record = sample()
    result = run_shadow(record, DeterministicShadowAdapter())
    assert result.status == "SHADOW_OK"
    assert result.source_case_id == record["case_id"]
    assert result.human_review_required is True
    assert result.output["source_case_id"] == record["case_id"]
    assert result.latency_ms >= 0
    assert record["status"] == "Received"


def test_shadow_rejects_autonomous_output_without_touching_record():
    record = sample()
    result = run_shadow(record, UnsafeAdapter())
    assert result.status == "SHADOW_ERROR"
    assert result.output is None
    assert "enforcement_action" in (result.error or "")
    assert record["status"] == "Received"


def test_shadow_captures_latency():
    result = run_shadow(sample(), SlowAdapter())
    assert result.status == "SHADOW_OK"
    assert result.latency_ms >= 0.5


def test_shadow_service_requires_shadow_permission_and_persists_separately(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    rec = service.create_observation(sample(), principal("submitter-1", "submitter"))
    reviewer = principal("reviewer-1", "reviewer")

    with pytest.raises(PermissionError):
        service.run_shadow(rec, reviewer)

    admin = principal("admin-1", "admin")
    result = service.run_shadow(rec, admin)
    assert result["status"] == "SHADOW_OK"
    assert result["source_case_id"] == rec["case_id"]
    assert service.get_observation(rec["case_id"], admin)["status"] == "Received"

    events = service.list_shadow_runs(rec["case_id"], admin)
    assert len(events) == 1
    assert events[0]["provider"] == "local-deterministic"
