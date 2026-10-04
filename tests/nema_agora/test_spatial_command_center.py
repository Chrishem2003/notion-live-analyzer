from nema_agora.spatial_command_center import build_command_center
def test_ready():
 m={"state":"MAP_READY","map_id":"MAP-1","baseline_scene_id":"S1","comparison_scene_id":"S2","grid_shape":[1,1],"cells":[{"changed":True}],"summary":{"changed_cells":1,"total_cells":1}}
 x=build_command_center(aoi={"asset_id":"AOI1","name":"Demo"},change_map=m);assert x["state"]=="COMMAND_CENTER_READY";assert x["map"]["changed_cells"]==1
def test_fail_closed(): assert build_command_center(aoi={"asset_id":"A"},change_map={"state":"CONTROL_REQUIRED"})["state"]=="CONTROL_REQUIRED"
def test_deterministic():
 m={"state":"MAP_READY","map_id":"MAP-1","baseline_scene_id":"S1","comparison_scene_id":"S2","grid_shape":[1,1],"cells":[]}
 a=build_command_center(aoi={"asset_id":"A"},change_map=m);b=build_command_center(aoi={"asset_id":"A"},change_map=m);assert a["fingerprint"]==b["fingerprint"]
