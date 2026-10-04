import json
import pytest

from nema_agora.admission import (
    ADMITTED, NOT_ADMITTED, AdmissionStore, ModelAdmissionPolicy,
    ModelCandidate, evaluate_admission,
)


def candidate():
    return ModelCandidate(
        provider="provider-a", model_version="model-1", adapter_name="adapter-a",
        intended_use="advisory classification", data_handling="synthetic only",
        retention_policy="controlled project retention", processing_location="local",
        failure_behaviour="fail closed and require human review",
    )


def evidence():
    c=candidate()
    return (
        {
            "dataset_version":"dataset-v1","manifest_hash":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","cases":25,
        },
        {
            "status":"READY_FOR_REVIEW",
            "minimum_category_kappa":0.85,
            "unresolved_disagreements":[],
            "gates":{
                "minimum_double_annotated_cases":True,
                "two_independent_annotators":True,
                "all_annotator_pairs_measured":True,
                "minimum_category_kappa":True,
                "all_disagreements_adjudicated":True,
            },
        },
        {
            "run_id":"CMP-123",
            "readiness":"READY_FOR_REVIEW",
            "dataset":{"dataset_version":"dataset-v1","manifest_hash":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","cases":25},
            "adapters":[{
                "adapter":"adapter-a","provider":"provider-a","model_version":"model-1",
                "failures":0,"category_accuracy":0.88,"duplicate_f1":0.91,
            }],
            "case_results":[
                {"adapter":"adapter-a","status":"OK","output":{
                    "source_case_id":f"CASE-{i}","human_review_required":True,
                }} for i in range(25)
            ],
        },
    )


def test_all_gates_pass_admits_for_controlled_shadow():
    dataset, ann, cmp = evidence()
    # The safety validator requires the normal advisory contract; this test
    # uses a monkeypatch to isolate the admission gate's evidence binding.
    import nema_agora.admission as admission
    original=admission.validate_advisory_output
    admission.validate_advisory_output=lambda output: []
    try:
        decision=evaluate_admission(
            candidate=candidate(), dataset=dataset, annotation_readiness=ann,
            comparison=cmp, comparison_run_id="CMP-123",
            approver_id="coordinator-1", rationale="Benchmark and annotation evidence reviewed.",
        )
    finally:
        admission.validate_advisory_output=original
    assert decision.decision==ADMITTED
    assert all(decision.gates.values())


def test_metric_failure_blocks_admission():
    dataset, ann, cmp = evidence()
    cmp["adapters"][0]["category_accuracy"]=0.79
    import nema_agora.admission as admission
    original=admission.validate_advisory_output
    admission.validate_advisory_output=lambda output: []
    try:
        decision=evaluate_admission(
            candidate=candidate(), dataset=dataset, annotation_readiness=ann,
            comparison=cmp, comparison_run_id="CMP-123",
            approver_id="coordinator-1", rationale="Review.",
        )
    finally:
        admission.validate_advisory_output=original
    assert decision.decision==NOT_ADMITTED
    assert not decision.gates["category_accuracy"]


def test_kappa_and_unresolved_disagreement_block():
    dataset, ann, cmp=evidence()
    ann["minimum_category_kappa"]=0.79
    ann["unresolved_disagreements"]=["CASE-7"]
    import nema_agora.admission as admission
    original=admission.validate_advisory_output
    admission.validate_advisory_output=lambda output: []
    try:
        decision=evaluate_admission(
            candidate=candidate(), dataset=dataset, annotation_readiness=ann,
            comparison=cmp, comparison_run_id="CMP-123",
            approver_id="coordinator-1", rationale="Review.",
        )
    finally:
        admission.validate_advisory_output=original
    assert decision.decision==NOT_ADMITTED
    assert not decision.gates["annotation_category_kappa"]
    assert not decision.gates["all_disagreements_adjudicated"]


def test_evidence_binding_blocks_mismatched_dataset():
    dataset, ann, cmp=evidence()
    cmp["dataset"]["manifest_hash"]="different"
    import nema_agora.admission as admission
    original=admission.validate_advisory_output
    admission.validate_advisory_output=lambda output: []
    try:
        decision=evaluate_admission(
            candidate=candidate(), dataset=dataset, annotation_readiness=ann,
            comparison=cmp, comparison_run_id="CMP-123",
            approver_id="coordinator-1", rationale="Review.",
        )
    finally:
        admission.validate_advisory_output=original
    assert decision.decision==NOT_ADMITTED
    assert not decision.gates["comparison_run_match"]


def test_missing_approver_or_rationale_rejected():
    dataset, ann, cmp=evidence()
    with pytest.raises(ValueError):
        evaluate_admission(candidate=candidate(),dataset=dataset,
            annotation_readiness=ann,comparison=cmp,comparison_run_id="CMP-123",
            approver_id="",rationale="Review.")
    with pytest.raises(ValueError):
        evaluate_admission(candidate=candidate(),dataset=dataset,
            annotation_readiness=ann,comparison=cmp,comparison_run_id="CMP-123",
            approver_id="coordinator-1",rationale="")


def test_admission_store_persists(tmp_path):
    dataset, ann, cmp=evidence()
    import nema_agora.admission as admission
    original=admission.validate_advisory_output
    admission.validate_advisory_output=lambda output: []
    try:
        decision=evaluate_admission(
            candidate=candidate(), dataset=dataset, annotation_readiness=ann,
            comparison=cmp, comparison_run_id="CMP-123",
            approver_id="coordinator-1", rationale="Review.",
        )
    finally:
        admission.validate_advisory_output=original
    store=AdmissionStore(str(tmp_path/"nema.sqlite3"))
    store.save(decision, actor_id="coordinator-1")
    rows=store.list()
    assert rows[0]["admission_id"]==decision.admission_id
    assert rows[0]["result"]["decision"]==ADMITTED
    assert rows[0]["result"]["policy_version"]=="phase16-v1"


def test_annotation_status_cannot_override_failed_gate():
    dataset, ann, cmp = evidence()
    ann["gates"]["two_independent_annotators"] = False
    import nema_agora.admission as admission
    original = admission.validate_advisory_output
    admission.validate_advisory_output = lambda output: []
    try:
        decision = evaluate_admission(
            candidate=candidate(), dataset=dataset, annotation_readiness=ann,
            comparison=cmp, comparison_run_id="CMP-123",
            approver_id="coordinator-1", rationale="Review.",
        )
    finally:
        admission.validate_advisory_output = original
    assert decision.decision == NOT_ADMITTED
    assert not decision.gates["annotation_ready"]


def test_invalid_manifest_hash_blocks_admission():
    dataset, ann, cmp = evidence()
    dataset["manifest_hash"] = "not-a-sha256"
    import nema_agora.admission as admission
    original = admission.validate_advisory_output
    admission.validate_advisory_output = lambda output: []
    try:
        decision = evaluate_admission(
            candidate=candidate(), dataset=dataset, annotation_readiness=ann,
            comparison=cmp, comparison_run_id="CMP-123",
            approver_id="coordinator-1", rationale="Review.",
        )
    finally:
        admission.validate_advisory_output = original
    assert decision.decision == NOT_ADMITTED
    assert not decision.gates["frozen_dataset"]


def test_safety_evidence_must_match_exact_model_identity():
    dataset, ann, cmp = evidence()
    cmp["case_results"][0]["provider"] = "other-provider"
    import nema_agora.admission as admission
    original = admission.validate_advisory_output
    admission.validate_advisory_output = lambda output: []
    try:
        decision = evaluate_admission(
            candidate=candidate(), dataset=dataset, annotation_readiness=ann,
            comparison=cmp, comparison_run_id="CMP-123",
            approver_id="coordinator-1", rationale="Review.",
        )
    finally:
        admission.validate_advisory_output = original
    assert decision.decision == NOT_ADMITTED
    assert not decision.gates["human_review_contract"]
