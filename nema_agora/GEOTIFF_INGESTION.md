# Validated Sentinel-2 GeoTIFF ingestion

Status: **implemented on the integration branch; CI verification pending**.

## UI workflow
In the single-page NEMA-AGORA workspace, open **Maps & metrics → Pilot metrics → Process supplied Sentinel-2 GeoTIFF**. Upload one multi-band GeoTIFF with band descriptions `B03`, `B04`, `B08`, `SCL` and optionally a polygonal AOI GeoJSON. The AOI file has no CRS declaration in this workflow, so the user must confirm its coordinates already use the raster CRS. No reprojection or resampling occurs.

## Validation and limits
- Upload limit: 100 MiB for raster, 5 MiB for AOI GeoJSON; 25 million raster pixels maximum.
- Requires raster CRS, finite/non-singular affine transform, explicit unique band descriptions and all required band names.
- Uses source raster's shared grid. No implicit band alignment or resampling.
- Applies per-band nodata masks; invalid reflectance values become missing values rather than zeros.
- Uses the same conservative SCL exclusions as the pixel-index contract.
- Optional AOI is rasterized on the source grid; no overlapping pixel means rejection.
- Records source and AOI SHA-256 digests, CRS, grid dimensions, band mapping, transform, nodata values, valid-pixel counts/fractions, index summaries and a processing-report digest.
- Uses the raster values as stored. It does not automatically infer or rescale Sentinel-2 integer reflectance values; verify compatible scale factors and processing metadata before interpreting results.

## Interpretation boundary
The report is a **screening result requiring review**. It is not independently authenticated satellite evidence, change detection, a wetland delineation, compliance determination or enforcement decision. For production use, the next layer must verify source acquisition/product metadata and reflectance scaling, add reproducible temporal comparison on harmonized grids, and validate against independent local reference data.
