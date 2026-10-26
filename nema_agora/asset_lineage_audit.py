"""Cross-split source-asset and derived-data lineage audit.

This checks declared identifiers and SHA-256 fingerprints. It is conservative
screening, not proof of source authenticity or complete scientific independence.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Any, Mapping, Sequence

_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_SPLITS = {"development", "validation", "holdout"}


class AssetLineageAuditError(ValueError):
    """Raised when declared asset-lineage metadata is malformed."""


def audit_asset_lineage(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Flag source assets, tiles, or derived parents reused across data splits.

    Each record requires record_id, split, source_asset_sha256, tile_ids, and
    derived_from. Lists may be empty, but the source asset digest is required.
    """
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or not records:
        raise AssetLineageAuditError("records must be a non-empty array.")
    normalized = []
    seen_ids = set()
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise AssetLineageAuditError(f"records[{index}] must be an object.")
        record_id, split = record.get("record_id"), record.get("split")
        if not isinstance(record_id, str) or not _ID.fullmatch(record_id.strip()):
            raise AssetLineageAuditError(f"records[{index}].record_id is invalid.")
        record_id = record_id.strip()
        if record_id in seen_ids:
            raise AssetLineageAuditError(f"duplicate record_id: {record_id}.")
        seen_ids.add(record_id)
        if split not in _SPLITS:
            raise AssetLineageAuditError(f"records[{index}].split is invalid.")
        digest = record.get("source_asset_sha256")
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise AssetLineageAuditError(f"records[{index}].source_asset_sha256 must be a SHA-256 digest.")
        tile_ids = record.get("tile_ids")
        parents = record.get("derived_from")
        if not isinstance(tile_ids, list) or not isinstance(parents, list):
            raise AssetLineageAuditError(f"records[{index}].tile_ids and derived_from must be arrays.")
        for field, values in (("tile_ids", tile_ids), ("derived_from", parents)):
            if any(not isinstance(value, str) or not _ID.fullmatch(value.strip()) for value in values):
                raise AssetLineageAuditError(f"records[{index}].{field} contains an invalid identifier.")
            if len(values) != len(set(value.strip() for value in values)):
                raise AssetLineageAuditError(f"records[{index}].{field} contains duplicate identifiers.")
        normalized.append({
            "record_id": record_id, "split": split, "source_asset_sha256": digest.lower(),
            "tile_ids": sorted(value.strip() for value in tile_ids),
            "derived_from": sorted(value.strip() for value in parents),
        })
    known = {item["record_id"] for item in normalized}
    for item in normalized:
        missing = sorted(set(item["derived_from"]) - known)
        if missing:
            raise AssetLineageAuditError(
                f"record {item['record_id']} references unknown derived parent(s): {', '.join(missing)}."
            )

    # A cycle makes lineage direction ambiguous and must fail closed.
    parent_map = {item["record_id"]: item["derived_from"] for item in normalized}
    visiting, visited = set(), set()
    def visit(node: str) -> None:
        if node in visiting:
            raise AssetLineageAuditError("derived_from lineage contains a cycle.")
        if node in visited:
            return
        visiting.add(node)
        for parent in parent_map[node]:
            visit(parent)
        visiting.remove(node)
        visited.add(node)
    for node in parent_map:
        visit(node)

    buckets: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for item in normalized:
        buckets[("source_asset_sha256", item["source_asset_sha256"])].append(item)
        for tile in item["tile_ids"]:
            buckets[("tile_id", tile)].append(item)
        for parent in item["derived_from"]:
            buckets[("derived_parent", parent)].append(item)
    findings = []
    for (kind, value), items in sorted(buckets.items()):
        split_names = sorted({item["split"] for item in items})
        if len(split_names) > 1:
            findings.append({
                "finding": "CROSS_SPLIT_LINEAGE_REUSE",
                "lineage_kind": kind,
                "lineage_fingerprint": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                "splits": split_names,
                "record_ids": sorted({item["record_id"] for item in items}),
            })
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "schema_version": "nema-asset-lineage-audit-v1",
        "state": "BLOCKED_CROSS_SPLIT_LINEAGE_REUSE" if findings else "NO_DECLARED_CROSS_SPLIT_LINEAGE_REUSE",
        "decision": "REVIEW_AND_BLOCK_UNTIL_RESOLVED" if findings else "NO_DECLARED_REUSE_FOUND",
        "record_count": len(normalized),
        "finding_count": len(findings),
        "findings": findings,
        "manifest_sha256": hashlib.sha256(canonical).hexdigest(),
        "limitations": [
            "Only declared asset hashes, tile IDs, and derived-from links are checked.",
            "Missing or dishonest declarations, alternate encodings, shared model weights, and holdout-informed tuning are not detected.",
            "A digest match proves byte equality only when hashes were computed from the actual source bytes and the expected digest is independently trusted.",
            "A clean report is not proof of complete dataset independence; independent geospatial and scientific review remains required.",
        ],
    }
