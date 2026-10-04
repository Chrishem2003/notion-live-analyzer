import tempfile
from pathlib import Path
import pytest
from nema_agora.fastapi_authenticated_routes import FASTAPI_AVAILABLE
@pytest.mark.skipif(not FASTAPI_AVAILABLE,reason="FastAPI optional")
def test_route_authentication_and_query():
 from fastapi.testclient import TestClient
 from nema_agora.fastapi_authenticated_routes import app
 with tempfile.TemporaryDirectory() as d:
  c=TestClient(app)
  base={"request_id":"REQ-87","database_path":str(Path(d)/"e.db"),"actor_id":"ACTOR-1","role":"coordinator"}
  assert c.get("/api/v1/spatial-evidence/query",params=base).status_code==401
  assert c.get("/api/v1/spatial-evidence/query",params=base,headers={"Authorization":"Bearer demo"}).status_code==200
@pytest.mark.skipif(not FASTAPI_AVAILABLE,reason="FastAPI optional")
def test_route_rejects_reviewer_query():
 from fastapi.testclient import TestClient
 from nema_agora.fastapi_authenticated_routes import app
 with tempfile.TemporaryDirectory() as d:
  c=TestClient(app);p={"request_id":"REQ-87","database_path":str(Path(d)/"e.db"),"actor_id":"ACTOR-1","role":"reviewer"}
  assert c.get("/api/v1/spatial-evidence/query",params=p,headers={"Authorization":"Bearer demo"}).status_code==403
