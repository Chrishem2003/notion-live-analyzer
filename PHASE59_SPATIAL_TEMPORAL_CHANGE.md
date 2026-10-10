# Phase 59 — Spatial/Temporal Change Evidence

Phase 59 compares two validated Sentinel-2-derived spectral-index observations and creates deterministic candidate-change evidence.

## Contract
The baseline must precede the comparison scene. An optional minimum temporal separation can be enforced. Both scenes must have NDVI and McFeeters NDWI values in [-1, 1].

For each index:
- delta = comparison - baseline
- absolute_delta = absolute value of delta

The result preserves both source observations, acquisition timestamps, index values, deltas, quality metadata and a deterministic SHA-256 fingerprint.

## Interpretation boundary
The engine reports CANDIDATE_CHANGE_EVIDENCE and requires human review. An index delta is not proof of deforestation, wetland loss, illegal activity or a regulatory violation. Robust interpretation requires spatial alignment, seasonality/context, imagery quality controls and human review.

No live imagery provider, raster processing dependency, automatic enforcement decision or official reporting integration is added in this phase.

## Completion gate
GitHub Actions must verify focused tests, compilation and Streamlit startup before Phase 59 is declared CI-green. No green status is inferred from source inspection.

## Next gate
Phase 60 should strengthen spatial/temporal evidence with explicit AOI/grid identity, co-location checks and uncertainty/quality metadata.
