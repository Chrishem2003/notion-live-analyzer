from pathlib import Path

import pytest

from nema_agora.admission import AdmissionDecision, AdmissionStore, ModelCandidate
from nema_agora.shadow_governance import ControlledShadowStore, execute_controlled_shadow


class Adapter:
    provider = "provider-a"
    model_version = "model-1"
    adapter_name = "adapter-a"

    def analyse(self, record):
        return {
            "source_case_id": record["case_id"],
            "summary": "advisory",
            "category_suggestions": [],
            "priority_advisory": "review",
            "quality_status": "VALID",
            "quality_flags": [],
            "human_review_required": True,
            "decision_notice": "Advisory only.",
        }


def _admission(tmp_path: Path, decision="ADMITTED_FOR_CONTROLLED_SHADOW"):
    candidate = ModelCandidate(
        provider="provider-a", model_version="model-1", adapter_name="adapter-a",
        intended_use="advisory", data_handling="synthetic", retention_policy="controlled",
        processing_location="local", failure_behaviour="fail closed",
    )
    item = AdmissionDecision(
        admission_id="ADM-TEST1234", candidate=candidate, dataset_version="ds-v1",
        manifest_hash="a" * 64, comparison_run_id="CMP-1", decision=decision,
        gates={"all": decision == "ADMITTED_FOR_CONTROLLED_SHADOW"},
        approver_id="coord-1", rationale="evidence reviewed", created_at="2026-10-04T12:00:00+03:00",
    )
    AdmissionStore(str(tmp_path / "nema.db")).save(item, actor_id="coord-1")
    return str(tmp_path / "nema.db"), item


def test_controlled_shadow_requires_admission(tmp_path):
    db, _ = _admission(tmp_path, "NOT_ADMITTED")
    with pytest.raises(PermissionError):
        execute_controlled_shadow(
            database_path=db,
            record={"case_id": "CASE-1"},
            admission_id="ADM-TEST1234",
            actor_id="reviewer-1",
            adapter=Adapter(),
        )


def test_controlled_shadow_binds_exact_adapter_identity(tmp_path):
    db, _ = _admission(tmp_path)
    class Wrong(Adapter):
        model_version = "model-2"
    with pytest.raises(ValueError):
        execute_controlled_shadow(
            database_path=db,
            record={"case_id": "CASE-1"},
            admission_id="ADM-TEST1234",
            actor_id="reviewer-1",
            adapter=Wrong(),
        )


def test_controlled_shadow_persists_bound_run(tmp_path):
    db, _ = _admission(tmp_path)
    result = execute_controlled_shadow(
        database_path=db,
        record={"case_id": "CASE-1"},
        admission_id="ADM-TEST1234",
        actor_id="reviewer-1",
        adapter=Adapter(),
    )
    assert result.status == "SHADOW_OK"
    assert result.human_review_required is True
    rows = ControlledShadowStore(db).list(admission_id="ADM-TEST1234")
    assert len(rows) == 1
    assert rows[0]["case_id"] == "CASE-1"
    assert rows[0]["provider"] == "provider-a"
