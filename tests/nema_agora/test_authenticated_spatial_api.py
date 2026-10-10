import tempfile
from pathlib import Path
from nema_agora.authenticated_spatial_api import authenticated_query
def test_authorized_query_reaches_store():
    with tempfile.TemporaryDirectory() as d:
        x=authenticated_query(database_path=str(Path(d)/"e.db"),actor_id="ACTOR-1",role="coordinator",request_id="REQ-1")
        assert x["http_status"]==200 and x["body"]["count"]==0 and x["body"]["authorization_context"]["actor_id"]=="ACTOR-1"
def test_missing_authentication_stops_before_store():
    with tempfile.TemporaryDirectory() as d:
        x=authenticated_query(database_path=str(Path(d)/"e.db"),actor_id="ACTOR-1",role="coordinator",request_id="REQ-1",token_present=False)
        assert x["http_status"]==401
def test_reader_cannot_query():
    with tempfile.TemporaryDirectory() as d:
        x=authenticated_query(database_path=str(Path(d)/"e.db"),actor_id="ACTOR-1",role="reviewer",request_id="REQ-1")
        assert x["http_status"]==403
def test_invalid_request_fails_closed():
    with tempfile.TemporaryDirectory() as d:
        x=authenticated_query(database_path=str(Path(d)/"e.db"),actor_id="ACTOR-1",role="coordinator",request_id="bad id")
        assert x["http_status"]==403
