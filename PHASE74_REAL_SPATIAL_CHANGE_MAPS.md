# Phase 74 — Real Spatial Change Maps

Creates a governed grid-level change-evidence contract from aligned baseline/comparison NDVI, McFeeters NDWI and MSAVI2 surfaces. Each cell retains per-index deltas, threshold reasons and a deterministic map fingerprint.

The implementation validates scene/AOI identity and grid alignment, rejects same-scene comparisons, and fails closed on malformed inputs. It does not fabricate satellite pixels and does not infer illegality, environmental truth, regulatory status or enforcement action.

The prototype accepts raster-derived arrays; live Earth Engine/Sentinel-2 wiring remains a separate integration boundary.

Next: Phase 75 — Spatial Command Center.