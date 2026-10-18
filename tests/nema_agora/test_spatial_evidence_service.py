from nema_agora.spatial_evidence_service import service_request,adapt_query_result
def test_request(): x=service_request(request_id="REQ-1",operation="QUERY",query={"aoi_id":"A1"});assert x["state"]=="SERVICE_REQUEST_READY";assert x["read_only"]
def test_bad_request(): assert service_request(request_id="bad id",operation="QUERY")["state"]=="CONTROL_REQUIRED"
def test_adapter(): q=service_request(request_id="REQ-1",operation="QUERY");r=adapt_query_result(q,{"state":"QUERY_READY","count":1,"records":[{"record_id":"R1"}]});assert r["state"]=="SERVICE_RESPONSE_READY"
def test_bad_result(): q=service_request(request_id="REQ-1",operation="QUERY");assert adapt_query_result(q,{"state":"CONTROL_REQUIRED"})["state"]=="CONTROL_REQUIRED"
