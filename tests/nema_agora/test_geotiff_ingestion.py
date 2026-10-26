import io

import pytest

rasterio = pytest.importorskip("rasterio")
np = pytest.importorskip("numpy")

from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from nema_agora.geotiff_ingestion import read_geotiff_scene
from nema_agora.paired_raster_array_analysis import analyze_paired_raster_arrays


def _geotiff(values, *, count=None, crs="EPSG:4326", transform=None):
    arr = np.asarray(values, dtype="float32")
    if arr.ndim == 2:
        arr = arr[np.newaxis, :, :]
    count = count or arr.shape[0]
    with MemoryFile() as mem:
        with mem.open(
            driver="GTiff", width=arr.shape[2], height=arr.shape[1],
            count=count, dtype="float32", crs=crs,
            transform=transform or from_origin(32.5, 0.5, 0.0001, 0.0001),
            nodata=-9999,
        ) as dst:
            dst.write(arr)
        return mem.read()


def _mask(values):
    return _geotiff(np.asarray(values, dtype="float32"))


def test_ingests_pair_and_runs_index_analysis():
    base_bytes = _geotiff([
        [[0.4, 0.4], [0.5, 0.3]],
        [[0.2, 0.2], [0.1, 0.3]],
        [[0.6, 0.6], [0.7, 0.5]],
    ])
    comp_bytes = _geotiff([
        [[0.3, 0.4], [0.6, 0.2]],
        [[0.3, 0.2], [0.1, 0.4]],
        [[0.5, 0.6], [0.7, 0.4]],
    ])
    valid = _mask([[1, 1], [1, 1]])
    common = dict(
        valid_mask_bytes=valid, aoi_id="AOI-001", reflectance_scale=1.0,
        cloud_shadow_mask_applied=True,
    )
    baseline = read_geotiff_scene(
        raster_bytes=base_bytes, scene_id="BASE", acquired_at="2026-06-01T10:00:00Z", **common
    )
    comparison = read_geotiff_scene(
        raster_bytes=comp_bytes, scene_id="COMP", acquired_at="2026-09-01T10:00:00Z", **common
    )
    result = analyze_paired_raster_arrays(baseline_scene=baseline, comparison_scene=comparison)
    assert result["state"] == "PIXEL_ANALYSIS_COMPLETE"
    assert baseline["ingestion"]["raster_sha256"]
    assert baseline["ingestion"]["valid_mask_pixels"] == 4


def test_rejects_mismatched_mask_grid_and_non_geographic_crs():
    image = _geotiff([
        [[0.4, 0.4], [0.5, 0.3]],
        [[0.2, 0.2], [0.1, 0.3]],
        [[0.6, 0.6], [0.7, 0.5]],
    ])
    wrong_mask = _geotiff([[1, 1], [1, 1]], transform=from_origin(32.51, 0.5, 0.0001, 0.0001))
    with pytest.raises(ValueError, match="VALID_MASK_TRANSFORM_MISMATCH"):
        read_geotiff_scene(
            raster_bytes=image, valid_mask_bytes=wrong_mask, scene_id="BASE",
            acquired_at="2026-06-01T10:00:00Z", aoi_id="AOI-001",
            reflectance_scale=1.0, cloud_shadow_mask_applied=True,
        )
    projected = _geotiff([
        [[0.4, 0.4], [0.5, 0.3]],
        [[0.2, 0.2], [0.1, 0.3]],
        [[0.6, 0.6], [0.7, 0.5]],
    ], crs="EPSG:32636")
    with pytest.raises(ValueError, match="ONLY_EPSG_4326"):
        read_geotiff_scene(
            raster_bytes=projected, valid_mask_bytes=_mask([[1, 1], [1, 1]]),
            scene_id="BASE", acquired_at="2026-06-01T10:00:00Z",
            aoi_id="AOI-001", reflectance_scale=1.0, cloud_shadow_mask_applied=True,
        )


def test_requires_timezone_mask_assertion_and_valid_scale():
    image = _geotiff([
        [[0.4, 0.4], [0.5, 0.3]],
        [[0.2, 0.2], [0.1, 0.3]],
        [[0.6, 0.6], [0.7, 0.5]],
    ])
    kwargs = dict(
        raster_bytes=image, valid_mask_bytes=_mask([[1, 1], [1, 1]]),
        scene_id="BASE", acquired_at="2026-06-01T10:00:00",
        aoi_id="AOI-001", reflectance_scale=1.0, cloud_shadow_mask_applied=True,
    )
    with pytest.raises(ValueError, match="TIMEZONE_AWARE"):
        read_geotiff_scene(**kwargs)
    kwargs["acquired_at"] = "2026-06-01T10:00:00Z"
    kwargs["cloud_shadow_mask_applied"] = False
    with pytest.raises(ValueError, match="CLOUD_SHADOW_MASK_ASSERTION"):
        read_geotiff_scene(**kwargs)
