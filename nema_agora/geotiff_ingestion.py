"""Bounded, fail-closed GeoTIFF ingestion for paired Sentinel-style reflectance scenes.

Rasterio is an optional dependency. This module reads a multiband GeoTIFF and an
explicit valid-pixel mask GeoTIFF from uploaded bytes. It does not download data,
infer scale factors, reproject, resample, or independently verify cloud masking.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any

from nema_agora.geojson_aoi import validate_geojson_aoi

MAX_PIXELS = 250_000
REQUIRED_BANDS = ("B03", "B04", "B08")


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _aware_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def read_geotiff_scene(
    *,
    raster_bytes: bytes,
    valid_mask_bytes: bytes,
    scene_id: str,
    acquired_at: str,
    aoi_id: str,
    reflectance_scale: float,
    reflectance_offset: float = 0.0,
    cloud_shadow_mask_applied: bool = False,
    aoi_geojson: Any | None = None,
) -> dict[str, Any]:
    """Decode a 3-band or more multiband GeoTIFF plus a same-grid validity mask.

    Band mapping is fixed to B03=band 1, B04=band 2, B08=band 3 (1-based).
    Caller must supply the correct source scaling and a precomputed cloud/shadow
    validity mask. A boolean flag is retained as a user assertion, not verified fact.
    """
    if not isinstance(raster_bytes, bytes) or not raster_bytes:
        raise ValueError("GEOTIFF_BYTES_REQUIRED")
    if not isinstance(valid_mask_bytes, bytes) or not valid_mask_bytes:
        raise ValueError("VALID_MASK_GEOTIFF_BYTES_REQUIRED")
    for name, value in (("scene_id", scene_id), ("aoi_id", aoi_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name.upper()}_REQUIRED")
    if not _aware_timestamp(acquired_at):
        raise ValueError("TIMEZONE_AWARE_ACQUISITION_TIME_REQUIRED")
    if isinstance(reflectance_scale, bool) or not isinstance(reflectance_scale, (int, float)) or not math.isfinite(float(reflectance_scale)) or float(reflectance_scale) <= 0:
        raise ValueError("INVALID_REFLECTANCE_SCALE")
    if isinstance(reflectance_offset, bool) or not isinstance(reflectance_offset, (int, float)) or not math.isfinite(float(reflectance_offset)):
        raise ValueError("INVALID_REFLECTANCE_OFFSET")
    if cloud_shadow_mask_applied is not True:
        raise ValueError("CLOUD_SHADOW_MASK_ASSERTION_REQUIRED")

    if aoi_geojson is not None and not validate_geojson_aoi(aoi_geojson).get("valid"):
        raise ValueError("INVALID_AOI_GEOJSON")

    try:
        import numpy as np
        import rasterio
        from rasterio.features import geometry_mask
        from rasterio.io import MemoryFile
    except ImportError as exc:
        raise RuntimeError("OPTIONAL_RASTERIO_DEPENDENCY_MISSING") from exc

    try:
        with MemoryFile(raster_bytes) as image_mem, MemoryFile(valid_mask_bytes) as mask_mem:
            with image_mem.open() as src, mask_mem.open() as mask_src:
                if src.driver != "GTiff" or mask_src.driver != "GTiff":
                    raise ValueError("GEOTIFF_FORMAT_REQUIRED")
                if src.count < 3:
                    raise ValueError("THREE_BAND_GEOTIFF_REQUIRED")
                if src.crs is None or mask_src.crs is None:
                    raise ValueError("CRS_METADATA_REQUIRED")
                if src.crs.to_string() != "EPSG:4326" or mask_src.crs.to_string() != "EPSG:4326":
                    raise ValueError("ONLY_EPSG_4326_SUPPORTED_WITHOUT_REPROJECTION")
                if src.width != mask_src.width or src.height != mask_src.height:
                    raise ValueError("VALID_MASK_DIMENSIONS_MISMATCH")
                if src.transform != mask_src.transform:
                    raise ValueError("VALID_MASK_TRANSFORM_MISMATCH")
                if src.width * src.height > MAX_PIXELS:
                    raise ValueError("GEOTIFF_PIXEL_LIMIT_EXCEEDED")
                if mask_src.count != 1:
                    raise ValueError("VALID_MASK_MUST_HAVE_ONE_BAND")
                if src.width < 1 or src.height < 1:
                    raise ValueError("EMPTY_GEOTIFF")
                if not src.transform.is_identity and src.transform.a == 0 and src.transform.e == 0:
                    raise ValueError("INVALID_GEOTIFF_TRANSFORM")
                if src.transform.a <= 0 or src.transform.e >= 0:
                    raise ValueError("UNSUPPORTED_OR_FLIPPED_PIXEL_ORIENTATION")
                if src.transform.b != 0 or src.transform.d != 0:
                    raise ValueError("ROTATED_GRID_UNSUPPORTED")
                raw = src.read(indexes=[1, 2, 3], masked=False)
                src_masks = src.read_masks(indexes=[1, 2, 3])
                mask_data = mask_src.read(1, masked=False)
                mask_values = np.isfinite(mask_data) & (mask_data == 1)
                mask_band_valid = np.all(src_masks > 0, axis=0)
                nodata = src.nodata
                if nodata is not None:
                    nodata_valid = np.all(raw != nodata, axis=0)
                else:
                    nodata_valid = np.ones(mask_data.shape, dtype=bool)
                valid = mask_values & mask_band_valid & nodata_valid
                domain_mask = np.ones(mask_data.shape, dtype=bool)
                scaled = raw.astype("float64") * float(reflectance_scale) + float(reflectance_offset)
                valid &= np.all(np.isfinite(scaled), axis=0)
                # The analysis contract accepts normalized reflectance only.
                valid &= np.all((scaled >= 0) & (scaled <= 1), axis=0)
                aoi_clipping_applied = False
                if aoi_geojson is not None:
                    aoi_mask = geometry_mask(
                        _geojson_geometries(aoi_geojson),
                        out_shape=(src.height, src.width),
                        transform=src.transform,
                        invert=True,
                        all_touched=False,
                    )
                    domain_mask = aoi_mask
                    valid &= domain_mask
                    aoi_clipping_applied = True
                scaled[:, ~valid] = 0.0
                bands = {
                    "B03": scaled[0].tolist(),
                    "B04": scaled[1].tolist(),
                    "B08": scaled[2].tolist(),
                }
                valid_list = valid.tolist()
                grid_id = _digest(json.dumps({
                    "crs": src.crs.to_string(),
                    "transform": tuple(src.transform),
                    "width": src.width,
                    "height": src.height,
                }, sort_keys=True).encode("utf-8"))
                return {
                    "scene_id": scene_id.strip(),
                    "acquired_at": acquired_at,
                    "aoi_id": aoi_id.strip(),
                    "grid_id": grid_id,
                    "crs": "EPSG:4326",
                    "bands": bands,
                    "valid_mask": valid_list,
                    "domain_mask": domain_mask.tolist(),
                    "cloud_mask_applied": True,
                    "ingestion": {
                        "method": "manual_geotiff_upload",
                        "raster_sha256": _digest(raster_bytes),
                        "valid_mask_sha256": _digest(valid_mask_bytes),
                        "raster_driver": src.driver,
                        "band_mapping": {"B03": 1, "B04": 2, "B08": 3},
                        "reflectance_scale": float(reflectance_scale),
                        "reflectance_offset": float(reflectance_offset),
                        "cloud_shadow_mask_applied_by_uploader": True,
                        "aoi_clipping_applied": aoi_clipping_applied,
                        "aoi_clipping_method": "pixel_center" if aoi_clipping_applied else None,
                        "aoi_sha256": _digest(json.dumps(_geojson_geometries(aoi_geojson), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")) if aoi_geojson is not None else None,
                        "aoi_pixel_count": int(np.count_nonzero(domain_mask)),
                        "aoi_valid_pixel_fraction": (float(np.count_nonzero(valid)) / int(np.count_nonzero(domain_mask))) if np.count_nonzero(domain_mask) else 0.0,
                        "aoi_validation": validate_geojson_aoi(aoi_geojson) if aoi_geojson is not None else None,
                        "valid_mask_pixels": int(np.count_nonzero(valid)),
                        "total_pixels": int(src.width * src.height),
                        "bounds": {
                            "west": float(src.bounds.left),
                            "south": float(src.bounds.bottom),
                            "east": float(src.bounds.right),
                            "north": float(src.bounds.top),
                        },
                        "limitations": [
                            "Band mapping assumes input order B03, B04, B08 and must be verified by uploader.",
                            "Reflectance scale and offset are user-supplied and not inferred from metadata.",
                            "Cloud/shadow mask provenance is user asserted; not independently verified.",
                            "No reprojection, resampling, or provider authenticity verification is performed.",
                            "Optional AOI clipping uses pixel-center inclusion; AOI authority and complete topology are not independently verified.",
                            "Grid identifier proves matching metadata only when compared with a separately ingested scene; it does not prove correct geospatial content.",
                        ],
                    },
                }
    except ValueError:
        raise
    except Exception as exc:
        # Do not leak local paths or untrusted raster metadata in UI-facing error text.
        raise ValueError(f"GEOTIFF_READ_FAILED_{type(exc).__name__}") from exc


def _geojson_geometries(document: Any) -> list[dict[str, Any]]:
    """Extract validated GeoJSON geometries accepted by rasterio.features."""
    if isinstance(document, str):
        try:
            document = json.loads(document)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError("INVALID_AOI_GEOJSON") from exc
    kind = document.get("type") if isinstance(document, dict) else None
    if kind == "Feature":
        geometries = [document.get("geometry")]
    elif kind == "FeatureCollection":
        geometries = [feature.get("geometry") for feature in document.get("features", [])]
    elif kind in {"Polygon", "MultiPolygon"}:
        geometries = [document]
    else:
        raise ValueError("INVALID_AOI_GEOJSON")
    if not geometries or any(not isinstance(geometry, dict) for geometry in geometries):
        raise ValueError("INVALID_AOI_GEOJSON")
    return geometries
