# Paired raster array analysis: input contract

The NEMA-AGORA Streamlit workspace includes a bounded pixel-array analysis path for paired scenes. It computes pixelwise NDVI and McFeeters NDWI from normalized reflectance arrays and reports summary statistics, delta arrays and a deterministic fingerprint.

## Input contract

Upload one JSON object per scene with this shape:

```json
{
  "scene_id": "SCENE-BASELINE-001",
  "acquired_at": "2026-06-01T10:00:00Z",
  "aoi_id": "AOI-001",
  "grid_id": "GRID-10M-001",
  "crs": "EPSG:4326",
  "bands": {
    "B03": [[0.4, 0.4], [0.5, 0.3]],
    "B04": [[0.2, 0.2], [0.1, 0.3]],
    "B08": [[0.6, 0.6], [0.7, 0.5]]
  },
  "valid_mask": [[true, true], [true, true]],
  "cloud_mask_applied": true
}
```

- Provide B03 (green), B04 (red) and B08 (near infrared).
- All band arrays must be rectangular and the same shape.
- Reflectance must already be scaled to finite values between 0 and 1. The module does not infer or convert source scaling factors.
- The valid mask must be a same-shape boolean array. A pixel is compared only when it is valid in both scenes.
- Scene dates must include a timezone; the baseline date must precede the comparison date.
- aoi_id, grid_id, and CRS must match. Grid equality is declared metadata, not an independent geospatial alignment test.
- Each scene is limited to 250,000 pixels. The application stores the output in the current Streamlit session and offers a JSON download.

## Computations

- NDVI = (B08 - B04) / (B08 + B04)
- McFeeters NDWI = (B03 - B08) / (B03 + B08)
- Per-pixel comparison deltas = comparison index minus baseline index.
- Pixels with invalid masks or a zero index denominator are omitted from calculations and marked null in the pixel output.

## Important boundaries

This is a decoded-array processor, not a GeoTIFF reader. It does not fetch Copernicus data, verify satellite asset authenticity, reproject/resample rasters, verify grid alignment from geotransforms, create a legal wetland boundary, or confirm the correctness of cloud masking. cloud_mask_applied=true is a user-provided assertion, not verified processing provenance. NDVI/NDWI threshold defaults are screening settings, not locally calibrated ecological criteria.

Outputs are evidence for human review only. They do not establish wetland loss, cause, regulatory non-compliance, or a legal violation, and cannot trigger enforcement or official submission. A real study should independently validate source product IDs, checksums, scaling/processing level, acquisition conditions, cloud/shadow masks, CRS/geotransforms, resampling, seasonal comparability, AOI boundaries and field evidence.