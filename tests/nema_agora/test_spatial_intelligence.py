from nema_agora.spatial_intelligence import aoi, spatial_analysis_contract, spatial_observation, validate_aoi, validate_coordinate, validate_geometry, validate_spatial_observation

def test_coordinate_validation_is_fail_closed():
    assert validate_coordinate(1, 2) == []
    assert validate_coordinate(91, 2)[0]["code"] == "LATITUDE_OUT_OF_RANGE"
    assert validate_coordinate(float("nan"), 2)[0]["code"] == "INVALID_LATITUDE"

def test_geometry_and_aoi_validation():
    good = {"type": "Point", "coordinates": [32.58, 0.35]}
    assert validate_geometry(good) == []
    assert validate_aoi({"aoi_id":"AOI-1","name":"Demo","type":"WETLAND","geometry":good,"crs":"EPSG:4326"})["state"] == "VALID"
    assert validate_aoi({"aoi_id":"bad id","name":"","type":"UNKNOWN","geometry":good,"crs":"EPSG:3857"})["state"] == "CONTROL_REQUIRED"

def test_spatial_observation_is_deterministic_and_geojson_compatible():
    row = spatial_observation("OBS-SPATIAL-1", 0.3476, 32.5825, "synthetic", "2026-10-04T12:00:00Z", accuracy_m=10)
    assert row["geometry"] == {"type":"Point","coordinates":[32.5825,0.3476]}
    first = validate_spatial_observation(row)
    second = validate_spatial_observation(row)
    assert first["state"] == second["state"] == "VALID"
    assert first["observation_fingerprint"] == second["observation_fingerprint"]

def test_spatial_observation_rejects_bad_provider_data():
    result = validate_spatial_observation({"observation_id":"OBS-1","latitude":0,"longitude":0,"crs":"EPSG:3857","source":"","captured_at":""})
    assert result["state"] == "CONTROL_REQUIRED"
    assert {x["code"] for x in result["findings"]} == {"UNSUPPORTED_CRS","MISSING_SOURCE","MISSING_CAPTURE_TIMESTAMP"}

def test_provider_contract_forbids_regulatory_conclusions():
    assert spatial_analysis_contract({"provider":"synthetic","analysis_type":"change_candidate","source_ids":["IMG-1"],"evidence":{"delta":0.2},"confidence":0.7,"metadata":{}})["state"] == "VALID"
    blocked = spatial_analysis_contract({"provider":"synthetic","analysis_type":"change_candidate","source_ids":["IMG-1"],"evidence":{},"conclusion":"illegal wetland filling"})
    assert blocked["state"] == "CONTROL_REQUIRED"
