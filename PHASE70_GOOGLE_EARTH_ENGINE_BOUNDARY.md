# Phase 70 — Google Earth Engine Integration Boundary

Defines the provider-neutral contract for authorized Google Earth Engine access.

A request binds a stable request ID and registered asset ID to AOI geometry, WGS84 CRS, collection, date window and cloud-cover constraint. Requests receive deterministic fingerprints.

The concrete provider boundary intentionally returns PROVIDER_NOT_CONNECTED until an authorized Earth Engine credential/project configuration is supplied. It never fabricates scenes, evidence, authorization, environmental truth, regulatory conclusions, violations or enforcement actions.

This phase establishes the seam for Phase 71 Sentinel-2 acquisition; it is not a live Earth Engine integration.

Completion gate: focused tests, compilation and Streamlit startup must pass in GitHub Actions before Phase 70 is CI-green.
