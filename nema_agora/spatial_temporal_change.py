"""Phase 59 — NEMA-AGORA spatial/temporal change evidence."""
from __future__ import annotations
import hashlib, json, math, re
from datetime import datetime
from typing import Any, Mapping

POLICY_VERSION = "phase59-v1"
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()).hexdigest()


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


def _valid_value(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) and -1.0 <= float(value) <= 1.0


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_change_inputs(*, baseline_scene_id: Any, comparison_scene_id: Any,
                           baseline_acquired_at: Any, comparison_acquired_at: Any,
                           baseline_indices: Mapping[str, Any], comparison_indices: Mapping[str, Any],
                           min_temporal_gap_days: float = 0.0) -> dict[str, Any]:
    findings = []
    if not _valid_id(baseline_scene_id): findings.append({"code": "INVALID_BASELINE_SCENE_ID"})
    if not _valid_id(comparison_scene_id): findings.append({"code": "INVALID_COMPARISON_SCENE_ID"})
    if baseline_scene_id == comparison_scene_id and _valid_id(baseline_scene_id):
        findings.append({"code": "BASELINE_AND_COMPARISON_SCENE_IDENTICAL"})
    if not _valid_timestamp(baseline_acquired_at): findings.append({"code": "INVALID_BASELINE_TIMESTAMP"})
    if not _valid_timestamp(comparison_acquired_at): findings.append({"code": "INVALID_COMPARISON_TIMESTAMP"})
    if _valid_timestamp(baseline_acquired_at) and _valid_timestamp(comparison_acquired_at):
        b = datetime.fromisoformat(str(baseline_acquired_at).replace("Z", "+00:00"))
        c = datetime.fromisoformat(str(comparison_acquired_at).replace("Z", "+00:00"))
        gap_days = (c - b).total_seconds() / 86400
        if gap_days <= 0: findings.append({"code": "COMPARISON_NOT_AFTER_BASELINE"})
        if not isinstance(min_temporal_gap_days, (int, float)) or isinstance(min_temporal_gap_days, bool) or not math.isfinite(float(min_temporal_gap_days)) or float(min_temporal_gap_days) < 0:
            findings.append({"code": "INVALID_MIN_TEMPORAL_GAP"})
        elif gap_days < float(min_temporal_gap_days):
            findings.append({"code": "TEMPORAL_GAP_BELOW_MINIMUM"})
    for label, values in (("BASELINE", baseline_indices), ("COMPARISON", comparison_indices)):
        if not isinstance(values, Mapping):
            findings.append({"code": f"INVALID_{label}_INDICES"})
            continue
        for name in ("NDVI", "NDWI_MCFEETERS"):
            if name not in values: findings.append({"code": f"MISSING_{label}_{name}"})
            elif not _valid_value(values[name]): findings.append({"code": f"INVALID_{label}_{name}"})
    return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED" if findings else "VALID", "findings": findings}


def calculate_change(baseline_value: float, comparison_value: float) -> dict[str, float]:
    if not _valid_value(baseline_value) or not _valid_value(comparison_value):
        raise ValueError("Index values must be finite values in [-1, 1].")
    delta = float(comparison_value) - float(baseline_value)
    return {"baseline": float(baseline_value), "comparison": float(comparison_value), "delta": delta, "absolute_delta": abs(delta)}


def spatial_temporal_change_evidence(*, baseline_scene_id: str, comparison_scene_id: str,
                                     baseline_acquired_at: str, comparison_acquired_at: str,
                                     baseline_indices: Mapping[str, Any], comparison_indices: Mapping[str, Any],
                                     min_temporal_gap_days: float = 0.0, quality: Mapping[str, Any] | None = None) -> dict[str, Any]:
    validation = validate_change_inputs(
        baseline_scene_id=baseline_scene_id, comparison_scene_id=comparison_scene_id,
        baseline_acquired_at=baseline_acquired_at, comparison_acquired_at=comparison_acquired_at,
        baseline_indices=baseline_indices, comparison_indices=comparison_indices,
        min_temporal_gap_days=min_temporal_gap_days)
    if validation["state"] != "VALID":
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED", "findings": validation["findings"]}
    changes = {name: calculate_change(baseline_indices[name], comparison_indices[name])
               for name in ("NDVI", "NDWI_MCFEETERS")}
    payload = {
        "policy_version": POLICY_VERSION, "state": "CANDIDATE_CHANGE_EVIDENCE",
        "baseline": {"scene_id": baseline_scene_id, "acquired_at": baseline_acquired_at, "indices": dict(baseline_indices)},
        "comparison": {"scene_id": comparison_scene_id, "acquired_at": comparison_acquired_at, "indices": dict(comparison_indices)},
        "change": changes, "quality": dict(quality or {}),
        "interpretation": {"status": "HUMAN_REVIEW_REQUIRED", "environmental_conclusion": None, "regulatory_conclusion": None},
    }
    payload["fingerprint"] = fingerprint(payload)
    return payload
