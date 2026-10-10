# Phase 71 — Live Sentinel-2 Acquisition

Defines the governed acquisition orchestration boundary between registered environmental assets and Sentinel-2 scene retrieval.

Requests bind asset identity, AOI geometry, collection, date range and cloud threshold. They receive deterministic fingerprints. The live provider remains disconnected until authorized Earth Engine access is configured.

Scene-list validation prevents duplicate or malformed provider identities. An unconnected provider returns an explicit ACQUISITION_NOT_CONNECTED state with no fabricated scenes or evidence.

This phase does not claim environmental truth, regulatory status, violations, enforcement or emergency authority.

Completion gate: GitHub Actions must verify focused tests, compilation and Streamlit startup before Phase 71 is CI-green.
Next gate: Phase 72 — Raster Processing Pipeline.