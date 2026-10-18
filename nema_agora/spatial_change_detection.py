"""Phase 61 — NEMA-AGORA broader spatial change candidate detection."""
from __future__ import annotations
import hashlib, json, math, re
from typing import Any, Mapping

POLICY_VERSION = "phase61-v1"
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_RULES = {"ANY", "ALL", "WEIGHTED"}

def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()).hexdigest()

def _valid_id(v: Any) -> bool:
    return isinstance(v, str) and bool(_ID_RE.fullmatch(v))

def _finite(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))

def _threshold(v: Any) -> bool:
    return _finite(v) and 0.0 <= float(v) <= 2.0

def _weight(v: Any) -> bool:
    return _finite(v) and 0.0 <= float(v) <= 1.0

def _extract(change: Mapping[str, Any], name: str) -> float | None:
    try:
        value = change["change"][name]["delta"]
    except (KeyError, TypeError):
        return None
    return float(value) if _finite(value) and -2.0 <= float(value) <= 2.0 else None

def validate_detection_policy(*, min_abs_ndvi_delta: Any, min_abs_ndwi_delta: Any,
                              rule_mode: Any = "ANY", ndvi_weight: Any = 0.5,
                              ndwi_weight: Any = 0.5, min_weighted_score: Any = 0.5) -> dict[str, Any]:
    findings = []
    for code, value in (("INVALID_MIN_ABS_NDVI_DELTA", min_abs_ndvi_delta),
                        ("INVALID_MIN_ABS_NDWI_DELTA", min_abs_ndwi_delta)):
        if not _threshold(value): findings.append({"code": code})
    if rule_mode not in _RULES: findings.append({"code": "INVALID_RULE_MODE"})
    for code, value in (("INVALID_NDVI_WEIGHT", ndvi_weight), ("INVALID_NDWI_WEIGHT", ndwi_weight),
                        ("INVALID_MIN_WEIGHTED_SCORE", min_weighted_score)):
        if not _weight(value): findings.append({"code": code})
    if _weight(ndvi_weight) and _weight(ndwi_weight) and float(ndvi_weight) + float(ndwi_weight) <= 0:
        findings.append({"code": "WEIGHTS_SUM_TO_ZERO"})
    return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED" if findings else "VALID", "findings": findings}

def detect_candidate(*, quality_evidence: Mapping[str, Any], min_abs_ndvi_delta: float,
                     min_abs_ndwi_delta: float, rule_mode: str = "ANY",
                     ndvi_weight: float = 0.5, ndwi_weight: float = 0.5,
                     min_weighted_score: float = 0.5) -> dict[str, Any]:
    if not isinstance(quality_evidence, Mapping):
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED",
                "findings": [{"code": "INVALID_QUALITY_EVIDENCE"}]}
    findings = []
    if quality_evidence.get("state") != "CANDIDATE_CHANGE_EVIDENCE":
        findings.append({"code": "QUALITY_EVIDENCE_NOT_APPROVED"})
    required = ("change_fingerprint", "spatial", "quality", "uncertainty", "interpretation")
    for key in required:
        if key not in quality_evidence: findings.append({"code": f"MISSING_QUALITY_FIELD_{key.upper()}"})
    policy = validate_detection_policy(min_abs_ndvi_delta=min_abs_ndvi_delta,
        min_abs_ndwi_delta=min_abs_ndwi_delta, rule_mode=rule_mode,
        ndvi_weight=ndvi_weight, ndwi_weight=ndwi_weight, min_weighted_score=min_weighted_score)
    findings.extend(policy["findings"])
    ndvi = _extract(quality_evidence, "NDVI")
    ndwi = _extract(quality_evidence, "NDWI_MCFEETERS")
    if ndvi is None: findings.append({"code": "MISSING_OR_INVALID_NDVI_DELTA"})
    if ndwi is None: findings.append({"code": "MISSING_OR_INVALID_NDWI_DELTA"})
    if findings:
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED", "findings": findings}
    abs_ndvi, abs_ndwi = abs(ndvi), abs(ndwi)
    ndvi_hit, ndwi_hit = abs_ndvi >= float(min_abs_ndvi_delta), abs_ndwi >= float(min_abs_ndwi_delta)
    normalized_weight = float(ndvi_weight) + float(ndwi_weight)
    weighted_score = ((abs_ndvi / max(float(min_abs_ndvi_delta), 1e-12)) * float(ndvi_weight)
                      + (abs_ndwi / max(float(min_abs_ndwi_delta), 1e-12)) * float(ndwi_weight)) / normalized_weight
    if rule_mode == "ANY": detected = ndvi_hit or ndwi_hit
    elif rule_mode == "ALL": detected = ndvi_hit and ndwi_hit
    else: detected = weighted_score >= float(min_weighted_score)
    reasons = []
    if ndvi_hit: reasons.append("NDVI_CHANGE_THRESHOLD_MET")
    if ndwi_hit: reasons.append("NDWI_CHANGE_THRESHOLD_MET")
    if ndvi_hit and ndwi_hit: reasons.append("COMBINED_CHANGE_SIGNAL")
    state = "CANDIDATE_CHANGE_DETECTED" if detected else "NO_CHANGE_DETECTED"
    payload = {
        "policy_version": POLICY_VERSION, "state": state,
        "candidate_id": None,
        "source_change_fingerprint": quality_evidence["change_fingerprint"],
        "spatial": dict(quality_evidence["spatial"]),
        "change": {"NDVI": {"delta": ndvi, "absolute_delta": abs_ndvi, "threshold": float(min_abs_ndvi_delta)},
                   "NDWI_MCFEETERS": {"delta": ndwi, "absolute_delta": abs_ndwi, "threshold": float(min_abs_ndwi_delta)}},
        "detection_policy": {"rule_mode": rule_mode, "ndvi_weight": float(ndvi_weight),
                             "ndwi_weight": float(ndwi_weight), "min_weighted_score": float(min_weighted_score),
                             "weighted_score": weighted_score},
        "reason_codes": reasons,
        "quality": dict(quality_evidence["quality"]),
        "uncertainty": dict(quality_evidence["uncertainty"]),
        "interpretation": {"status": "HUMAN_REVIEW_REQUIRED" if detected else "NO_REVIEW_TRIGGERED",
                           "environmental_conclusion": None, "regulatory_conclusion": None,
                           "violation": None, "enforcement_action": None},
    }
    payload["candidate_id"] = "CHANGE-" + fingerprint({
        "source_change_fingerprint": payload["source_change_fingerprint"],
        "spatial": payload["spatial"], "change": payload["change"],
        "detection_policy": payload["detection_policy"], "reason_codes": reasons,
    })[:24]
    payload["fingerprint"] = fingerprint(payload)
    return payload
