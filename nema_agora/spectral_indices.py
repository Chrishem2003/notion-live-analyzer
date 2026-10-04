"""Phase 58 — NEMA-AGORA transparent NDVI / McFeeters NDWI analytics."""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Mapping

POLICY_VERSION = "phase58-v1"
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
INDEX_NAMES = {"NDVI", "NDWI_MCFEETERS"}
BAND_REQUIREMENTS = {"NDVI": ("B04", "B08"), "NDWI_MCFEETERS": ("B03", "B08")}


def fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
    ).hexdigest()


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


def _valid_reflectance(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and 0.0 <= float(value) <= 1.0
    )


def _index(numerator: float, denominator: float) -> float:
    if denominator == 0:
        raise ValueError("Spectral-index denominator cannot be zero.")
    value = numerator / denominator
    if not math.isfinite(value) or not -1.0 <= value <= 1.0:
        raise ValueError("Spectral-index result is outside the expected [-1, 1] range.")
    return value


def calculate_ndvi(*, red: float, nir: float) -> float:
    """NDVI = (NIR - RED) / (NIR + RED), using normalized reflectance [0, 1]."""
    if not _valid_reflectance(red) or not _valid_reflectance(nir):
        raise ValueError("NDVI inputs must be finite normalized reflectance values in [0, 1].")
    return _index(float(nir) - float(red), float(nir) + float(red))


def calculate_ndwi(*, green: float, nir: float) -> float:
    """McFeeters NDWI = (GREEN - NIR) / (GREEN + NIR), using normalized reflectance [0, 1]."""
    if not _valid_reflectance(green) or not _valid_reflectance(nir):
        raise ValueError("NDWI inputs must be finite normalized reflectance values in [0, 1].")
    return _index(float(green) - float(nir), float(green) + float(nir))


def validate_spectral_inputs(
    *, scene_id: Any, band_values: Mapping[str, Any], index_names: Any = ("NDVI", "NDWI_MCFEETERS")
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    if not _valid_id(scene_id):
        findings.append({"code": "INVALID_SCENE_ID"})
    if not isinstance(index_names, (list, tuple)) or not index_names:
        findings.append({"code": "INVALID_INDEX_SELECTION"})
        requested: list[Any] = []
    else:
        requested = list(index_names)
        for name in requested:
            if name not in INDEX_NAMES:
                findings.append({"code": "UNSUPPORTED_INDEX"})
    if not isinstance(band_values, Mapping):
        findings.append({"code": "INVALID_BAND_VALUES"})
        bands: Mapping[str, Any] = {}
    else:
        bands = band_values
        needed = {band for name in requested if name in BAND_REQUIREMENTS for band in BAND_REQUIREMENTS[name]}
        for band in sorted(needed):
            if band not in bands:
                findings.append({"code": f"MISSING_{band}"})
            elif not _valid_reflectance(bands[band]):
                findings.append({"code": f"INVALID_{band}_REFLECTANCE"})
    return {
        "policy_version": POLICY_VERSION,
        "state": "CONTROL_REQUIRED" if findings else "VALID",
        "findings": findings,
    }


def spectral_index_evidence(
    *, scene_id: str, band_values: Mapping[str, Any], index_names: tuple[str, ...] = ("NDVI", "NDWI_MCFEETERS")
) -> dict[str, Any]:
    validation = validate_spectral_inputs(scene_id=scene_id, band_values=band_values, index_names=index_names)
    if validation["state"] != "VALID":
        return {
            "policy_version": POLICY_VERSION,
            "state": "CONTROL_REQUIRED",
            "findings": validation["findings"],
        }

    values: dict[str, float] = {}
    formulas: dict[str, str] = {}
    for name in index_names:
        if name == "NDVI":
            values[name] = calculate_ndvi(red=float(band_values["B04"]), nir=float(band_values["B08"]))
            formulas[name] = "(B08 - B04) / (B08 + B04)"
        elif name == "NDWI_MCFEETERS":
            values[name] = calculate_ndwi(green=float(band_values["B03"]), nir=float(band_values["B08"]))
            formulas[name] = "(B03 - B08) / (B03 + B08)"

    payload = {
        "policy_version": POLICY_VERSION,
        "state": "VALID",
        "scene_id": scene_id,
        "index_values": values,
        "formulas": formulas,
        "source_bands": {name: list(BAND_REQUIREMENTS[name]) for name in index_names},
        "quality": {
            "input_scale": "normalized_reflectance_0_to_1",
            "finite_inputs": True,
            "denominator_nonzero": True,
            "expected_range": [-1.0, 1.0],
        },
    }
    payload["fingerprint"] = fingerprint(payload)
    return payload
