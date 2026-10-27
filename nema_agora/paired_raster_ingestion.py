"""Paired GeoTIFF ingestion and fail-closed temporal index screening."""
from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np

from nema_agora.pixel_indices import EXCLUDED_SCL_CLASSES
from nema_agora.raster_ingestion import MAX_PIXEL_COUNT, MAX_UPLOAD_BYTES, RasterIngestionError, _aoi_geometries
from nema_agora.satellite_change import ChangeComparisonError, compare_two_dates


class PairedRasterError(ValueError):
    """Raised when paired-raster comparison prerequisites are not met."""


_METADATA_TAG_ALLOWLIST = {
    "PRODUCT_URI", "PRODUCT_ID", "PROCESSING_BASELINE", "DATATAKE_SENSING_START",
    "SENSING_TIME", "SPACECRAFT_NAME", "SENSOR", "PLATFORM", "INSTRUMENT",
    "AREA_OR_POINT", "TIFFTAG_DATETIME", "GRANULE_ID", "MGRS_TILE",
}


def _safe_metadata_tags(tags: dict[str, Any]) -> dict[str, str]:
    """Return a small allowlisted subset of untrusted raster metadata."""
    result = {}
    for key, value in tags.items():
        normalized_key = str(key).strip().upper()
        if normalized_key not in _METADATA_TAG_ALLOWLIST:
            continue
        normalized_value = str(value).replace("\\x00", "").strip()
        if normalized_value:
            result[normalized_key] = normalized_value[:240]
    return result


def _read_pair_source(raw: bytes, label: str) -> dict[str, Any]:
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise PairedRasterError(f"{label}: upload a non-empty GeoTIFF.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise PairedRasterError(f"{label}: raster exceeds the 100 MiB limit.")
    try:
        import rasterio
        from rasterio.io import MemoryFile
    except ImportError as exc:
        raise PairedRasterError("GeoTIFF dependency rasterio is not installed.") from exc
    try:
        with MemoryFile(bytes(raw)) as memfile:
            with memfile.open() as ds:
                if ds.driver != "GTiff" or ds.crs is None:
                    raise PairedRasterError(f"{label}: a GeoTIFF with an explicit CRS is required.")
                if ds.width <= 0 or ds.height <= 0 or ds.width * ds.height > MAX_PIXEL_COUNT:
                    raise PairedRasterError(f"{label}: raster exceeds the 5-million-pixel safety limit.")
                if ds.count < 4:
                    raise PairedRasterError(f"{label}: expected named B03, B04, B08 and SCL bands.")
                names = [str(v).strip().upper() if v else "" for v in ds.descriptions]
                if any(not name for name in names) or len(set(names)) != len(names):
                    raise PairedRasterError(f"{label}: all bands need unique, explicit descriptions.")
                if not {"B03", "B04", "B08", "SCL"}.issubset(names):
                    raise PairedRasterError(f"{label}: required band descriptions B03, B04, B08 and SCL are missing.")
                if not np.all(np.isfinite(ds.transform[:6])) or abs(ds.transform.determinant) < 1e-20:
                    raise PairedRasterError(f"{label}: invalid or singular affine transform.")
                idx = {name: names.index(name) + 1 for name in ("B03", "B04", "B08", "SCL")}
                bands = {}
                for name in ("B03", "B04", "B08"):
                    masked = ds.read(idx[name], masked=True).astype("float64")
                    bands[name] = masked.filled(np.nan)
                scl_masked = ds.read(idx["SCL"], masked=True)
                scl = np.asarray(scl_masked.filled(0))
                if not np.all(np.isfinite(scl)) or not np.all(scl == np.floor(scl)):
                    raise PairedRasterError(f"{label}: SCL must contain finite integer class codes.")
                band_scales = {name: float(ds.scales[idx[name] - 1]) for name in ("B03", "B04", "B08")}
                band_offsets = {name: float(ds.offsets[idx[name] - 1]) for name in ("B03", "B04", "B08")}
                if not all(np.isfinite(v) for v in (*band_scales.values(), *band_offsets.values())):
                    raise PairedRasterError(f"{label}: band scale/offset metadata must be finite.")
                return {
                    "raw_sha256": hashlib.sha256(raw).hexdigest(),
                    "band_scales": band_scales,
                    "band_offsets": band_offsets,
                    "metadata_tags": _safe_metadata_tags(ds.tags()),
                    "band_metadata_tags": {
                        name: _safe_metadata_tags(ds.tags(idx[name]))
                        for name in ("B03", "B04", "B08", "SCL")
                    },
                    "crs": str(ds.crs),
                    "width": int(ds.width),
                    "height": int(ds.height),
                    "transform": tuple(float(v) for v in ds.transform[:6]),
                    "bands": bands,
                    "scl": scl.astype(np.int32),
                    "descriptions": names,
                    "nodata": {name: (float(ds.nodatavals[idx[name] - 1]) if ds.nodatavals[idx[name] - 1] is not None and np.isfinite(ds.nodatavals[idx[name] - 1]) else None) for name in idx},
                }
    except PairedRasterError:
        raise
    except Exception as exc:
        raise PairedRasterError(f"{label}: file could not be opened or validated as GeoTIFF.") from exc


def compare_uploaded_geotiff_pair(
    earlier_bytes: bytes,
    later_bytes: bytes,
    *,
    earlier_acquired_at: str,
    later_acquired_at: str,
    earlier_reflectance_scale_id: str,
    later_reflectance_scale_id: str,
    earlier_processing_baseline: str,
    later_processing_baseline: str,
    aoi_geojson_bytes: bytes | None = None,
    aoi_crs_confirmed_same_as_rasters: bool = False,
    ndvi_change_threshold: float = 0.15,
    ndwi_change_threshold: float = 0.15,
    minimum_valid_fraction: float = 0.7,
) -> dict[str, Any]:
    """Validate two local GeoTIFFs and compare only their shared valid pixels.

    Product/scale/baseline labels are supplied by the operator and are not
    independently authenticated. The same declared labels are applied to both
    files; reviewers must verify them against original product metadata.
    """
    scale_a = earlier_reflectance_scale_id.strip() if isinstance(earlier_reflectance_scale_id, str) else ""
    scale_b = later_reflectance_scale_id.strip() if isinstance(later_reflectance_scale_id, str) else ""
    baseline_a = earlier_processing_baseline.strip() if isinstance(earlier_processing_baseline, str) else ""
    baseline_b = later_processing_baseline.strip() if isinstance(later_processing_baseline, str) else ""
    for label, value in (("earlier reflectance scale/product", scale_a), ("later reflectance scale/product", scale_b),
                         ("earlier processing baseline", baseline_a), ("later processing baseline", baseline_b)):
        if not value or len(value) > 120:
            raise PairedRasterError(f"Provide a concise, source-metadata-checked {label} identifier (1–120 characters).")
    if scale_a != scale_b:
        raise PairedRasterError("Reflectance scale/product identifiers differ between dates; comparison blocked.")
    if baseline_a != baseline_b:
        raise PairedRasterError("Processing baseline identifiers differ between dates; comparison blocked.")
    a = _read_pair_source(earlier_bytes, "Earlier raster")
    b = _read_pair_source(later_bytes, "Later raster")
    for label, source, declared_baseline in (
        ("Earlier", a, baseline_a),
        ("Later", b, baseline_b),
    ):
        embedded_baseline = source["metadata_tags"].get("PROCESSING_BASELINE")
        if embedded_baseline and embedded_baseline != declared_baseline:
            raise PairedRasterError(
                f"{label} raster embedded PROCESSING_BASELINE tag conflicts with the operator declaration; comparison blocked."
            )
    if (a["crs"], a["width"], a["height"], a["transform"]) != (b["crs"], b["width"], b["height"], b["transform"]):
        raise PairedRasterError("CRS, dimensions or affine transform differ between dates; comparison blocked without reprojection/resampling.")
    if a["band_scales"] != b["band_scales"] or a["band_offsets"] != b["band_offsets"]:
        raise PairedRasterError("Embedded spectral-band scales or offsets differ between dates; comparison blocked.")
    aoi_mask = np.ones((a["height"], a["width"]), dtype=bool)
    aoi_digest = None
    if aoi_geojson_bytes is not None:
        if not aoi_crs_confirmed_same_as_rasters:
            raise PairedRasterError("Confirm the AOI GeoJSON coordinates already use the exact CRS of both rasters.")
        if not aoi_geojson_bytes or len(aoi_geojson_bytes) > 5 * 1024 * 1024:
            raise PairedRasterError("AOI GeoJSON must be non-empty and no larger than 5 MiB.")
        try:
            from rasterio.features import geometry_mask
            aoi_mask = geometry_mask(
                _aoi_geometries(aoi_geojson_bytes),
                out_shape=(a["height"], a["width"]),
                transform=__import__("affine").Affine(*a["transform"]),
                invert=True,
                all_touched=False,
            )
        except RasterIngestionError as exc:
            raise PairedRasterError(f"AOI rejected: {exc}") from exc
        except Exception as exc:
            raise PairedRasterError("AOI could not be rasterized on the shared raster grid.") from exc
        if not np.any(aoi_mask):
            raise PairedRasterError("AOI does not overlap any pixel on the shared grid.")
        aoi_digest = hashlib.sha256(aoi_geojson_bytes).hexdigest()

    def calculate(src: dict[str, Any], formula: str) -> np.ndarray:
        bands = src["bands"]
        if formula == "NDVI":
            x, y = bands["B08"], bands["B04"]
        else:
            x, y = bands["B03"], bands["B08"]
        denom = x + y
        out = np.full(x.shape, np.nan, dtype=np.float64)
        valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(denom) & (np.abs(denom) > 1e-12)
        np.divide(x - y, denom, out=out, where=valid)
        out[valid] = np.clip(out[valid], -1.0, 1.0)
        return out

    ndvi_a, ndvi_b = calculate(a, "NDVI"), calculate(b, "NDVI")
    ndwi_a, ndwi_b = calculate(a, "NDWI"), calculate(b, "NDWI")
    valid = (
        aoi_mask
        & ~np.isin(a["scl"], list(EXCLUDED_SCL_CLASSES))
        & ~np.isin(b["scl"], list(EXCLUDED_SCL_CLASSES))
        & np.isfinite(a["bands"]["B03"]) & np.isfinite(a["bands"]["B04"]) & np.isfinite(a["bands"]["B08"])
        & np.isfinite(b["bands"]["B03"]) & np.isfinite(b["bands"]["B04"]) & np.isfinite(b["bands"]["B08"])
        & np.isfinite(ndvi_a) & np.isfinite(ndvi_b) & np.isfinite(ndwi_a) & np.isfinite(ndwi_b)
    )
    grid_identity = hashlib.sha256(json.dumps({
        "crs": a["crs"], "width": a["width"], "height": a["height"], "transform": a["transform"]
    }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    try:
        comparison = compare_two_dates(
            earlier={
                "acquired_at": earlier_acquired_at, "source_sha256": a["raw_sha256"],
                "crs": a["crs"], "width": a["width"], "height": a["height"],
                "transform": list(a["transform"]), "grid_id": grid_identity,
                "reflectance_scale_id": scale_a,
                "processing_baseline": baseline_a,
            },
            later={
                "acquired_at": later_acquired_at, "source_sha256": b["raw_sha256"],
                "crs": b["crs"], "width": b["width"], "height": b["height"],
                "transform": list(b["transform"]), "grid_id": grid_identity,
                "reflectance_scale_id": scale_b,
                "processing_baseline": baseline_b,
            },
            earlier_ndvi=ndvi_a, later_ndvi=ndvi_b,
            earlier_ndwi=ndwi_a, later_ndwi=ndwi_b,
            shared_valid_mask=valid,
            comparison_domain_mask=aoi_mask,
            ndvi_change_threshold=ndvi_change_threshold,
            ndwi_change_threshold=ndwi_change_threshold,
            minimum_valid_fraction=minimum_valid_fraction,
        )
    except ChangeComparisonError as exc:
        raise PairedRasterError(str(exc)) from exc
    comparison["source"] = {
        "earlier": {"sha256": a["raw_sha256"], "crs": a["crs"], "width": a["width"], "height": a["height"], "band_descriptions": a["descriptions"], "nodata": a["nodata"], "spectral_band_scales": a["band_scales"], "spectral_band_offsets": a["band_offsets"], "metadata_tags": a["metadata_tags"], "band_metadata_tags": a["band_metadata_tags"]},
        "later": {"sha256": b["raw_sha256"], "crs": b["crs"], "width": b["width"], "height": b["height"], "band_descriptions": b["descriptions"], "nodata": b["nodata"], "spectral_band_scales": b["band_scales"], "spectral_band_offsets": b["band_offsets"], "metadata_tags": b["metadata_tags"], "band_metadata_tags": b["band_metadata_tags"]},
        "aoi_geojson_sha256": aoi_digest,
        "earlier_reflectance_scale_id_operator_supplied": scale_a,
        "later_reflectance_scale_id_operator_supplied": scale_b,
        "earlier_processing_baseline_operator_supplied": baseline_a,
        "later_processing_baseline_operator_supplied": baseline_b,
        "resampling_performed": False,
        "remote_assets_downloaded": False,
    }
    comparison["limitations"].extend([
        "Operator-declared reflectance scale/product and processing baseline labels are compared for exact equality but are not independently authenticated.",
        "Embedded GeoTIFF scales and offsets are read and compared exactly for the B03, B04 and B08 bands. Matching values (including default 1.0/0.0 values) do not prove that pixel values are physically scaled reflectance; verify original provider metadata and processing history.",
        "Only a short allowlist of embedded metadata tags is included in provenance; tags are untrusted file claims and are not authenticated by this workflow.",
        "Both dates use the same AOI and conservative SCL exclusion policy; valid pixels are the intersection of both dates.",
        "This local paired-raster workflow does not independently validate atmospheric correction, acquisition metadata, or the scientific suitability of the chosen threshold.",
        "Seasonal phenology, rainfall, water-level variation, illumination, viewing geometry and land-management cycles can change NDVI/NDWI without a harmful or persistent land-cover change; compare like seasons and contextual records before interpretation.",
        "The SCL class exclusion policy reduces some cloud, shadow and invalid-pixel contamination but cannot guarantee cloud-free observations; inspect source imagery, cloud edges, haze, shadows and residual artefacts.",
        "A two-date difference is a screening signal only; it cannot by itself distinguish temporary seasonal variation from persistent change or establish cause, area, legal status or responsibility.",
    ])
    comparison["aoi_pixel_count"] = int(np.count_nonzero(aoi_mask))
    comparison["processing_report_sha256"] = hashlib.sha256(
        json.dumps(comparison, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    return comparison
