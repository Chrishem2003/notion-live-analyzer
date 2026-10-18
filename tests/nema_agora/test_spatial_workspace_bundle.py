from __future__ import annotations

from copy import deepcopy

from nema_agora.spatial_workspace_bundle import (
    build_spatial_evidence_bundle,
    validate_spatial_evidence_bundle,
)


def _layers():
    change = {
        "state": "CANDIDATE_CHANGE_EVIDENCE",
        "fingerprint": "a" * 64,
        "change": {"NDVI": {"delta": -0.2}, "NDWI_MCFEETERS": {"delta": 0.1}},
    }
    quality = {
        "state": "CANDIDATE_CHANGE_EVIDENCE",
        "fingerprint": "b" * 64,
        "change_fingerprint": change["fingerprint"],
    }
    candidate = {
        "state": "CANDIDATE_CHANGE_DETECTED",
        "fingerprint": "c" * 64,
        "candidate_id": "CHANGE-DEMO",
    }
    return change, quality, candidate


def test_bundle_is_fingerprint_bound_and_validates():
    change, quality, candidate = _layers()
    bundle = build_spatial_evidence_bundle(
        change_evidence=change, quality_evidence=quality, candidate=candidate
    )

    result = validate_spatial_evidence_bundle(bundle)

    assert result["valid"] is True
    assert len(result["fingerprint"]) == 64
    assert bundle["governance"]["human_review_required"] is True
    assert bundle["governance"]["environmental_conclusion"] is None
    assert bundle["live_provider_connected"] is False


def test_bundle_fingerprint_is_deterministic_for_same_inputs():
    change, quality, candidate = _layers()
    first = build_spatial_evidence_bundle(
        change_evidence=change, quality_evidence=quality, candidate=candidate
    )
    second = build_spatial_evidence_bundle(
        change_evidence=change, quality_evidence=quality, candidate=candidate
    )

    assert first["fingerprint"] == second["fingerprint"]


def test_bundle_detects_tampered_candidate_after_creation():
    change, quality, candidate = _layers()
    bundle = build_spatial_evidence_bundle(
        change_evidence=change, quality_evidence=quality, candidate=candidate
    )
    tampered = deepcopy(bundle)
    tampered["candidate"]["candidate_id"] = "CHANGE-TAMPERED"

    result = validate_spatial_evidence_bundle(tampered)

    assert result["valid"] is False
    assert {"code": "BUNDLE_FINGERPRINT_MISMATCH"} in result["findings"]


def test_bundle_rejects_false_provider_and_governance_claims():
    change, quality, candidate = _layers()
    bundle = build_spatial_evidence_bundle(
        change_evidence=change, quality_evidence=quality, candidate=candidate
    )
    bundle["live_provider_connected"] = True

    result = validate_spatial_evidence_bundle(bundle)

    assert result["valid"] is False
    assert {"code": "UNVERIFIED_PROVIDER_CLAIM"} in result["findings"]
    assert {"code": "BUNDLE_FINGERPRINT_MISMATCH"} in result["findings"]


def test_bundle_rejects_invalid_candidate_state():
    change, quality, candidate = _layers()
    candidate["state"] = "CONTROL_REQUIRED"

    try:
        build_spatial_evidence_bundle(
            change_evidence=change, quality_evidence=quality, candidate=candidate
        )
    except ValueError as exc:
        assert "Candidate state" in str(exc)
    else:
        raise AssertionError("Invalid candidate state should not be bundled.")
