"""Reference-label review gate for NEMA-AGORA offline evaluation.

Checks declared review metadata and traceability only. It cannot authenticate
reviewers, evidence assets, label correctness, or independence from model tuning.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

_SCHEMA = "nema-reference-review-v1"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


class ReferenceReviewError(ValueError):
    """Raised when a reference review package is incomplete or inconsistent."""


def validate_reference_review_package(package: Mapping[str, Any]) -> dict[str, Any]:
    """Validate two-reviewer evidence declarations and return a stable digest."""
    if not isinstance(package, Mapping):
        raise ReferenceReviewError("package must be an object.")
    for field in ("reference_set_id", "reference_set_version", "split", "units"):
        if field not in package:
            raise ReferenceReviewError(f"missing required field: {field}")
    for field in ("reference_set_id", "reference_set_version"):
        value = package[field]
        if not isinstance(value, str) or not _ID.fullmatch(value.strip()):
            raise ReferenceReviewError(f"{field} must be a valid non-empty identifier.")
    if package["split"] not in {"development", "validation", "holdout"}:
        raise ReferenceReviewError("split must be development, validation, or holdout.")
    units = package["units"]
    if not isinstance(units, Sequence) or isinstance(units, (str, bytes)) or not units:
        raise ReferenceReviewError("units must be a non-empty array.")
    seen: set[str] = set()
    normalized_units = []
    for index, unit in enumerate(units):
        if not isinstance(unit, Mapping):
            raise ReferenceReviewError(f"units[{index}] must be an object.")
        unit_id = unit.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id.strip():
            raise ReferenceReviewError(f"units[{index}].unit_id must be non-empty.")
        unit_id = unit_id.strip()
        if unit_id in seen:
            raise ReferenceReviewError(f"duplicate unit_id: {unit_id}")
        seen.add(unit_id)
        if not isinstance(unit.get("reference_change"), bool):
            raise ReferenceReviewError(f"units[{index}].reference_change must be boolean.")
        reviewers = unit.get("reviewer_ids")
        if not isinstance(reviewers, list) or len(reviewers) < 2 or any(
            not isinstance(r, str) or not r.strip() for r in reviewers
        ):
            raise ReferenceReviewError(f"units[{index}].reviewer_ids must list at least two named reviewers.")
        clean_reviewers = [r.strip() for r in reviewers]
        if len(set(clean_reviewers)) != len(clean_reviewers):
            raise ReferenceReviewError(f"units[{index}].reviewer_ids must be distinct.")
        reviewed_at = unit.get("reviewed_at")
        if not isinstance(reviewed_at, str):
            raise ReferenceReviewError(f"units[{index}].reviewed_at must be ISO-8601 with timezone.")
        try:
            parsed_at = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ReferenceReviewError(f"units[{index}].reviewed_at must be ISO-8601 with timezone.") from exc
        if parsed_at.tzinfo is None or parsed_at.utcoffset() is None:
            raise ReferenceReviewError(f"units[{index}].reviewed_at must include a timezone.")
        evidence_refs = unit.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs or any(
            not isinstance(ref, str) or not ref.strip() for ref in evidence_refs
        ):
            raise ReferenceReviewError(f"units[{index}].evidence_refs must contain at least one evidence reference.")
        if unit.get("reviewers_blinded_to_candidate") is not True:
            raise ReferenceReviewError(f"units[{index}] must declare reviewers_blinded_to_candidate=true.")
        normalized_units.append({
            "unit_id": unit_id,
            "reference_change": unit["reference_change"],
            "reviewer_ids": clean_reviewers,
            "reviewed_at": reviewed_at,
            "evidence_refs": [ref.strip() for ref in evidence_refs],
            "reviewers_blinded_to_candidate": True,
        })
    canonical = {
        "schema_version": _SCHEMA,
        "reference_set_id": package["reference_set_id"].strip(),
        "reference_set_version": package["reference_set_version"].strip(),
        "split": package["split"],
        "units": normalized_units,
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return {
        "schema_version": _SCHEMA,
        "state": "REVIEW_METADATA_COMPLETE_NOT_AUTHENTICATED",
        "reference_set_id": canonical["reference_set_id"],
        "reference_set_version": canonical["reference_set_version"],
        "split": canonical["split"],
        "unit_count": len(normalized_units),
        "reviewed_unit_count": len(normalized_units),
        "package_sha256": hashlib.sha256(encoded).hexdigest(),
        "limitations": [
            "Reviewer IDs and evidence references are declarations; this validator does not authenticate people or open evidence assets.",
            "Two declared reviewers and blinding do not prove actual independence or correct labels.",
            "Holdout split is a declaration; confirm no tuning, threshold selection or model development used these units.",
            "Reference labels should be adjudicated when reviewers disagree; this package schema does not infer disagreement from missing data.",
        ],
        "canonical_package": canonical,
    }
