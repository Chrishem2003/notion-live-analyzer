# Phase 60 — Spatial/Temporal Evidence Quality

## Purpose
Strengthen Phase 59 candidate-change evidence with explicit spatial co-location and evidence-quality controls before broader change-detection workflows.

## Implemented
- Stable AOI identity for baseline and comparison.
- Stable grid/cell identity for baseline and comparison.
- Explicit spatial alignment; only ALIGNED passes.
- Positive spatial-resolution validation.
- Cloud-cover thresholds bounded to 0–100 percent.
- Valid-pixel fraction thresholds bounded to 0–1.
- Upstream-provided NDVI/NDWI uncertainty metadata with non-negative finite validation.
- Deterministic SHA-256 evidence fingerprint.
- Fail-closed findings for spatial mismatch, unverified alignment, poor imagery quality and invalid uncertainty.
- Synthetic Streamlit demonstration and focused tests.

## Limitation
The module validates supplied uncertainty metadata; it does not invent statistical uncertainty estimates. The evidence explicitly records the method as UPSTREAM_PROVIDED.

## Governance boundary
Passing the quality gate only means the evidence met defined engineering checks for human review. It does not establish deforestation, wetland loss, illegality, environmental truth, regulatory status, NEMA authorization, enforcement, emergency response or production approval.

## Completion gate
GitHub Actions must verify Phase 60 focused tests, compilation and Streamlit startup before Phase 60 is declared CI-green. No green status is inferred from source inspection.

## Next gate
Phase 61 — Broader Spatial Change Detection: introduce explicit change-detection policies and candidate generation over quality-approved spatial/temporal evidence while preserving human review and non-regulatory outputs.
