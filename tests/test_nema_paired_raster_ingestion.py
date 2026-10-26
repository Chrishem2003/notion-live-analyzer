import json

import numpy as np
import pytest
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from nema_agora.paired_raster_ingestion import PairedRasterError, compare_uploaded_geotiff_pair


def make_raster(offset=0, transform=None, crs="EPSG:32636", scales=None, offsets=None):
    base = np.array([
        [[3000, 3100, 3200, 3300], [3100, 3200, 3300, 3400], [3200, 3300, 3400, 3500], [3300, 3400, 3500, 3600]],
        [[2000, 2100, 2200, 2300], [2100, 2200, 2300, 2400], [2200, 2300, 2400, 2500], [2300, 2400, 2500, 2600]],
        [[5000, 5100, 5200, 5300], [5100, 5200, 5300, 5400], [5200, 5300, 5400, 5500], [5300, 5400, 5500, 5600]],
        [[4, 4, 4, 4], [4, 4, 4, 4], [4, 4, 4, 4], [4, 4, 4, 4]],
    ], dtype=np.uint16)
    base[0:3] += offset
    with MemoryFile() as mem:
        with mem.open(driver="GTiff", height=4, width=4, count=4, dtype="uint16",
                      crs=crs, transform=transform or from_origin(500000, 1000000, 10, 10), nodata=0) as ds:
            ds.write(base)
            for i, name in enumerate(("B03", "B04", "B08", "SCL"), 1):
                ds.set_band_description(i, name)
            if scales is not None:
                ds.scales = tuple(scales)
            if offsets is not None:
                ds.offsets = tuple(offsets)
        return mem.read()


def run(a, b, **kwargs):
    return compare_uploaded_geotiff_pair(
        a, b,
        earlier_acquired_at="2026-01-01T10:00:00Z",
        later_acquired_at="2026-02-01T10:00:00Z",
        earlier_reflectance_scale_id=kwargs.pop("earlier_reflectance_scale_id", "L2A-reflectance-1e-4"),
        later_reflectance_scale_id=kwargs.pop("later_reflectance_scale_id", "L2A-reflectance-1e-4"),
        earlier_processing_baseline=kwargs.pop("earlier_processing_baseline", "04.00"),
        later_processing_baseline=kwargs.pop("later_processing_baseline", "04.00"),
        **kwargs,
    )


def test_pair_processes_common_grid_and_returns_provenance():
    report = run(make_raster(), make_raster(offset=100))
    assert report["state"] == "TWO_DATE_SCREENING_REVIEW_REQUIRED"
    assert report["compatibility"]["shared_valid_pixel_count"] == 16
    assert report["compatibility"]["shared_valid_pixel_fraction"] == 1.0
    assert report["source"]["resampling_performed"] is False
    assert len(report["processing_report_sha256"]) == 64


def test_pair_blocks_grid_mismatch():
    with pytest.raises(PairedRasterError, match="dimensions or affine transform differ"):
        run(make_raster(), make_raster(transform=from_origin(500010, 1000000, 10, 10)))


def test_pair_blocks_invalid_dates():
    with pytest.raises(PairedRasterError, match="strictly after"):
        compare_uploaded_geotiff_pair(
            make_raster(), make_raster(),
            earlier_acquired_at="2026-02-01T10:00:00Z",
            later_acquired_at="2026-01-01T10:00:00Z",
            earlier_reflectance_scale_id="scale", later_reflectance_scale_id="scale",
            earlier_processing_baseline="04.00", later_processing_baseline="04.00",
        )


def test_pair_uses_shared_aoi_for_valid_fraction():
    aoi = json.dumps({
        "type": "Polygon",
        "coordinates": [[[500000, 1000000], [500020, 1000000], [500020, 999980], [500000, 999980], [500000, 1000000]]],
    }).encode()
    report = run(make_raster(), make_raster(offset=100), aoi_geojson_bytes=aoi,
                 aoi_crs_confirmed_same_as_rasters=True, minimum_valid_fraction=0.9)
    assert report["aoi_pixel_count"] == 4
    assert report["compatibility"]["coverage_denominator"] == "comparison domain (AOI when supplied)"


def test_pair_requires_aoi_crs_attestation_and_rejects_bad_bytes():
    aoi = json.dumps({"type": "Polygon", "coordinates": []}).encode()
    with pytest.raises(PairedRasterError, match="Confirm"):
        run(make_raster(), make_raster(), aoi_geojson_bytes=aoi)
    with pytest.raises(PairedRasterError, match="could not be opened"):
        run(b"not a GeoTIFF", make_raster())


def test_pair_blocks_different_operator_declared_scaling_or_baseline():
    with pytest.raises(PairedRasterError, match="scale/product identifiers differ"):
        run(make_raster(), make_raster(offset=100), later_reflectance_scale_id="L2A-reflectance-1e-3")
    with pytest.raises(PairedRasterError, match="baseline identifiers differ"):
        run(make_raster(), make_raster(offset=100), later_processing_baseline="05.00")



def test_pair_blocks_embedded_spectral_scale_or_offset_mismatch():
    base_scales = (1.0, 1.0, 1.0, 1.0)
    changed_scales = (0.0001, 1.0, 1.0, 1.0)
    with pytest.raises(PairedRasterError, match="Embedded spectral-band scales or offsets differ"):
        run(make_raster(scales=base_scales), make_raster(offset=100, scales=changed_scales))
    base_offsets = (0.0, 0.0, 0.0, 0.0)
    changed_offsets = (10.0, 0.0, 0.0, 0.0)
    with pytest.raises(PairedRasterError, match="Embedded spectral-band scales or offsets differ"):
        run(make_raster(offsets=base_offsets), make_raster(offset=100, offsets=changed_offsets))
