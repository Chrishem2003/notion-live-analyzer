# Phase 61 — Broader Spatial Change Detection

## Purpose
Generate deterministic, explainable candidate-change records from Phase 60 quality-approved evidence.

## Implemented
- Explicit NDVI and McFeeters NDWI absolute-change thresholds.
- Rule modes: ANY, ALL and transparent WEIGHTED scoring.
- Combined NDVI+NDWI reason codes.
- Fail-closed dependency on Phase 60 candidate evidence.
- Deterministic candidate IDs and evidence fingerprints.
- Quality and uncertainty metadata carried forward without inventing statistics.
- Human-review status for detected candidates.
- No regulatory, enforcement, emergency or NEMA-authority conclusions.

## Weighted mode
The weighted score is a transparent engineering score, not a calibrated probability or environmental-risk score. Threshold normalization is explicit and the score must not be interpreted as confidence.

## Governance boundary
A detected candidate indicates only that configured analytical thresholds were met. It does not establish deforestation, wetland loss, illegality, environmental truth, regulatory status, enforcement action, emergency response, NEMA authorization or production approval.

## Completion gate
GitHub Actions must verify Phase 61 focused tests, compilation and Streamlit startup before Phase 61 is declared CI-green.
