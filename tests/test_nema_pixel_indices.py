import numpy as np
import pytest

from nema_agora.pixel_indices import (
    EXCLUDED_SCL_CLASSES,
    PixelProcessingError,
    process_sentinel2_bands,
)


def inputs():
    green = np.array([[0.3, 0.2], [0.4, 0.1]], dtype=float)
    red = np.array([[0.2, 0.1], [0.3, 0.1]], dtype=float)
    nir = np.array([[0.6, 0.4], [0.5, 0.3]], dtype=float)
    scl = np.array([[4, 4], [3, 4]], dtype=np.uint8)
    return green, red, nir, scl


def test_computes_ndvi_and_mcfeeters_ndwi_with_cloud_mask():
    green, red, nir, scl = inputs()
    report = process_sentinel2_bands(b03_green=green, b04_red=red, b08_nir=nir, scl=scl)
    assert report["indices"]["NDVI"]["valid_pixel_count"] == 3
    assert report["indices"]["NDWI_MCFEETERS"]["valid_pixel_count"] == 3
    assert report["quality"]["masked_scl_pixel_count"] == 1
    assert report["indices"]["NDVI"]["median"] == pytest.approx(0.5)
    assert len(report["report_sha256"]) == 64
    assert report["quality"]["grid_alignment_verified_by_processor"] is False


def test_nonfinite_values_and_zero_denominators_are_excluded_not_zero_filled():
    green, red, nir, scl = inputs()
    green[0, 0] = np.nan
    red[0, 1] = -0.4
    nir[0, 1] = 0.4
    report = process_sentinel2_bands(b03_green=green, b04_red=red, b08_nir=nir, scl=scl)
    assert report["indices"]["NDVI"]["valid_pixel_count"] == 2
    assert report["indices"]["NDWI_MCFEETERS"]["valid_pixel_count"] == 2
    assert report["quality"]["nonfinite_band_pixel_count"] == 1
    assert report["quality"]["zero_or_invalid_denominator_ndvi_count"] == 1


def test_aoi_mask_limits_valid_pixel_fraction_denominator():
    green, red, nir, scl = inputs()
    aoi = np.array([[True, False], [False, False]], dtype=bool)
    report = process_sentinel2_bands(b03_green=green, b04_red=red, b08_nir=nir, scl=scl, aoi_mask=aoi)
    assert report["quality"]["aoi_pixel_count"] == 1
    assert report["indices"]["NDVI"]["valid_pixel_fraction_within_aoi"] == pytest.approx(1.0)


@pytest.mark.parametrize("bad", [
    np.ones((2, 3)),
    np.array([1, 2]),
])
def test_mismatched_or_non_2d_band_shapes_fail_closed(bad):
    green, red, nir, scl = inputs()
    with pytest.raises(PixelProcessingError):
        process_sentinel2_bands(b03_green=green, b04_red=red, b08_nir=bad, scl=scl)


def test_non_boolean_aoi_mask_is_rejected():
    green, red, nir, scl = inputs()
    with pytest.raises(PixelProcessingError, match="boolean array"):
        process_sentinel2_bands(b03_green=green, b04_red=red, b08_nir=nir, scl=scl, aoi_mask=np.ones((2, 2), dtype=int))


def test_invalid_scl_codes_are_excluded_conservatively():
    green, red, nir, scl = inputs()
    scl[0, 0] = 10
    report = process_sentinel2_bands(b03_green=green, b04_red=red, b08_nir=nir, scl=scl)
    assert report["indices"]["NDVI"]["valid_pixel_count"] == 2
    assert 10 in EXCLUDED_SCL_CLASSES


def test_empty_valid_pixels_report_null_statistics():
    green, red, nir, scl = inputs()
    scl[:] = 9
    report = process_sentinel2_bands(b03_green=green, b04_red=red, b08_nir=nir, scl=scl)
    assert report["indices"]["NDVI"]["valid_pixel_count"] == 0
    assert report["indices"]["NDVI"]["mean"] is None
    assert report["indices"]["NDWI_MCFEETERS"]["median"] is None
