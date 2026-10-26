import copy

from nema_agora.source_registry import SOURCES, list_sources, validate_source_registry


def test_real_world_source_catalogue_is_valid_and_explicitly_not_connected():
    report = validate_source_registry()
    assert report["state"] == "VALID"
    assert report["source_count"] >= 5
    assert report["findings"] == []
    assert all(item["integration_status"] == "reference_only" for item in SOURCES)
    assert all(item["machine_endpoint_verified"] is False for item in SOURCES)
    assert all(item["automated_ingestion_enabled"] is False for item in SOURCES)


def test_catalogue_covers_uganda_policy_research_wetlands_and_satellite_sources():
    source_ids = {item["source_id"] for item in SOURCES}
    assert {
        "UG-NEMA-ACT-CAP181",
        "UG-NEMA-NERA-2024-2029",
        "UG-NEMA-STRATEGIC-PLAN-2025-2030",
        "UG-NEMA-NSOER-2024",
        "UG-MWE-WEIS-WETLANDS",
        "COPERNICUS-SENTINEL-2",
    } <= source_ids
    assert len(list_sources(source_type="satellite_data_catalogue")) == 1


def test_registry_fails_closed_on_unsupported_live_integration_claims():
    modified = [copy.deepcopy(item) for item in SOURCES]
    modified[0]["automated_ingestion_enabled"] = True
    report = validate_source_registry(modified)
    assert report["state"] == "CONTROL_REQUIRED"
    assert {"code": "SOURCE_0_UNVERIFIED_INGESTION_CLAIM"} in report["findings"]


def test_registry_rejects_duplicate_ids_and_non_https_urls():
    modified = [copy.deepcopy(item) for item in SOURCES]
    modified[1]["source_id"] = modified[0]["source_id"]
    modified[1]["url"] = "http://example.invalid/source"
    report = validate_source_registry(modified)
    assert report["state"] == "CONTROL_REQUIRED"
    assert {"code": "SOURCE_1_DUPLICATE_ID"} in report["findings"]
    assert {"code": "SOURCE_1_URL_NOT_HTTPS"} in report["findings"]
