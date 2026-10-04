from nema_agora.spatial_evidence_http import handle_request
def test_ready_request(): x=handle_request(request_id="REQ-1",operation="QUERY");assert x["http_status"]==202
def test_ready_response(): x=handle_request(request_id="REQ-1",operation="QUERY",result={"state":"QUERY_READY","count":1,"records":[{"record_id":"R1"}]});assert x["http_status"]==200
def test_invalid_request(): assert handle_request(request_id="bad id",operation="QUERY")["http_status"]==400
def test_invalid_result(): assert handle_request(request_id="REQ-1",operation="QUERY",result={"state":"CONTROL_REQUIRED"})["http_status"]==409
