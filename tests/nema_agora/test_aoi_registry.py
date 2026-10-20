from nema_agora.aoi_registry import *
G={"type":"Polygon","coordinates":[[[32,0],[32.1,0],[32.1,0.1],[32,0]]]}
def a(i="AOI-001"): return build_asset(i,"Demo Wetland","WETLAND",G,"SYNTHETIC","DEMO-REF")
def test_valid_registry(): assert validate_registry([a()])["state"]=="REGISTRY_READY"
def test_duplicate_fails(): assert validate_registry([a(),a()])["state"]=="CONTROL_REQUIRED"
def test_bad_crs_fails(): x=a();x["crs"]="EPSG:3857";assert validate_registry([x])["state"]=="CONTROL_REQUIRED"
def test_query_deterministic(): assert [x["asset_id"] for x in query_assets([a("B"),a("A")])]==["A","B"]
def test_bad_source_reference_fails(): x=a();x["source_reference"]="";assert validate_asset(x)["state"]=="CONTROL_REQUIRED"