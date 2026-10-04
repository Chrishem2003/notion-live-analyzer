from nema_agora.spatial_evidence_api import query_spatial_evidence
R=[{"record_id":"R2","aoi_id":"A1","scene_id":"S2","candidate_id":"C2","review_status":"QUEUED","observed_at":"2026-10-02"},{"record_id":"R1","aoi_id":"A1","scene_id":"S1","candidate_id":"C1","review_status":"CONFIRMED","observed_at":"2026-10-01"}]
def test_query_and_order(): x=query_spatial_evidence(R,aoi_id="A1");assert x["state"]=="QUERY_READY";assert [r["record_id"] for r in x["records"]]==["R1","R2"]
def test_filters(): assert query_spatial_evidence(R,candidate_id="C2")["count"]==1
def test_fail_closed(): assert query_spatial_evidence(R,limit=0)["state"]=="CONTROL_REQUIRED"
