# Public STAC scene discovery

This phase adds an opt-in catalogue metadata search against the fixed Earth Search STAC API and the `sentinel-2-l2a` collection. It does not fetch pixels, run spectral calculations, or authenticate labels. Scene results remain candidates pending asset review.

## Inputs and safety

- Supply an AOI identifier, WGS84 bounding box `[west, south, east, north]`, acquisition date range, cloud-cover threshold, and result limit.
- The API endpoint and collection are fixed in code; users cannot supply arbitrary URLs.
- Request timeout is 20 seconds. Result count is capped at 100. Invalid geometry bounds, dates, cloud thresholds, response shapes, and non-HTTPS asset URLs are rejected.
- The report preserves item IDs, acquisition time, scene-level cloud cover, platform, processing metadata where available, safe HTTPS asset references, rejection reasons, and a report digest.
- No credentials are required by this adapter. Do not pass tokens or private endpoints.

## Limits before pixel processing

Catalogue cloud cover is scene-level, not an AOI-specific valid-pixel fraction. Asset presence does not prove access, checksum validity, grid alignment, or pixel quality. Before calculating NDVI/NDWI, an ingestion stage must fetch only allowlisted assets, verify checksums and raster metadata, apply the provider's cloud/QA mask, calculate valid-pixel fraction over the exact AOI, align grids, and persist immutable acquisition provenance. Reference labels remain separately reviewed. All detections stay advisory.
