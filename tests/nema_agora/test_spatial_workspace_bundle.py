from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from nema_agora.spatial_workspace_bundle import (
    build_spatial_evidence_bundle,
    validate_spatial_evidence_bundle,
)


def _seal(payload):
    value = dict(payload)
    value["fingerprint"] = hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()
    return value


def _layers():
    change = _seal({
        "state": "CANDIDATE_CHANGE_EVIDENCE",
        "change": {"NDVI": {"delta": -0.2}, "NDWI_MCFEETERS": {"delta": 0.1}},
    })
    quality = _seal({
        "state": "CANDIDATE_CHANGE_EVIDENCE",
        "change_fingerprint": change["fingerprint"],
        "change": {"NDVI": {"delta": -0.2}, "NDWI_MCFEETERS": {"delta": 0.1}},
    })
    candidate = _seal({
        "state": "CANDIDATE_CHANGE_DETECTED",
        "candidate_id": "CHANGE-DEMO",
        "source_change_fingerprint": quality["change_fingerprint"],
        "change": {"NDVI": {"delta": -0.2}, "NDWI_MCFEETERS": {"delta": 0.1}},
    })
    return change, quality, candidate


def _build():
    change, quality, candidate = _layers()
    return build_spatial_evidence_bundle(
        change_evidence=change, quality_evidence=quality, candidate=candidate
    )


def test_bundle_is_fingerprint_bound_and_validates():
    bundle = _build()
    result = validate_spatial_evidence_bundle(bundle)
    assert result["valid"] is True
    assert len(result["fingerprint"]) == 64
    assert bundle["governance"]["human_review_required"] is True
    assert bundle["governance"]["environmental_conclusion"] is None
    assert bundle["live_provider_connected"] is False


def test_bundle_fingerprint_is_deterministic_for_same_inputs():
    assert _build()["fingerprint"] == _build()["fingerprint"]


def test_bundle_detects_tampered_candidate_after_creation():
    tampered = deepcopy(_build())
    tampered["candidate"]["candidate_id"] = "CHANGE-TAMPERED"
    result = validate_spatial_evidence_bundle(tampered)
    assert result["valid"] is False
    assert {"code": "BUNDLE_FINGERPRINT_MISMATCH"} in result["findings"]
    assert {"code": "CANDIDATE_FINGERPRINT_MISMATCH"} in result["findings"]


def test_bundle_rejects_false_provider_and_governance_claims():
    bundle = _build()
    bundle["live_provider_connected"] = True
    result = validate_spatial_evidence_bundle(bundle)
    assert result["valid"] is False
    assert {"code": "UNVERIFIED_PROVIDER_CLAIM"} in result["findings"]
    assert {"code": "BUNDLE_FINGERPRINT_MISMATCH"} in result["findings"]


def test_bundle_rejects_invalid_candidate_state():
    change, quality, candidate = _layers()
    candidate["state"] = "CONTROL_REQUIRED"
    candidate = _seal({k: v for k, v in candidate.items() if k != "fingerprint"})
    try:
        build_spatial_evidence_bundle(
            change_evidence=change, quality_evidence=quality, candidate=candidate
        )
    except ValueError as exc:
        assert "Candidate state" in str(exc)
    else:
        raise AssertionError("Invalid candidate state should not be bundled.")


def test_bundle_rejects_mismatched_upstream_fingerprint():
    change, quality, candidate = _layers()
    quality["change_fingerprint"] = "f" * 64
    quality = _seal({k: v for k, v in quality.items() if k != "fingerprint"})
    try:
        build_spatial_evidence_bundle(
            change_evidence=change, quality_evidence=quality, candidate=candidate
        )
    except ValueError as exc:
        assert "QUALITY_CHANGE_LINEAGE_MISMATCH" in str(exc)
    else:
        raise AssertionError("Mismatched upstream lineage should be rejected.")


def test_bundle_rejects_changed_delta_between_quality_and_candidate():
    change, quality, candidate = _layers()
    candidate["change"]["NDVI"]["delta"] = 0.4
    candidate = _seal({k: v for k, v in candidate.items() if k != "fingerprint"})
    try:
        build_spatial_evidence_bundle(
            change_evidence=change, quality_evidence=quality, candidate=candidate
        )
    except ValueError as exc:
        assert "NDVI_DELTA_LINEAGE_MISMATCH" in str(exc)
    else:
        raise AssertionError("Divergent index deltas should be rejected.")


def test_validator_rejects_ineligible_states_even_if_all_fingerprints_are_recomputed():
    bundle = _build()
    candidate_payload = dict(bundle["candidate"])
    candidate_payload.pop("fingerprint")
    candidate_payload["state"] = "CONTROL_REQUIRED"
    bundle["candidate"] = _seal(candidate_payload)
    outer_payload = dict(bundle)
    outer_payload.pop("fingerprint")
    bundle["fingerprint"] = hashlib.sha256(
        json.dumps(outer_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()

    result = validate_spatial_evidence_bundle(bundle)
    assert result["valid"] is False
    assert {"code": "CANDIDATE_STATE_NOT_ELIGIBLE"} in result["findings"]
