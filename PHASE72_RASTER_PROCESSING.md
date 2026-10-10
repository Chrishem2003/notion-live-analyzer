# Phase 72 — Raster Processing Pipeline

Defines the governed processing contract for Sentinel-2 raster inputs.

It validates scene identity, WGS84 AOI, required Sentinel-2 bands (B02/B03/B04/B08), dimensions, dtype, native resolution, duplicate bands, valid-pixel fraction and cloud-mask status.

Processing requires an explicit cloud mask and supported target resolution. A successful result records source and processing fingerprints, target resolution, valid fraction and band set.

This is a processing contract, not a live raster engine. It does not fabricate pixel values or claim environmental/regulatory truth.

Completion gate: GitHub Actions must verify focused tests, compilation and Streamlit startup before Phase 72 is CI-green.
Next gate: Phase 73 — MSAVI2 + Expanded Spectral Intelligence.