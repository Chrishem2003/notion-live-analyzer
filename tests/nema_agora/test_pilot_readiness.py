from nema_agora.pilot_readiness import (
    NOT_READY,
    READY,
    evaluate_pilot_readiness,
)

def _inputs():
    evidence = {
        "domains": {
            "impact": {"count": 10},
            "accessibility": {"count": 12},
            "provenance": {"count": 10},
            "field_evaluation": {"count": 11},
            "human_governance": {"count": 10},
        }
    }
    shadow = {
        "total_runs": 10,
        "error_rate": 0.0,
        "status": "HEALTHY_WITHIN_SHADOW_POLICY",
    }
    manifest = {"manifest_id": "m-1", "git_revision": "abc123"}
    governance = {
        "human_review_required": True,
        "explicit_lifecycle_control": True,
        "autonomous_state_change_blocked": True,
    }
    return evidence, shadow, manifest, governance

def test_ready_requires_all_gates():
    evidence, shadow, manifest, governance = _inputs()
    result = evaluate_pilot_readiness(
        evidence_scorecard=evidence,
        shadow_monitoring=shadow,
        reproducibility_manifest=manifest,
        human_governance=governance,
    )
    assert result.decision == READY
    assert all(result.gates.values())
    assert len(result.readiness_id) == 64

def test_thin_evidence_blocks_readiness():
    evidence, shadow, manifest, governance = _inputs()
    evidence["domains"]["impact"]["count"] = 9
    result = evaluate_pilot_readiness(
        evidence_scorecard=evidence,
        shadow_monitoring=shadow,
        reproducibility_manifest=manifest,
        human_governance=governance,
    )
    assert result.decision == NOT_READY
    assert "EVIDENCE_COVERAGE_INSUFFICIENT" in result.warnings

def test_shadow_error_rate_is_conservative():
    evidence, shadow, manifest, governance = _inputs()
    shadow["error_rate"] = 0.051
    result = evaluate_pilot_readiness(
        evidence_scorecard=evidence,
        shadow_monitoring=shadow,
        reproducibility_manifest=manifest,
        human_governance=governance,
    )
    assert result.decision == NOT_READY

def test_missing_manifest_blocks_readiness():
    evidence, shadow, _, governance = _inputs()
    result = evaluate_pilot_readiness(
        evidence_scorecard=evidence,
        shadow_monitoring=shadow,
        reproducibility_manifest=None,
        human_governance=governance,
    )
    assert result.decision == NOT_READY
    assert "REPRODUCIBILITY_MANIFEST_MISSING_OR_INCOMPLETE" in result.warnings

def test_autonomous_state_change_blocks_readiness():
    evidence, shadow, manifest, governance = _inputs()
    governance["autonomous_state_change_blocked"] = False
    result = evaluate_pilot_readiness(
        evidence_scorecard=evidence,
        shadow_monitoring=shadow,
        reproducibility_manifest=manifest,
        human_governance=governance,
    )
    assert result.decision == NOT_READY
