import pytest
from nema_agora.stac_discovery import (
    COLLECTION, STAC_API, StacDiscoveryError, discover_scenes, validate_search,
)


def feature(item_id="scene-001", cloud=12.0, collection=COLLECTION):
    return {
        "type": "Feature", "id": item_id, "collection": collection,
        "geometry": {"type": "Polygon", "coordinates": []},
        "properties": {"datetime": "2026-01-10T10:30:00Z", "eo:cloud_cover": cloud, "platform": "sentinel-2b"},
        "assets": {"visual": {"href": "https://assets.example/preview.tif", "type": "image/tiff; application=geotiff"},
                   "unsafe": {"href": "http://example.invalid/file.tif"}},
    }


def test_search_rejects_bad_bbox_and_date_range():
    with pytest.raises(StacDiscoveryError):
        validate_search(aoi_id="AOI-01", bbox=[1, 3, 2, 4], start_date="2026-01-01", end_date="2026-01-02")
    with pytest.raises(StacDiscoveryError):
        validate_search(aoi_id="AOI-01", bbox=[1, 2, 3, 4], start_date="2026-02-01", end_date="2026-01-01")


def test_search_is_fixed_to_allowlisted_provider_and_never_downloads_pixels():
    calls = []
    def fake_request(url, *, payload, timeout):
        calls.append((url, payload, timeout))
        return {"type": "FeatureCollection", "features": [feature()]}
    report = discover_scenes(aoi_id="AOI-01", bbox=[32.0, 0.5, 33.0, 1.5],
                             start_date="2026-01-01", end_date="2026-01-31",
                             request_json=fake_request)
    assert calls[0][0] == f"{STAC_API}/search"
    assert calls[0][1]["collections"] == [COLLECTION]
    assert report["state"] == "SCENES_FOUND_REQUIRING_ASSET_REVIEW"
    assert report["scenes"][0]["provenance"]["pixel_downloaded"] is False
    assert "unsafe" not in report["scenes"][0]["assets"]


def test_scene_with_unknown_cloud_cover_is_rejected():
    report = discover_scenes(aoi_id="AOI-01", bbox=[32.0, 0.5, 33.0, 1.5],
                             start_date="2026-01-01", end_date="2026-01-31",
                             request_json=lambda *a, **k: {"features": [feature(cloud=None)]})
    assert report["scenes"] == []
    assert report["rejected"][0]["reason"] == "MISSING_OR_INVALID_CLOUD_COVER"


def test_nonmatching_collection_is_rejected_without_asset_exposure():
    report = discover_scenes(aoi_id="AOI-01", bbox=[32.0, 0.5, 33.0, 1.5],
                             start_date="2026-01-01", end_date="2026-01-31",
                             request_json=lambda *a, **k: {"features": [feature(collection="other")]})
    assert report["scenes"] == []
    assert "not from the configured" in report["rejected"][0]["reason"]


def test_catalogue_errors_fail_closed():
    def fail(*a, **k):
        raise TimeoutError("timeout")
    with pytest.raises(StacDiscoveryError, match="Catalogue request failed"):
        discover_scenes(aoi_id="AOI-01", bbox=[32.0, 0.5, 33.0, 1.5],
                        start_date="2026-01-01", end_date="2026-01-31", request_json=fail)
