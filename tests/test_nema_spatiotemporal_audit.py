"""Tests for conservative spatial/temporal split separation."""
import pytest

from nema_agora.spatiotemporal_audit import SpatiotemporalAuditError, audit_spatiotemporal_separation


def unit(unit_id, split, bbox, start, end):
    return {"unit_id": unit_id, "split": split, "bbox_wgs84": bbox,
            "observation_start": start, "observation_end": end}


def test_disjoint_boxes_and_dates_have_no_declared_overlap():
    result = audit_spatiotemporal_separation([
        unit("d1", "development", [29, 0, 29.1, 0.1], "2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z"),
        unit("h1", "holdout", [31, 1, 31.1, 1.1], "2025-06-01T00:00:00Z", "2025-06-02T00:00:00Z"),
    ])
    assert result["decision"] == "NO_DECLARED_OVERLAP_FOUND"


def test_spatial_intersection_flags_cross_split_pair():
    result = audit_spatiotemporal_separation([
        unit("d1", "development", [29, 0, 30, 1], "2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z"),
        unit("h1", "holdout", [29.5, 0.5, 30.5, 1.5], "2025-06-01T00:00:00Z", "2025-06-02T00:00:00Z"),
    ])
    assert result["findings"][0]["finding"] == "SPATIAL_OVERLAP"
    assert result["decision"] == "REVIEW_AND_BLOCK_UNTIL_RESOLVED"


def test_temporal_intersection_flags_cross_split_pair():
    result = audit_spatiotemporal_separation([
        unit("d1", "development", [29, 0, 29.1, 0.1], "2025-01-01T00:00:00Z", "2025-02-02T00:00:00Z"),
        unit("h1", "holdout", [31, 1, 31.1, 1.1], "2025-02-01T00:00:00Z", "2025-02-03T00:00:00Z"),
    ])
    assert result["findings"][0]["finding"] == "TEMPORAL_OVERLAP"


@pytest.mark.parametrize("bad", [
    unit("x", "holdout", [29, 0, 29, 1], "2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z"),
    unit("x", "holdout", [29, 0, 30, 1], "2025-01-01", "2025-01-02T00:00:00Z"),
    unit("x", "other", [29, 0, 30, 1], "2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z"),
])
def test_invalid_spatiotemporal_metadata_rejected(bad):
    with pytest.raises(SpatiotemporalAuditError):
        audit_spatiotemporal_separation([bad])
