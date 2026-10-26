"""Fail-closed orchestration gate for holdout evaluation.

This gate combines declared reference-review metadata and split disjointness
before calculating metrics. It is not an authenticity or independence proof.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from nema_agora.asset_lineage_audit import AssetLineageAuditError, audit_asset_lineage
from nema_agora.reference_review import ReferenceReviewError, validate_reference_review_package
from nema_agora.satellite_evaluation import SatelliteEvaluationError, evaluate_change_candidates
from nema_agora.split_audit import SplitAuditError, audit_dataset_splits
from nema_agora.spatiotemporal_audit import SpatiotemporalAuditError, audit_spatiotemporal_separation


class EvaluationGateError(ValueError):
    """Raised when the declared evaluation prerequisites are not satisfied."""


def evaluate_holdout_package(
    *,
    reference_review_package: Mapping[str, Any],
    split_manifests: Sequence[Mapping[str, Any]],
    evaluation_records: Sequence[Mapping[str, Any]],
    spatiotemporal_units: Sequence[Mapping[str, Any]],
    asset_lineage_records: Sequence[Mapping[str, Any]] | None = None,
    min_area_ha: float = 0.1,
) -> dict[str, Any]:
    """Audit declared holdout prerequisites and compute metrics only if all pass."""
    try:
        review = validate_reference_review_package(reference_review_package)
        split_audit = audit_dataset_splits(split_manifests)
        spatial_audit = audit_spatiotemporal_separation(spatiotemporal_units)
        asset_lineage_audit = audit_asset_lineage(asset_lineage_records) if asset_lineage_records is not None else None
    except (ReferenceReviewError, SplitAuditError, SpatiotemporalAuditError, AssetLineageAuditError) as exc:
        raise EvaluationGateError(f"evaluation prerequisites rejected: {exc}") from exc

    if split_audit["decision"] != "NO_DECLARED_UNIT_ID_OVERLAP":
        raise EvaluationGateError("evaluation blocked: declared unit IDs overlap across splits.")
    if spatial_audit["finding_count"]:
        raise EvaluationGateError("evaluation blocked: potential spatial/temporal overlap across splits requires review.")
    if asset_lineage_records is None:
        raise EvaluationGateError("evaluation blocked: asset_lineage_records is required; source-asset, tile, and derived-data separation must be audited before metrics.")
    if not asset_lineage_records:
        raise EvaluationGateError("evaluation blocked: asset_lineage_records must contain at least one declared asset record.")
    if asset_lineage_audit is None:
        raise EvaluationGateError("evaluation blocked: asset-lineage audit did not produce a report.")
    if asset_lineage_audit["finding_count"]:
        raise EvaluationGateError("evaluation blocked: source assets, satellite tiles, or derived lineage are reused across splits.")
    declared_split_pairs = {(unit_id, split) for item in split_audit["canonical_manifests"] for unit_id in item["unit_ids"] for split in [item["split"]]}
    spatial_split_pairs = {(item["unit_id"], item["split"]) for item in spatiotemporal_units}
    if declared_split_pairs != spatial_split_pairs:
        raise EvaluationGateError("evaluation blocked: spatial/temporal unit IDs and split labels must exactly match split manifests.")
    canonical_review = review["canonical_package"]
    if canonical_review["split"] != "holdout":
        raise EvaluationGateError("evaluation blocked: reference-review package must declare split='holdout'.")
    matching = [
        item for item in split_audit["canonical_manifests"]
        if item["reference_set_id"] == canonical_review["reference_set_id"]
        and item["reference_set_version"] == canonical_review["reference_set_version"]
        and item["split"] == "holdout"
    ]
    if len(matching) != 1:
        raise EvaluationGateError("evaluation blocked: exactly one matching holdout manifest is required.")
    holdout_ids = set(matching[0]["unit_ids"])
    reviewed_ids = {unit["unit_id"] for unit in canonical_review["units"]}
    if reviewed_ids != holdout_ids:
        raise EvaluationGateError("evaluation blocked: reviewed unit IDs must exactly match the declared holdout manifest.")

    if not isinstance(evaluation_records, Sequence) or isinstance(evaluation_records, (str, bytes)):
        raise EvaluationGateError("evaluation_records must be an array of objects.")
    record_ids = []
    for index, record in enumerate(evaluation_records):
        if not isinstance(record, Mapping):
            raise EvaluationGateError(f"evaluation_records[{index}] must be an object.")
        unit_id = record.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id.strip():
            raise EvaluationGateError(f"evaluation_records[{index}].unit_id must be non-empty.")
        record_ids.append(unit_id.strip())
    if len(record_ids) != len(set(record_ids)):
        raise EvaluationGateError("evaluation blocked: duplicate evaluation unit IDs.")
    if set(record_ids) != holdout_ids:
        raise EvaluationGateError("evaluation blocked: evaluation record IDs must exactly match the declared holdout units.")

    labels = {unit["unit_id"]: unit["reference_change"] for unit in canonical_review["units"]}
    normalized_records = []
    for record in evaluation_records:
        unit_id = record["unit_id"].strip()
        if record.get("reference_change") is not labels[unit_id]:
            raise EvaluationGateError(f"evaluation blocked: reference label for unit {unit_id} does not match the reviewed package.")
        normalized_records.append(dict(record))
    try:
        metrics = evaluate_change_candidates(normalized_records, min_area_ha=min_area_ha)
    except SatelliteEvaluationError as exc:
        raise EvaluationGateError(f"evaluation records rejected: {exc}") from exc

    return {
        "schema_version": "nema-holdout-evaluation-gate-v1",
        "state": "HOLDOUT_METRICS_COMPUTED_DECLARATIONS_NOT_AUTHENTICATED",
        "decision": "METRICS_COMPUTED_WITH_DECLARED_GATES",
        "reference_review_sha256": review["package_sha256"],
        "split_manifest_sha256": split_audit["manifest_sha256"],
        "reference_set_id": canonical_review["reference_set_id"],
        "reference_set_version": canonical_review["reference_set_version"],
        "holdout_unit_count": len(holdout_ids),
        "split_audit": split_audit,
        "spatiotemporal_audit": spatial_audit,
        "asset_lineage_audit": asset_lineage_audit,
        "evaluation": metrics,
        "limitations": [
            "Asset-lineage screening is required, but it checks only declared hashes, tile IDs, and lineage links; it does not prove evidence authenticity or independence.",
            "The gate enforces declared ID matching only; it cannot detect aliases, spatial or temporal leakage, duplicate evidence, or holdout use during tuning.",
            "Reviewer identities, evidence references, labels, and blinding are not authenticated by this code.",
            "Metrics describe only the submitted holdout records and configured area threshold; they are not live operational performance.",
            "An independent scientific reviewer must approve the split protocol and evidence before results are used for policy, enforcement, or public claims.",
        ],
    }
