# Phase 70 — Google Earth Engine Integration Boundary

## Scope
A deterministic boundary between the governed Area of Interest (AOI) registry and a future Google Earth Engine (GEE) adapter. This batch does not install the Earth Engine SDK, authenticate an account, or claim satellite scenes were retrieved.

## Controls
- Accept only registry-valid AOIs with WGS84 (EPSG:4326) GeoJSON Polygon/MultiPolygon geometry.
- Require real ISO calendar dates; reversed or greater-than-90-day windows fail closed.
- Allowlist collection IDs. Initial collection: Sentinel-2 Surface Reflectance Harmonized (COPERNICUS/S2_SR_HARMONIZED).
- Require a numeric cloud threshold between 0 and 100 percent.
- Provider execution requires explicitly configured credentials and an injected adapter.
- Sanitize provider errors; malformed, duplicate, or out-of-window scene metadata fails the response closed.
- Scene metadata is evidence for review, never an automated legal or compliance determination.

## States
- REQUEST_VALIDATED: request contract passed; no provider call occurred.
- PROVIDER_NOT_CONFIGURED: credentials or adapter absent; no scenes returned.
- PROVIDER_ERROR: provider failed or response violated the contract.
- PROVIDER_QUERY_COMPLETE: valid provider metadata returned and filtered.
- CONTROL_REQUIRED: request or upstream AOI is invalid.

## Test gate
Run in the repository environment:
    python -m unittest tests.test_gee_boundary -v
    python -m compileall -q nema_agora tests

Review actual command and GitHub Actions results before marking this phase CI-green. Creating these files does not itself execute repository CI.

## Explicit non-goals
No fake credentials, synthetic provider success, fabricated scene inventory, automatic enforcement decision, or claim of NEMA approval. A production adapter still needs credential, quota, retry, audit-provenance and provider-terms review.
