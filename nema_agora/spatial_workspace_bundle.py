"""Phase 175 — validate spatial evidence lineage across bundled layers."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

POLICY_VERSION = "phase175-v1"
_REQUIRED_LAYERS = ("change_evidence", "quality_evidence", "candidate")


def _digest(value: Any) -> str:
    canonical = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _layer_digest_matches(layer: Mapping[str, Any]) -> bool:
    supplied = layer.get("fingerprint")
    if not isinstance(supplied, str):
        return False
    payload = dict(layer)
    payload.pop("fingerprint", None)
    try:
        return supplied == _digest(payload)
    except (TypeError, ValueError):
        return False


def _lineage_findings(layers: Mapping[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    change = layers.get("change_evidence")
    quality = layers.get("quality_evidence")
    candidate = layers.get("candidate")
    for name, layer in layers.items():
        if isinstance(layer, Mapping) and not _layer_digest_matches(layer):
            findings.append({"code": f"{name.upper()}_FINGERPRINT_MISMATCH"})
    if not all(isinstance(layer, Mapping) for layer in (change, quality, candidate)):
        return findings
    change_fp = change.get("fingerprint")
    if quality.get("change_fingerprint") != change_fp:
        findings.append({"code": "QUALITY_CHANGE_LINEAGE_MISMATCH"})
    if candidate.get("source_change_fingerprint") != quality.get("change_fingerprint"):
        findings.append({"code": "CANDIDATE_CHANGE_LINEAGE_MISMATCH"})
    quality_changes = quality.get("change")
    candidate_changes = candidate.get("change")
    if not isinstance(quality_changes, Mapping) or not isinstance(candidate_changes, Mapping):
        findings.append({"code": "CHANGE_VALUES_MISSING_FOR_LINEAGE_CHECK"})
    else:
        for index_name in ("NDVI", "NDWI_MCFEETERS"):
            q_value = quality_changes.get(index_name)
            c_value = candidate_changes.get(index_name)
            q_delta = q_value.get("delta") if isinstance(q_value, Mapping) else None
            c_delta = c_value.get("delta") if isinstance(c_value, Mapping) else None
            if (isinstance(q_delta, bool) or isinstance(c_delta, bool)
                    or not isinstance(q_delta, (int, float))
                    or not isinstance(c_delta, (int, float))
                    or q_delta != c_delta):
                findings.append({"code": f"{index_name}_DELTA_LINEAGE_MISMATCH"})
    return findings


def build_spatial_evidence_bundle(
    *,
    change_evidence: Mapping[str, Any],
    quality_evidence: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a deterministic bundle only when upstream fingerprints and lineage agree."""
    layers = {
        "change_evidence": change_evidence,
        "quality_evidence": quality_evidence,
        "candidate": candidate,
    }
    for name, layer in layers.items():
        if not isinstance(layer, Mapping):
            raise ValueError(f"{name} must be a mapping.")
    if change_evidence.get("state") != "CANDIDATE_CHANGE_EVIDENCE":
        raise ValueError("Change evidence is not eligible for bundling.")
    if quality_evidence.get("state") != "CANDIDATE_CHANGE_EVIDENCE":
        raise ValueError("Quality evidence is not eligible for bundling.")
    if candidate.get("state") not in {"CANDIDATE_CHANGE_DETECTED", "NO_CHANGE_DETECTED"}:
        raise ValueError("Candidate state is not eligible for bundling.")
    lineage_findings = _lineage_findings(layers)
    if lineage_findings:
        codes = ", ".join(item["code"] for item in lineage_findings)
        raise ValueError(f"Spatial evidence lineage validation failed: {codes}")

    bundle: dict[str, Any] = {
        "policy_version": POLICY_VERSION,
        "source_mode": "user_supplied_index_values",
        "live_provider_connected": False,
        "change_evidence": dict(change_evidence),
        "quality_evidence": dict(quality_evidence),
        "candidate": dict(candidate),
        "governance": {
            "human_review_required": True,
            "environmental_conclusion": None,
            "regulatory_conclusion": None,
            "automatic_enforcement": False,
            "official_submission": False,
        },
    }
    bundle["fingerprint"] = _digest(bundle)
    return bundle


def validate_spatial_evidence_bundle(bundle: Any) -> dict[str, Any]:
    """Validate outer integrity, upstream fingerprints, lineage and guardrails."""
    if not isinstance(bundle, Mapping):
        return {"valid": False, "findings": [{"code": "INVALID_BUNDLE_TYPE"}]}
    findings: list[dict[str, str]] = []
    required = (
        "policy_version", "source_mode", "live_provider_connected",
        *_REQUIRED_LAYERS, "governance", "fingerprint",
    )
    for key in required:
        if key not in bundle:
            findings.append({"code": f"MISSING_{key.upper()}"})
    if findings:
        return {"valid": False, "findings": findings}
    if bundle.get("policy_version") != POLICY_VERSION:
        findings.append({"code": "POLICY_VERSION_MISMATCH"})
    if bundle.get("source_mode") != "user_supplied_index_values":
        findings.append({"code": "UNEXPECTED_SOURCE_MODE"})
    if bundle.get("live_provider_connected") is not False:
        findings.append({"code": "UNVERIFIED_PROVIDER_CLAIM"})
    governance = bundle.get("governance")
    if not isinstance(governance, Mapping):
        findings.append({"code": "INVALID_GOVERNANCE_GUARDRAILS"})
    else:
        if governance.get("human_review_required") is not True:
            findings.append({"code": "HUMAN_REVIEW_NOT_REQUIRED"})
        if governance.get("environmental_conclusion") is not None:
            findings.append({"code": "ENVIRONMENTAL_CONCLUSION_MUST_REMAIN_UNSET"})
        if governance.get("regulatory_conclusion") is not None:
            findings.append({"code": "REGULATORY_CONCLUSION_MUST_REMAIN_UNSET"})
        if governance.get("automatic_enforcement") is not False:
            findings.append({"code": "AUTOMATIC_ENFORCEMENT_MUST_REMAIN_DISABLED"})
        if governance.get("official_submission") is not False:
            findings.append({"code": "OFFICIAL_SUBMISSION_MUST_REMAIN_DISABLED"})
    layers = {name: bundle.get(name) for name in _REQUIRED_LAYERS}
    for name, layer in layers.items():
        if not isinstance(layer, Mapping):
            findings.append({"code": f"INVALID_{name.upper()}"})
    findings.extend(_lineage_findings(layers))
    try:
        payload = dict(bundle)
        supplied = payload.pop("fingerprint")
        if not isinstance(supplied, str) or supplied != _digest(payload):
            findings.append({"code": "BUNDLE_FINGERPRINT_MISMATCH"})
    except (TypeError, ValueError):
        findings.append({"code": "BUNDLE_NOT_CANONICAL_JSON"})
    return {
        "valid": not findings,
        "fingerprint": bundle.get("fingerprint"),
        "findings": findings,
    }
