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
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError):
        return False
    return math.isfinite(number) and -1.0 <= number <= 1.0


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse an ISO 8601 timestamp only when it has an explicit UTC offset."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _valid_timestamp(value: Any) -> bool:
    return _parse_timestamp(value) is not None


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
    baseline_parsed = _parse_timestamp(baseline_acquired_at)
    comparison_parsed = _parse_timestamp(comparison_acquired_at)
    if baseline_parsed is not None and comparison_parsed is not None:
        # Convert both instants to UTC before subtraction so differing offsets
        # cannot change the elapsed-time result or trigger naive/aware errors.
        gap_days = (
            comparison_parsed.astimezone().timestamp()
            - baseline_parsed.astimezone().timestamp()
        ) / 86400
        if gap_days <= 0:
            findings.append({"code": "COMPARISON_NOT_AFTER_BASELINE"})
        if (not isinstance(min_temporal_gap_days, (int, float))
                or isinstance(min_temporal_gap_days, bool)
                or not math.isfinite(float(min_temporal_gap_days))
                or float(min_temporal_gap_days) < 0):
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
    delta = round(float(comparison_value) - float(baseline_value), 12)
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
