from nema_agora.aoi_registry import *
G={"type":"Polygon","coordinates":[[[32,0],[32.1,0],[32.1,0.1],[32,0]]]}
def a(i="AOI-001"): return build_asset(i,"Demo Wetland","WETLAND",G,"SYNTHETIC","DEMO-REF")
def test_valid_registry(): assert validate_registry([a()])["state"]=="REGISTRY_READY"
def test_duplicate_fails(): assert validate_registry([a(),a()])["state"]=="CONTROL_REQUIRED"
def test_bad_crs_fails(): x=a();x["crs"]="EPSG:3857";assert validate_registry([x])["state"]=="CONTROL_REQUIRED"
def test_query_deterministic(): assert [x["asset_id"] for x in query_assets([a("B"),a("A")])]==["A","B"]
def test_bad_source_reference_fails(): x=a();x["source_reference"]="";assert validate_asset(x)["state"]=="CONTROL_REQUIRED"

def test_geometry_requires_closed_valid_polygon_ring():
 x=a()
 x["geometry"]={"type":"Polygon","coordinates":[[[32,0],[32.1,0],[32.1,0.1],[32.2,0.2]]]}
 assert "INVALID_GEOMETRY" in {item["code"] for item in validate_asset(x)["findings"]}

def test_geometry_rejects_out_of_range_and_non_finite_coordinates():
 x=a()
 x["geometry"]={"type":"Point","coordinates":[200,0]}
 assert validate_asset(x)["state"]=="CONTROL_REQUIRED"
 x=a()
 x["geometry"]={"type":"Point","coordinates":[float("nan"),0]}
 assert validate_asset(x)["state"]=="CONTROL_REQUIRED"

def test_geometry_accepts_closed_polygon_and_valid_point():
 x=a()
 assert validate_asset(x)["state"]=="VALID"
 x=build_asset("AOI-POINT","Demo Point","CUSTOM",{"type":"Point","coordinates":[32.0,0.0]},"SYNTHETIC","DEMO-POINT")
 assert validate_asset(x)["state"]=="VALID"

def test_multipolygon_requires_valid_rings():
 valid_geometry={"type":"MultiPolygon","coordinates":[[[[32,0],[32.1,0],[32.1,0.1],[32,0]]]]}
 x=build_asset("AOI-MULTI","Demo Multi","WETLAND",valid_geometry,"SYNTHETIC","DEMO-MULTI")
 assert validate_asset(x)["state"]=="VALID"
 x=a()
 x["geometry"]={"type":"MultiPolygon","coordinates":[[[[32,0],[32.1,0],[32.1,0.1]]]]}
 x.pop("asset_fingerprint",None)
 result=validate_asset(x)
 assert result["state"]=="CONTROL_REQUIRED"
 assert "INVALID_GEOMETRY" in {item["code"] for item in result["findings"]}


def test_registry_rejects_non_mapping_and_unhashable_asset_ids_without_crashing():
 assert validate_registry([None])["state"]=="CONTROL_REQUIRED"
 malformed={"asset_id":["not","hashable"],"name":"bad"}
 result=validate_registry([malformed])
 assert result["state"]=="CONTROL_REQUIRED"
 assert "INVALID_ASSET_ID" in {item["code"] for item in result["findings"]}

def test_registry_only_detects_duplicates_for_valid_string_ids():
 result=validate_registry([{"asset_id":["x"]},{"asset_id":["x"]}])
 assert result["state"]=="CONTROL_REQUIRED"
 assert "DUPLICATE_ASSET_ID" not in {item["code"] for item in result["findings"]}


def test_asset_fingerprint_detects_tampered_geometry():
 x=a()
 assert validate_asset(x)["state"]=="VALID"
 x["geometry"]["coordinates"][0][1][0]=32.2
 result=validate_asset(x)
 assert result["state"]=="CONTROL_REQUIRED"
 assert "ASSET_FINGERPRINT_MISMATCH" in {item["code"] for item in result["findings"]}

def test_asset_fingerprint_is_checked_during_registry_validation():
 x=a()
 x["source"]="ALTERED"
 result=validate_registry([x])
 assert result["state"]=="CONTROL_REQUIRED"
 assert "ASSET_FINGERPRINT_MISMATCH" in {item["code"] for item in result["findings"]}
