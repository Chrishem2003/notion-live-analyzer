import json

import numpy as np
import pytest
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from nema_agora.raster_ingestion import RasterIngestionError, process_uploaded_geotiff


def make_raster(*, descriptions=("B03", "B04", "B08", "SCL"), crs="EPSG:32636"):
    data = np.array([
        [[3000, 2000], [4000, 1000]],
        [[2000, 1000], [3000, 1000]],
        [[6000, 4000], [5000, 3000]],
        [[4, 4], [3, 4]],
    ], dtype=np.uint16)
    with MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff", height=2, width=2, count=4, dtype="uint16",
            crs=crs, transform=from_origin(500000, 1000000, 10, 10), nodata=0,
        ) as ds:
            ds.write(data)
            for i, name in enumerate(descriptions, 1):
                ds.set_band_description(i, name)
        return memfile.read()


def test_valid_geotiff_returns_indices_and_provenance_hashes():
    report = process_uploaded_geotiff(make_raster())
    assert report["state"] == "RASTER_SCREENING_REPORT_REVIEW_REQUIRED"
    assert report["indices"]["NDVI"]["valid_pixel_count"] == 3
    assert report["source"]["crs"] == "EPSG:32636"
    assert report["source"]["resampling_performed"] is False
    assert len(report["source"]["source_sha256"]) == 64
    assert len(report["processing_report_sha256"]) == 64


def test_missing_band_descriptions_fail_closed():
    with pytest.raises(RasterIngestionError, match="description"):
        process_uploaded_geotiff(make_raster(descriptions=("", "B04", "B08", "SCL")))


def test_missing_crs_fails_closed():
    with pytest.raises(RasterIngestionError, match="no CRS"):
        process_uploaded_geotiff(make_raster(crs=None))


def test_aoi_requires_same_crs_attestation_and_overlap():
    raster = make_raster()
    aoi = json.dumps({
        "type": "Polygon",
        "coordinates": [[[500000, 1000000], [500020, 1000000], [500020, 999980], [500000, 999980], [500000, 1000000]]],
    }).encode()
    with pytest.raises(RasterIngestionError, match="Confirm"):
        process_uploaded_geotiff(raster, aoi_geojson_bytes=aoi)
    report = process_uploaded_geotiff(raster, aoi_geojson_bytes=aoi, aoi_crs_confirmed_same_as_raster=True)
    assert report["source"]["aoi_handling"].startswith("GeoJSON rasterized")
    assert report["quality"]["aoi_pixel_count"] > 0


def test_bad_bytes_are_rejected():
    with pytest.raises(RasterIngestionError):
        process_uploaded_geotiff(b"not a raster")
