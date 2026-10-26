"""Validated local GeoTIFF ingestion for NEMA-AGORA Sentinel-2 screening.

The loader deliberately accepts one multi-band GeoTIFF whose band descriptions
are exactly B03, B04, B08 and SCL (order-independent). All bands therefore share
one raster grid. It does not reproject, resample, fetch remote assets, or infer
missing metadata. AOI GeoJSON must already use the raster's CRS.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np

from nema_agora.pixel_indices import PixelProcessingError, process_sentinel2_bands

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_PIXEL_COUNT = 25_000_000
REQUIRED_BANDS = ("B03", "B04", "B08", "SCL")


class RasterIngestionError(ValueError):
    """Raised when a raster cannot be safely interpreted."""


def _aoi_geometries(raw: bytes) -> list[dict[str, Any]]:
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RasterIngestionError("AOI must be a valid UTF-8 GeoJSON document.") from exc
    kind = doc.get("type") if isinstance(doc, dict) else None
    if kind == "FeatureCollection":
        features = doc.get("features")
        if not isinstance(features, list) or not features:
            raise RasterIngestionError("AOI FeatureCollection must contain features.")
        geometries = [f.get("geometry") for f in features if isinstance(f, dict) and f.get("type") == "Feature"]
    elif kind == "Feature":
        geometries = [doc.get("geometry")]
    elif kind in {"Polygon", "MultiPolygon"}:
        geometries = [doc]
    else:
        raise RasterIngestionError("AOI must be a Polygon, MultiPolygon, Feature, or FeatureCollection.")
    if not geometries or any(not isinstance(g, dict) or g.get("type") not in {"Polygon", "MultiPolygon"} for g in geometries):
        raise RasterIngestionError("AOI contains an empty or unsupported geometry; only polygonal AOIs are accepted.")
    return geometries


def process_uploaded_geotiff(
    raster_bytes: bytes,
    *,
    aoi_geojson_bytes: bytes | None = None,
    aoi_crs_confirmed_same_as_raster: bool = False,
) -> dict[str, Any]:
    """Validate a four-band GeoTIFF and return a provenance-bound index report."""
    if not isinstance(raster_bytes, (bytes, bytearray)) or not raster_bytes:
        raise RasterIngestionError("Upload a non-empty GeoTIFF file.")
    if len(raster_bytes) > MAX_UPLOAD_BYTES:
        raise RasterIngestionError(f"Raster upload exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB safety limit.")
    if aoi_geojson_bytes is not None:
        if not aoi_crs_confirmed_same_as_raster:
            raise RasterIngestionError("Confirm that the AOI GeoJSON coordinates already use the raster CRS; reprojection is not performed.")
        if not aoi_geojson_bytes or len(aoi_geojson_bytes) > 5 * 1024 * 1024:
            raise RasterIngestionError("AOI GeoJSON must be non-empty and no larger than 5 MiB.")
    try:
        import rasterio
        from rasterio.io import MemoryFile
        from rasterio.features import geometry_mask
    except ImportError as exc:
        raise RasterIngestionError("GeoTIFF processing dependency rasterio is not installed in this environment.") from exc

    source_digest = hashlib.sha256(raster_bytes).hexdigest()
    try:
        with MemoryFile(bytes(raster_bytes)) as memfile:
            with memfile.open() as dataset:
                if dataset.driver != "GTiff":
                    raise RasterIngestionError("Upload must be a GeoTIFF.")
                if dataset.crs is None:
                    raise RasterIngestionError("Raster has no CRS; ingestion is blocked.")
                if dataset.width <= 0 or dataset.height <= 0 or dataset.width * dataset.height > MAX_PIXEL_COUNT:
                    raise RasterIngestionError(f"Raster dimensions are invalid or exceed {MAX_PIXEL_COUNT:,} pixels.")
                if dataset.count < 4:
                    raise RasterIngestionError("Raster must contain named B03, B04, B08 and SCL bands.")
                descriptions = [str(v).strip().upper() if v else "" for v in dataset.descriptions]
                if any(not name for name in descriptions):
                    raise RasterIngestionError("Every raster band must have an explicit band description.")
                if len(set(descriptions)) != len(descriptions):
                    raise RasterIngestionError("Duplicate band descriptions are ambiguous and rejected.")
                missing = sorted(set(REQUIRED_BANDS) - set(descriptions))
                if missing:
                    raise RasterIngestionError("Required band descriptions missing: " + ", ".join(missing))
                if not dataset.transform.isfinite or abs(dataset.transform.determinant) < 1e-20:
                    raise RasterIngestionError("Raster affine transform is invalid or singular.")
                indexes = {name: descriptions.index(name) + 1 for name in REQUIRED_BANDS}
                masked_bands = {}
                for name in ("B03", "B04", "B08"):
                    arr = dataset.read(indexes[name], masked=True).astype("float64")
                    masked_bands[name] = arr.filled(np.nan)
                scl_masked = dataset.read(indexes["SCL"], masked=True)
                scl_data = np.asarray(scl_masked.filled(0))
                if not np.all(np.isfinite(scl_data)) or not np.all(scl_data == np.floor(scl_data)):
                    raise RasterIngestionError("SCL band must contain finite integer class codes.")
                aoi_mask = None
                aoi_digest = None
                if aoi_geojson_bytes is not None:
                    geometries = _aoi_geometries(aoi_geojson_bytes)
                    aoi_digest = hashlib.sha256(aoi_geojson_bytes).hexdigest()
                    try:
                        aoi_mask = geometry_mask(
                            geometries,
                            out_shape=(dataset.height, dataset.width),
                            transform=dataset.transform,
                            invert=True,
                            all_touched=False,
                        )
                    except Exception as exc:
                        raise RasterIngestionError("AOI could not be rasterized on the source grid.") from exc
                    if not np.any(aoi_mask):
                        raise RasterIngestionError("AOI does not overlap any raster pixel on this grid.")
                result = process_sentinel2_bands(
                    b03_green=masked_bands["B03"],
                    b04_red=masked_bands["B04"],
                    b08_nir=masked_bands["B08"],
                    scl=scl_data,
                    aoi_mask=aoi_mask,
                )
                metadata = {
                    "source_sha256": source_digest,
                    "aoi_geojson_sha256": aoi_digest,
                    "source_format": "GeoTIFF",
                    "crs": str(dataset.crs),
                    "width_pixels": int(dataset.width),
                    "height_pixels": int(dataset.height),
                    "band_descriptions": descriptions,
                    "selected_band_indexes_1_based": indexes,
                    "transform": [float(v) for v in dataset.transform[:6]],
                    "nodata_by_band": {name: dataset.nodatavals[indexes[name] - 1] for name in REQUIRED_BANDS},
                    "reflectance_scale_assumption": "Values are used as stored; caller must confirm B03/B04/B08 share compatible reflectance scaling.",
                    "aoi_handling": "none_full_raster" if aoi_mask is None else "GeoJSON rasterized on source grid; caller attested same CRS",
                    "resampling_performed": False,
                    "source_pixels_downloaded_by_processor": False,
                }
    except RasterIngestionError:
        raise
    except Exception as exc:
        raise RasterIngestionError("GeoTIFF could not be opened or validated. Check file integrity and band metadata.") from exc
    result["source"] = metadata
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    result["processing_report_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    result["state"] = "RASTER_SCREENING_REPORT_REVIEW_REQUIRED"
    result["limitations"].extend([
        "The user supplied the source raster; the processor does not independently authenticate its provider or acquisition metadata.",
        "A GeoJSON AOI has no embedded CRS in this workflow; same-CRS correctness is an explicit user attestation.",
        "Pixel-level index summaries do not establish environmental change, wetland status, legal compliance or enforcement evidence.",
    ])
    return result
