# Phase 62 — Spatial Change Evidence Scoring & Review Priority

Phase 62 assigns a transparent engineering priority score to Phase 61 detected candidates.

## Implemented
- NDVI and NDWI magnitude components.
- Optional quality and uncertainty components.
- Explicit configurable weights and review threshold.
- Deterministic score/fingerprint and HIGH/MEDIUM/LOW priority tier.
- Reason-code carry-forward and human-review status.
- Fail-closed candidate/policy validation.

The score is an engineering prioritisation indicator, not a calibrated probability, environmental-risk score, compliance score or regulatory finding.

## Governance boundary
No result establishes deforestation, wetland loss, illegality, environmental truth, regulatory status, enforcement action, emergency response, NEMA authorization or production approval.

## Completion gate
GitHub Actions must verify Phase 62 tests, compilation and Streamlit startup before this phase is declared CI-green.
