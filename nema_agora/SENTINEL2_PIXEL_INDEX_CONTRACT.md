# Sentinel-2 pixel index processing contract

Status: **implemented calculation contract; not yet connected to GeoTIFF ingestion or a live satellite download workflow**.

The `nema_agora.pixel_indices` module calculates two indices from already-loaded, already-aligned 2D arrays:

- NDVI = (B08 NIR − B04 red) / (B08 NIR + B04 red)
- McFeeters NDWI = (B03 green − B08 NIR) / (B03 green + B08 NIR)

## Safety and quality behavior

- Requires B03, B04, B08 and SCL to have exactly the same 2D shape. It does not silently resample or reproject.
- Requires a boolean AOI mask when one is provided; valid-pixel fractions use only pixels inside that mask.
- Excludes non-finite band values, SCL classes 0, 1, 3, 7, 8, 9, 10 and 11, and pixels whose index denominator is effectively zero.
- Does not silently replace missing pixels with zero. If no pixels remain, summary statistics are null.
- Reports valid pixel counts/fractions, summary quantiles, masking counts, limitations and a deterministic SHA-256 digest.
- Assumes caller has checked reflectance scaling, co-registration, resolution, CRS, AOI rasterization and acquisition provenance. The processor itself explicitly does not claim to verify these.

## Important interpretation limits

NDWI here means the green-NIR McFeeters water index, not the NIR-SWIR moisture index. It is a screening metric, not a wetland boundary, legal determination, or enforcement finding. Index thresholds must be calibrated against independently reviewed local reference data, seasonality, terrain, turbidity and sensor/processing differences. Do not compare dates unless grids, masks, acquisition context and processing are harmonized.

## Next integration gate

Before operational use, implement and test a constrained GeoTIFF reader that validates CRS, transform, dimensions, band descriptions, nodata, SCL classes and AOI overlap; records source SHA-256; and refuses mismatched grids instead of resampling implicitly. Only then wire an explicit user-upload workflow into the NEMA-AGORA UI. A separate, audited downloader is needed before any remote asset acquisition; catalogue discovery does not itself prove asset safety or availability.
