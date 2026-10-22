"""Contract tests for the fail-closed Earth Engine boundary."""
from nema_agora.aoi_registry import build_asset
from nema_agora.gee_boundary import execute_scene_request, validate_scene_request

GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[[32.0, 0.0], [32.1, 0.0], [32.1, 0.1], [32.0, 0.0]]],
}


def asset():
    return build_asset(
        "AOI-001",
        "Synthetic wetland",
        "WETLAND",
        GEOMETRY,
        "SYNTHETIC",
        "DEMO-REFERENCE",
        status="ACTIVE",
    )


def test_scene_request_validates_governed_aoi_and_bounded_window():
    result = validate_scene_request(asset(), "2026-09-01", "2026-10-01")
    assert result["state"] == "REQUEST_VALIDATED"
    assert result["request"]["collection_id"] == "COPERNICUS/S2_SR_HARMONIZED"
    assert result["request"]["end_date_exclusive"] == "2026-10-01"


def test_scene_request_rejects_oversized_window_and_unapproved_collection():
    oversized = validate_scene_request(asset(), "2026-01-01", "2026-05-01")
    assert oversized["state"] == "CONTROL_REQUIRED"
    assert {"code": "DATE_WINDOW_TOO_LARGE"} in oversized["findings"]

    collection = validate_scene_request(asset(), "2026-09-01", "2026-10-01", collection="UNAPPROVED")
    assert collection["state"] == "CONTROL_REQUIRED"
    assert {"code": "COLLECTION_NOT_ALLOWLISTED"} in collection["findings"]


def test_missing_provider_never_fakes_live_earth_engine_access():
    request = validate_scene_request(asset(), "2026-09-01", "2026-10-01")
    result = execute_scene_request(request, provider=None, credentials_configured=True)
    assert result["state"] == "PROVIDER_ERROR"
    assert result["findings"] == [{"code": "SCENE_PROVIDER_MISSING"}]
    assert result["scenes"] == []


def test_provider_scene_metadata_is_validated_filtered_and_sorted():
    class Provider:
        def list_scenes(self, request):
            return [
                {"scene_id": "S2-B", "acquired_date": "2026-09-05", "cloud_percent": 20},
                {"scene_id": "S2-CLOUDY", "acquired_date": "2026-09-04", "cloud_percent": 90},
                {"scene_id": "S2-A", "acquired_date": "2026-09-03", "cloud_percent": 10},
            ]

    request = validate_scene_request(asset(), "2026-09-01", "2026-10-01", cloud_max=30)
    result = execute_scene_request(request, provider=Provider(), credentials_configured=True)
    assert result["state"] == "PROVIDER_QUERY_COMPLETE"
    assert [scene["scene_id"] for scene in result["scenes"]] == ["S2-A", "S2-B"]
    assert result["scene_count"] == 2
    assert "not a compliance finding" in result["evidence_note"]
