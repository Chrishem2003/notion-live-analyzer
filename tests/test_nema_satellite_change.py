import numpy as np
import pytest

from nema_agora.satellite_change import ChangeComparisonError, compare_two_dates


def metadata(acquired_at, **overrides):
    value = {
        "acquired_at": acquired_at,
        "source_sha256": "a" * 64,
        "crs": "EPSG:32636",
        "width": 2,
        "height": 2,
        "transform": [10, 0, 500000, 0, -10, 1000000],
        "grid_id": "grid-sha256-example",
        "reflectance_scale_id": "s2-reflectance-1e-4",
        "processing_baseline": "04.00",
    }
    value.update(overrides)
    return value


def arrays():
    a = np.array([[0.2, 0.4], [0.1, 0.3]])
    b = np.array([[0.4, 0.2], [0.1, 0.6]])
    w = np.array([[0.1, 0.2], [0.3, 0.4]])
    z = np.array([[0.3, 0.2], [0.3, 0.2]])
    valid = np.ones((2, 2), dtype=bool)
    return a, b, w, z, valid


def test_two_date_comparison_reports_deltas_and_hash():
    a, b, w, z, valid = arrays()
    report = compare_two_dates(
        earlier=metadata("2026-01-01T10:00:00Z"),
        later=metadata("2026-02-01T10:00:00Z"),
        earlier_ndvi=a, later_ndvi=b, earlier_ndwi=w, later_ndwi=z,
        shared_valid_mask=valid, ndvi_change_threshold=0.15,
    )
    assert report["state"] == "TWO_DATE_SCREENING_REVIEW_REQUIRED"
    assert report["compatibility"]["shared_valid_pixel_fraction"] == 1.0
    assert report["indices"]["NDVI_delta"]["pixels_above_positive_threshold"] == 2
    assert len(report["report_sha256"]) == 64


def test_comparison_blocks_different_grid_or_scaling():
    a, b, w, z, valid = arrays()
    with pytest.raises(ChangeComparisonError, match="blocked"):
        compare_two_dates(
            earlier=metadata("2026-01-01T10:00:00Z"),
            later=metadata("2026-02-01T10:00:00Z", grid_id="different-grid"),
            earlier_ndvi=a, later_ndvi=b, earlier_ndwi=w, later_ndwi=z,
            shared_valid_mask=valid,
        )


def test_comparison_blocks_naive_dates_and_reversed_order():
    a, b, w, z, valid = arrays()
    with pytest.raises(ChangeComparisonError, match="timezone"):
        compare_two_dates(
            earlier=metadata("2026-01-01T10:00:00"),
            later=metadata("2026-02-01T10:00:00Z"),
            earlier_ndvi=a, later_ndvi=b, earlier_ndwi=w, later_ndwi=z,
            shared_valid_mask=valid,
        )
    with pytest.raises(ChangeComparisonError, match="strictly after"):
        compare_two_dates(
            earlier=metadata("2026-02-01T10:00:00Z"),
            later=metadata("2026-01-01T10:00:00Z"),
            earlier_ndvi=a, later_ndvi=b, earlier_ndwi=w, later_ndwi=z,
            shared_valid_mask=valid,
        )


def test_comparison_blocks_low_shared_valid_fraction():
    a, b, w, z, valid = arrays()
    valid[:] = False
    valid[0, 0] = True
    with pytest.raises(ChangeComparisonError, match="below required"):
        compare_two_dates(
            earlier=metadata("2026-01-01T10:00:00Z"),
            later=metadata("2026-02-01T10:00:00Z"),
            earlier_ndvi=a, later_ndvi=b, earlier_ndwi=w, later_ndwi=z,
            shared_valid_mask=valid, minimum_valid_fraction=0.7,
        )


def test_comparison_requires_boolean_mask_and_same_shapes():
    a, b, w, z, valid = arrays()
    with pytest.raises(ChangeComparisonError, match="boolean"):
        compare_two_dates(
            earlier=metadata("2026-01-01T10:00:00Z"),
            later=metadata("2026-02-01T10:00:00Z"),
            earlier_ndvi=a, later_ndvi=b, earlier_ndwi=w, later_ndwi=z,
            shared_valid_mask=valid.astype(int),
        )
    with pytest.raises(ChangeComparisonError, match="match the declared grid"):
        compare_two_dates(
            earlier=metadata("2026-01-01T10:00:00Z"),
            later=metadata("2026-02-01T10:00:00Z"),
            earlier_ndvi=a, later_ndvi=b[:, :1], earlier_ndwi=w, later_ndwi=z,
            shared_valid_mask=valid,
        )
