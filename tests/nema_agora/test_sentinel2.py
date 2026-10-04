from nema_agora.sentinel2 import remote_sensing_evidence, sentinel2_scene, validate_bbox, validate_sentinel2_scene

def test_bbox_is_fail_closed():
    assert validate_bbox([32,0,33,1]) == []
    assert validate_bbox([33,0,32,1])[0]["code"] == "BBOX_WEST_AFTER_EAST"

def test_valid_sentinel2_scene_is_deterministic():
    scene=sentinel2_scene("S2-SCENE-1","S2-PRODUCT-1","2026-10-04T10:30:00Z",12.5,[32,0,33,1])
    first=validate_sentinel2_scene(scene)
    second=validate_sentinel2_scene(scene)
    assert first["state"]=="VALID"
    assert first["scene_fingerprint"]==second["scene_fingerprint"]

def test_invalid_scene_fails_closed():
    result=validate_sentinel2_scene({"scene_id":"S2-1","product_id":"S2-2","collection":"BAD","acquired_at":"bad","crs":"EPSG:3857","bbox":[32,0,33,1],"cloud_cover_pct":101,"bands":["B04"],"provider":""})
    assert result["state"]=="CONTROL_REQUIRED"
    assert {"INVALID_COLLECTION","INVALID_ACQUISITION_TIMESTAMP","UNSUPPORTED_CRS","CLOUD_COVER_OUT_OF_RANGE","REQUIRED_BANDS_MISSING","MISSING_PROVIDER"}.issubset({x["code"] for x in result["findings"]})

def test_evidence_contains_source_metadata_not_regulatory_conclusion():
    scene=sentinel2_scene("S2-SCENE-2","S2-PRODUCT-2","2026-10-04T10:30:00Z",5,[32,0,33,1])
    result=remote_sensing_evidence(scene)
    assert result["state"]=="VALID"
    assert "conclusion" not in result and "violation" not in result
