# Two-date satellite index comparison contract

Status: **paired local GeoTIFF workflow implemented in the single-page workspace; automated verification is in progress and no independently validated imagery has been analysed**.

The `nema_agora.satellite_change.compare_two_dates` function accepts paired NDVI and McFeeters NDWI arrays, explicit acquisition timestamps, grid/CRS/transform identity, reflectance-scale identity, processing-baseline identity, and a shared boolean validity mask.

## Required safeguards
- Both acquisition timestamps must include timezone information and later date must be strictly later.
- CRS, dimensions, affine transform, grid identifier, reflectance scale identifier and processing baseline must match exactly.
- Every index array and shared valid mask must match the declared raster grid.
- A configurable minimum shared-valid fraction is enforced (default 70%); low coverage blocks the comparison.
- Outputs include index deltas, robust summary statistics, threshold-exceedance pixel counts, compatibility checks and a report SHA-256 digest.
- Does not calculate area, infer causation, authenticate source imagery or make environmental/legal findings.

## Important caveat
The grid/scale/baseline IDs are caller-supplied assertions. The function cannot independently prove that two rasters are co-registered or radiometrically comparable. A trusted ingestion workflow must derive these identifiers from validated source metadata and verified processing configuration, not from user guesses.

## Next integration gate
Build a paired GeoTIFF loader and UI flow that:
1. validates both files and the band descriptions;
2. requires acquisition timestamps and scale/product metadata;
3. enforces exact CRS, dimensions and affine transform equality;
4. applies the same AOI mask and valid-pixel/cloud policy to both dates;
5. generates a comparison report only after all checks pass;
6. tests seasonal and cloud artefacts against independently reviewed local reference data.
