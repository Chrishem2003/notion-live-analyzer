"""Dataset split leakage audit for NEMA-AGORA evaluation manifests.

This checks declared unit IDs only; it cannot prove that related locations,
dates, tiles, source imagery, or derived features are independent.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence


class SplitAuditError(ValueError):
    """Raised when split manifests are malformed or have declared unit overlap."""


_SPLITS = {"development", "validation", "holdout"}
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


def audit_dataset_splits(manifests: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Audit unit-ID disjointness across development, validation and holdout manifests."""
    if not isinstance(manifests, Sequence) or isinstance(manifests, (str, bytes)) or not manifests:
        raise SplitAuditError("manifests must be a non-empty array.")
    by_set: dict[str, dict[str, set[str]]] = {}
    versions: dict[str, set[str]] = {}
    canonical_manifests = []
    seen_manifest_keys: set[tuple[str, str, str]] = set()

    for index, manifest in enumerate(manifests):
        if not isinstance(manifest, Mapping):
            raise SplitAuditError(f"manifests[{index}] must be an object.")
        set_id = manifest.get("reference_set_id")
        version = manifest.get("reference_set_version")
        split = manifest.get("split")
        units = manifest.get("unit_ids")
        for field, value in (("reference_set_id", set_id), ("reference_set_version", version)):
            if not isinstance(value, str) or not _ID.fullmatch(value.strip()):
                raise SplitAuditError(f"manifests[{index}].{field} must be a valid identifier.")
        set_id, version = set_id.strip(), version.strip()
        if split not in _SPLITS:
            raise SplitAuditError(f"manifests[{index}].split must be development, validation, or holdout.")
        if not isinstance(units, list) or not units:
            raise SplitAuditError(f"manifests[{index}].unit_ids must be a non-empty array.")
        key = (set_id, version, split)
        if key in seen_manifest_keys:
            raise SplitAuditError(f"duplicate manifest for reference set {set_id} version {version} split {split}.")
        seen_manifest_keys.add(key)
        clean_units = []
        local_seen = set()
        for unit_index, unit_id in enumerate(units):
            if not isinstance(unit_id, str) or not _ID.fullmatch(unit_id.strip()):
                raise SplitAuditError(f"manifests[{index}].unit_ids[{unit_index}] must be a valid identifier.")
            unit_id = unit_id.strip()
            if unit_id in local_seen:
                raise SplitAuditError(f"duplicate unit ID {unit_id} within {set_id}/{split}.")
            local_seen.add(unit_id)
            clean_units.append(unit_id)
        by_set.setdefault(set_id, {name: set() for name in _SPLITS})[split].update(clean_units)
        versions.setdefault(set_id, set()).add(version)
        canonical_manifests.append({
            "reference_set_id": set_id,
            "reference_set_version": version,
            "split": split,
            "unit_ids": sorted(clean_units),
        })

    overlaps = []
    for set_id, split_units in sorted(by_set.items()):
        names = sorted(split_units)
        for i, left in enumerate(names):
            for right in names[i + 1:]:
                shared = sorted(split_units[left] & split_units[right])
                if shared:
                    overlaps.append({
                        "reference_set_id": set_id,
                        "left_split": left,
                        "right_split": right,
                        "overlap_count": len(shared),
                        "overlapping_unit_ids": shared,
                    })
    canonical_manifests.sort(key=lambda x: (x["reference_set_id"], x["reference_set_version"], x["split"]))
    encoded = json.dumps(canonical_manifests, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    split_counts = {
        set_id: {split: len(units) for split, units in sorted(split_units.items())}
        for set_id, split_units in sorted(by_set.items())
    }
    return {
        "schema_version": "nema-dataset-split-audit-v1",
        "state": "DECLARED_SPLITS_DISJOINT_NOT_AUTHENTICATED" if not overlaps else "BLOCKED_DECLARED_SPLIT_OVERLAP",
        "decision": "NO_DECLARED_UNIT_ID_OVERLAP" if not overlaps else "BLOCK_EVALUATION",
        "reference_set_count": len(by_set),
        "manifest_count": len(canonical_manifests),
        "split_unit_counts": split_counts,
        "overlaps": overlaps,
        "manifest_sha256": hashlib.sha256(encoded).hexdigest(),
        "canonical_manifests": canonical_manifests,
        "limitations": [
            "Only exact declared unit IDs are compared; aliases, overlapping geographies, nearby dates, tiles, source assets, and derived features are not detected.",
            "A no-overlap result does not prove that holdout units were excluded from tuning or that reference labels and source evidence are authentic.",
            "Set IDs and versions are declarations. Reusing the same unit ID across versions is conservatively treated as overlap across splits.",
            "Evaluation must remain blocked until any reported overlap is resolved and an independent reviewer confirms the split protocol.",
        ],
    }
