# Phase 58 — NDVI / NDWI Analytics

## Purpose

Phase 58 adds transparent, deterministic spectral-index calculations on validated Sentinel-2 optical inputs.

### Indices

- NDVI = (B08 - B04) / (B08 + B04) using Sentinel-2 NIR (B08) and red (B04).
- McFeeters NDWI = (B03 - B08) / (B03 + B08) using green (B03) and NIR (B08).

Inputs are explicitly contracted as normalized reflectance values in [0, 1]. Scaling from provider-specific asset values belongs to the remote-sensing adapter, not this index engine.

## Quality controls

- Scene identity must be a valid stable ID.
- Required bands must be present.
- Inputs must be finite numeric values in [0, 1].
- A zero denominator is rejected rather than converted to a misleading value.
- Results must be finite and within the theoretical [-1, 1] range.
- Results and formulas receive deterministic SHA-256 fingerprints.
- Evidence records identify source bands and quality assumptions.

## Governance boundary

NDVI and NDWI are analytical measurements, not automatic classifications of deforestation, wetland loss, illegality or regulatory violations. A change signal requires appropriate temporal/spatial comparison and human review. This phase does not connect to Google Earth Engine, download imagery, make enforcement decisions, or submit official reports.

## Completion gate

GitHub Actions must verify focused tests, compilation and Streamlit startup before Phase 58 is declared CI-green. No green status is inferred from source inspection.

## Next gate

Phase 59 should build spatial/temporal change evidence from validated Sentinel-2 scenes and spectral-index observations, with explicit baseline comparison and uncertainty handling.
