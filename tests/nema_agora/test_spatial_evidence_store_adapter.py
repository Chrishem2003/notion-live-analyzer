from nema_agora.spatial_evidence_store_adapter import InMemoryEvidenceRepository,execute_query
R=[{"record_id":"R1","aoi_id":"A1","scene_id":"S1"},{"record_id":"R2","aoi_id":"A2","scene_id":"S2"}]
def test_adapter_queries_store(): x=execute_query(repository=InMemoryEvidenceRepository(R),request_id="REQ-1",query={"aoi_id":"A1"});assert x["http_status"]==200;assert x["body"]["count"]==1
def test_empty_store_is_valid(): x=execute_query(repository=InMemoryEvidenceRepository(),request_id="REQ-1");assert x["body"]["count"]==0
def test_invalid_request_fails_closed(): assert execute_query(repository=InMemoryEvidenceRepository(R),request_id="bad id")["http_status"]==400
