from nema_agora.spatial_evidence_integration import retrieve_spatial_evidence
class Repo:
    def __init__(self,records=(),error=None): self.records=records; self.error=error
    def list(self,**kwargs):
        if self.error: raise self.error
        return [r for r in self.records if kwargs.get("aoi_id") is None or r.get("aoi_id")==kwargs["aoi_id"]]
def test_api_service_repository_round_trip():
    x=retrieve_spatial_evidence(repository=Repo([{"record_id":"R1","aoi_id":"A1"}]),request_id="REQ-1",query={"aoi_id":"A1"})
    assert x["http_status"]==200 and x["body"]["count"]==1
def test_filter_returns_empty_without_failure():
    x=retrieve_spatial_evidence(repository=Repo([{"record_id":"R1","aoi_id":"A1"}]),request_id="REQ-1",query={"aoi_id":"A2"})
    assert x["http_status"]==200 and x["body"]["count"]==0
def test_repository_failure_is_fail_closed():
    x=retrieve_spatial_evidence(repository=Repo(error=RuntimeError("db down")),request_id="REQ-1")
    assert x["http_status"]==409 and x["body"]["state"]=="CONTROL_REQUIRED"
def test_invalid_request_is_rejected():
    x=retrieve_spatial_evidence(repository=Repo(),request_id="bad id")
    assert x["http_status"]==400
