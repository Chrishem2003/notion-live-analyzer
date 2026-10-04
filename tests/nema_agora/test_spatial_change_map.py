from nema_agora.spatial_change_map import build_change_map
def grids(): return {"NDVI":[[.7,.7],[.7,.7]],"NDWI_MCFEETERS":[[.3,.3],[.3,.3]],"MSAVI2":[[.65,.65],[.65,.65]]}
def test_map_ready():
 b=grids();c={k:[row[:] for row in v] for k,v in b.items()};c["NDVI"][0][0]=.4;x=build_change_map(baseline_scene_id="S1",comparison_scene_id="S2",aoi_id="AOI1",baseline_indices=b,comparison_indices=c);assert x["state"]=="MAP_READY";assert x["summary"]["changed_cells"]==1
def test_alignment_fail_closed():
 b=grids();c=grids();c["NDVI"]=[[.5]];assert build_change_map(baseline_scene_id="S1",comparison_scene_id="S2",aoi_id="AOI1",baseline_indices=b,comparison_indices=c)["state"]=="CONTROL_REQUIRED"
def test_deterministic():
 b=grids();x=build_change_map(baseline_scene_id="S1",comparison_scene_id="S2",aoi_id="AOI1",baseline_indices=b,comparison_indices=b);y=build_change_map(baseline_scene_id="S1",comparison_scene_id="S2",aoi_id="AOI1",baseline_indices=b,comparison_indices=b);assert x["fingerprint"]==y["fingerprint"]