from nema_agora.spatial_map_layers import build_map_layers
def m(): return {"state":"MAP_READY","map_id":"MAP1","baseline_scene_id":"B","comparison_scene_id":"C","cells":[{"row":0,"col":0,"changed":True,"reason_codes":["NDVI_CHANGE_THRESHOLD_MET"]}]}
def test_layers_ready(): x=build_map_layers(aoi={"asset_id":"AOI1"},change_map=m());assert x["state"]=="LAYERS_READY";assert x["layer_count"]==5
def test_fail_closed(): assert build_map_layers(aoi={},change_map=m())["state"]=="CONTROL_REQUIRED"
def test_deterministic(): assert build_map_layers(aoi={"asset_id":"A"},change_map=m())["fingerprint"]==build_map_layers(aoi={"asset_id":"A"},change_map=m())["fingerprint"]
