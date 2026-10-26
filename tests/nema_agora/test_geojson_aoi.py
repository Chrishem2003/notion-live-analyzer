from __future__ import annotations

import json

from nema_agora.geojson_aoi import validate_geojson_aoi


def _polygon():
    return {
        "type": "Feature",
        "properties": {"name": "synthetic test polygon"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [32.50, 0.30], [32.51, 0.30], [32.51, 0.31],
                [32.50, 0.31], [32.50, 0.30],
            ]],
        },
    }


def test_valid_feature_polygon_returns_wgs84_bounds():
    report = validate_geojson_aoi(_polygon())
    assert report["valid"] is True
    assert report["bounds"] == {
        "west": 32.5, "south": 0.3, "east": 32.51, "north": 0.31,
    }
    assert report["coordinate_reference"].startswith("WGS84")


def test_json_text_and_multipolygon_are_supported():
    feature = _polygon()["geometry"]
    multi = {"type": "MultiPolygon", "coordinates": [[feature["coordinates"][0]]]}
    assert validate_geojson_aoi(json.dumps(multi))["valid"] is True


def test_rejects_unclosed_ring_and_out_of_range_coordinates():
    doc = _polygon()
    doc["geometry"]["coordinates"][0][-1] = [200, 0.30]
    report = validate_geojson_aoi(doc)
    codes = {f["code"] for f in report["findings"]}
    assert "GEOMETRY_0_RING_0_INVALID_POSITION" in codes
    assert "GEOMETRY_0_RING_0_RING_NOT_CLOSED" in codes


def test_rejects_unsupported_geometry_and_invalid_json():
    assert "UNSUPPORTED_GEOJSON_TYPE" in {
        f["code"] for f in validate_geojson_aoi({"type": "Point", "coordinates": [32, 0]})["findings"]
    }
    assert validate_geojson_aoi("{bad")["findings"] == [{"code": "INVALID_JSON"}]


def test_flags_ring_that_is_not_closed():
    doc = _polygon()
    doc["geometry"]["coordinates"][0] = [
        [32.5, 0.3], [32.51, 0.3], [32.51, 0.31], [32.5, 0.31]
    ]
    report = validate_geojson_aoi(doc)
    assert "GEOMETRY_0_RING_0_RING_NOT_CLOSED" in {
        f["code"] for f in report["findings"]
    }


def test_does_not_claim_legal_boundary_or_topological_validation():
    report = validate_geojson_aoi(_polygon())
    assert any("not verified as an official" in item for item in report["limitations"])
    assert any("self-intersection" in item for item in report["limitations"])
