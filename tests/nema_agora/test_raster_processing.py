from nema_agora.raster_processing import *
G={"type":"Polygon","coordinates":[[[32,0],[32.1,0],[32.1,0.1],[32,0]]]}
B=[{"band_id":f"B-{x}","band":x,"width":100,"height":100,"dtype":"uint16","resolution_m":10} for x in ("B02","B03","B04","B08")]
def r(mask=False): return build_raster_input("SCENE-072",G,B,valid_fraction=.95,cloud_mask_applied=mask)
def test_valid_input(): assert validate_raster_input(r())["state"]=="VALID"
def test_processing_requires_cloud_mask(): assert process_raster(r())["state"]=="CONTROL_REQUIRED"
def test_processing_succeeds(): assert process_raster(r(True))["state"]=="PROCESSED"
def test_missing_band_fails(): x=r();x["bands"]=B[:3];assert validate_raster_input(x)["state"]=="CONTROL_REQUIRED"
def test_bad_fraction_fails(): x=r();x["valid_fraction"]=1.5;assert validate_raster_input(x)["state"]=="CONTROL_REQUIRED"
def test_fingerprint_deterministic(): assert r()["input_fingerprint"]==r()["input_fingerprint"]