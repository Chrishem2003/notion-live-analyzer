# Two-date satellite index comparison contract

Status: **paired local GeoTIFF workflow implemented in the single-page workspace; automated verification is in progress and no independently validated imagery has been analysed**.

The `nema_agora.paired_raster_ingestion.compare_uploaded_geotiff_pair` workflow accepts two local multi-band GeoTIFFs, explicit acquisition timestamps, separately declared reflectance-scale/product identifiers and processing baselines for each date, and an optional AOI. It validates both files, blocks mismatched grids, checks the per-date metadata declarations for exact equality, applies the same AOI and conservative SCL policy, and compares only the intersection of valid pixels. The lower-level `nema_agora.satellite_change.compare_two_dates` function enforces array-level prerequisites.

## Required safeguards
- Both acquisition timestamps must include timezone information and later date must be strictly later.
- CRS, dimensions, affine transform, grid identifier, reflectance scale identifier and processing baseline must match exactly.
- Every index array and shared valid mask must match the declared raster grid.
- A configurable minimum shared-valid fraction is enforced (default 70%); low coverage blocks the comparison.
- Outputs include index deltas, robust summary statistics, threshold-exceedance pixel counts, compatibility checks and a report SHA-256 digest.
- Does not calculate area, infer causation, authenticate source imagery or make environmental/legal findings.

## Important caveat
The scale and processing-baseline identifiers are separately entered operator assertions, checked for exact equality. The workflow does not independently authenticate those labels against provider metadata; reviewers must verify them from original product documentation. The grid/CRS/transform and dimensions are derived from the raster files themselves. Exact grid metadata equality does not prove source authenticity or scientific suitability.

## Next integration gate
Build a paired GeoTIFF loader and UI flow that:
1. validates both files and the band descriptions;
2. requires acquisition timestamps and scale/product metadata;
3. enforces exact CRS, dimensions and affine transform equality;
4. applies the same AOI mask and valid-pixel/cloud policy to both dates;
5. generates a comparison report only after all checks pass;
6. tests seasonal and cloud artefacts against independently reviewed local reference data.
