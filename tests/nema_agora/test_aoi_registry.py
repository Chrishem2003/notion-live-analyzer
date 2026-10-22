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
 x=a()
 x["geometry"]={"type":"Point","coordinates":[32.0,0.0]}
 assert validate_asset(x)["state"]=="VALID"

def test_multipolygon_requires_valid_rings():
 x=a()
 x["geometry"]={"type":"MultiPolygon","coordinates":[[[[32,0],[32.1,0],[32.1,0.1],[32,0]]]]}
 assert validate_asset(x)["state"]=="VALID"
 x["geometry"]={"type":"MultiPolygon","coordinates":[[[[32,0],[32.1,0],[32.1,0.1]]]]}
 assert validate_asset(x)["state"]=="CONTROL_REQUIRED"
