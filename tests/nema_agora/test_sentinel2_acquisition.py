from nema_agora.sentinel2_acquisition import *
G={"type":"Polygon","coordinates":[[[32,0],[32.1,0],[32.1,0.1],[32,0]]]}
def r(): return build_acquisition_request("REQ-071","DEMO-WETLAND-001",G,"COPERNICUS/S2_SR_HARMONIZED","2026-09-01","2026-10-01")
def test_ready(): assert validate_acquisition_request(r())["state"]=="READY"
def test_not_connected_is_explicit(): assert acquisition_boundary(r())["state"]=="ACQUISITION_NOT_CONNECTED"
def test_reversed_dates_fail(): x=r();x["start_date"]="2026-11-01";assert validate_acquisition_request(x)["state"]=="CONTROL_REQUIRED"
def test_bad_cloud_fails(): x=r();x["max_cloud_cover_pct"]=101;assert validate_acquisition_request(x)["state"]=="CONTROL_REQUIRED"
def test_duplicate_scene_fails(): s={"scene_id":"S1","provider":"google-earth-engine"};assert validate_scene_list([s,s])["state"]=="CONTROL_REQUIRED"