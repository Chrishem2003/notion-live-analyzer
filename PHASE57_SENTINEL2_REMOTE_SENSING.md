# Phase 57 — Sentinel-2 Remote Sensing Adapter

## Purpose
Introduce a provider-neutral Sentinel-2 imagery contract on top of Phase 56 spatial intelligence.

## Implemented
- Sentinel-2 scene/product identity validation.
- L1C/L2A collection validation.
- ISO-compatible acquisition timestamp validation.
- WGS84 bounding-box validation.
- Cloud-cover quality metadata in the 0–100% range.
- Required B02, B03, B04 and B08 band presence for the initial optical analytics path.
- Deterministic scene fingerprints.
- Provider adapter boundary with no live credentials or network dependency.
- Evidence output containing source/acquisition/quality metadata, without autonomous regulatory conclusions.

## Governance boundary
A Sentinel-2 scene is a source of spatial evidence. Cloud cover and metadata validity are quality signals, not environmental truth. Imagery-derived candidates must remain subject to human review and must not be labelled automatically as illegal activity, enforcement cases, emergency incidents or official regulatory findings.

## Completion gate
GitHub Actions must verify Phase 57 tests, compilation and Streamlit startup before this phase is declared CI-green.

## Next gate
Phase 58 — NDVI / NDWI Analytics: derive transparent spectral indices from validated imagery inputs, with explicit quality handling and no automatic regulatory conclusions.
