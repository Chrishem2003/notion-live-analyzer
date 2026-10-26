# Two-date satellite index comparison contract

Status: **paired local GeoTIFF workflow implemented in the single-page workspace; automated verification is in progress and no independently validated imagery has been analysed**.

The `nema_agora.paired_raster_ingestion.compare_uploaded_geotiff_pair` workflow accepts two local multi-band GeoTIFFs, explicit acquisition timestamps, separately declared reflectance-scale/product identifiers and processing baselines for each date, and an optional AOI. It validates both files, blocks mismatched grids, checks the per-date metadata declarations for exact equality, applies the same AOI and conservative SCL policy, and compares only the intersection of valid pixels. The lower-level `nema_agora.satellite_change.compare_two_dates` function enforces array-level prerequisites.

## Required safeguards
- Both acquisition timestamps must include timezone information and later date must be strictly later.
- CRS, dimensions, affine transform, grid identifier, reflectance scale identifier and processing baseline must match exactly.
- Every index array and shared valid mask must match the declared raster grid.
- A configurable minimum shared-valid fraction is enforced (default 70%); low coverage blocks the comparison.
- Embedded GeoTIFF scale and offset values for B03, B04 and B08 must be finite and match exactly between dates; the values are recorded in provenance.
- A short allowlist of dataset and band metadata tags is captured for review, with values bounded to 240 characters. If an embedded PROCESSING_BASELINE tag exists and conflicts with the corresponding operator declaration, comparison is blocked. Tags remain untrusted claims, not authenticated evidence.
- Outputs include index deltas, robust summary statistics, threshold-exceedance pixel counts, compatibility checks and a report SHA-256 digest.
- Does not calculate area, infer causation, authenticate source imagery or make environmental/legal findings.

## Important caveat
The scale and processing-baseline identifiers are separately entered operator assertions, checked for exact equality. The workflow does not independently authenticate those labels against provider metadata; reviewers must verify them from original product documentation. Embedded GeoTIFF scales and offsets are read for B03/B04/B08 and compared exactly, but matching defaults (often 1.0 and 0.0) do not prove the pixel values are physically scaled reflectance. A bounded allowlist of source tags is included in the report to help reviewers locate product identifiers and processing metadata; those tags may be missing, edited or forged and are not authenticated. The grid/CRS/transform and dimensions are derived from the raster files themselves. Exact grid or band-metadata equality does not prove source authenticity or scientific suitability.

## Next integration gate
Build a paired GeoTIFF loader and UI flow that:
1. validates both files and the band descriptions;
2. requires acquisition timestamps and scale/product metadata;
3. enforces exact CRS, dimensions and affine transform equality;
4. applies the same AOI mask and valid-pixel/cloud policy to both dates;
5. generates a comparison report only after all checks pass;
6. tests seasonal and cloud artefacts against independently reviewed local reference data.
