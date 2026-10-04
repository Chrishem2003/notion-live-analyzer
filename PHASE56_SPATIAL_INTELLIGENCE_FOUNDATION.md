# Phase 56 — Spatial Intelligence Foundation

## Purpose
Establish the provider-neutral spatial contract required before Sentinel-2, NDVI/NDWI and spatial-change analytics are added.

## Implemented
- WGS84 (EPSG:4326) spatial observation records with deterministic fingerprints.
- GeoJSON-compatible point, polygon and multipolygon geometry contracts.
- Area-of-interest records for district, wetland, watershed, protected-area and custom boundaries.
- Fail-closed coordinate, CRS, identity, source and capture-time validation.
- Provider-neutral analysis contract that accepts evidence metadata but rejects autonomous regulatory conclusions.
- No live Earth Engine/provider connection in this phase.

## Governance boundary
Spatial analytics may identify candidate changes or evidence for human review. They must not declare illegality, environmental truth, enforcement action, emergency status or official regulatory status.

## Completion gate
GitHub Actions must verify Phase 56 focused tests, compilation and Streamlit startup before this phase is declared CI-green.

## Next gate
Phase 57 — Sentinel-2 Remote Sensing Adapter: define imagery metadata, acquisition/cloud-quality contracts and a provider adapter boundary without turning imagery signals into automatic violations.
