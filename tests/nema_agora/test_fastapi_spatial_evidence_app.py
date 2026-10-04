import tempfile
from pathlib import Path
import pytest
from nema_agora.fastapi_spatial_evidence_app import app_contract,FASTAPI_AVAILABLE
def test_contract_is_read_only(): x=app_contract();assert x["read_only"] is True;assert x["environmental_conclusion"] is None;assert x["regulatory_conclusion"] is None
@pytest.mark.skipif(not FASTAPI_AVAILABLE,reason="FastAPI optional")
def test_health_and_query_routes():
    from fastapi.testclient import TestClient
    from nema_agora.fastapi_spatial_evidence_app import app
    with tempfile.TemporaryDirectory() as d:
        c=TestClient(app)
        h=c.get("/api/v1/spatial-evidence/health");assert h.status_code==200
        q=c.get("/api/v1/spatial-evidence/query",params={"request_id":"REQ-84","database_path":str(Path(d)/"e.db")})
        assert q.status_code==200 and q.json()["count"]==0
