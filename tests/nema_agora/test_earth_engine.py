from nema_agora.earth_engine import *
G={"type":"Polygon","coordinates":[[[32,0],[32.1,0],[32.1,0.1],[32,0]]]}
def r(): return build_request("REQ-001","DEMO-WETLAND-001",G,"COPERNICUS/S2_SR_HARMONIZED","2026-09-01","2026-10-01")
def test_valid_request(): assert validate_request(r())["state"]=="READY"
def test_boundary_never_fakes_connection(): assert provider_boundary(r())["state"]=="PROVIDER_NOT_CONNECTED"
def test_wrong_provider_fails(): x=r();x["provider"]="fake";assert validate_request(x)["state"]=="CONTROL_REQUIRED"
def test_cloud_limit_fails(): x=r();x["max_cloud_cover_pct"]=101;assert validate_request(x)["state"]=="CONTROL_REQUIRED"
def test_fingerprint_deterministic(): assert r()["request_fingerprint"]==r()["request_fingerprint"]