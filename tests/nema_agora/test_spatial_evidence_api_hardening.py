import tempfile
from pathlib import Path
from nema_agora.spatial_evidence_api_hardening import query_persistent_evidence
def test_invalid_limit(): 
 with tempfile.TemporaryDirectory() as d: assert query_persistent_evidence(database_path=str(Path(d)/"x.db"),request_id="REQ-1",limit=0)["http_status"]==400
def test_unsupported_filter():
 with tempfile.TemporaryDirectory() as d: assert query_persistent_evidence(database_path=str(Path(d)/"x.db"),request_id="REQ-1",query={"bad":"x"})["http_status"]==400
def test_missing_db_is_created_and_empty_query_is_ready():
 with tempfile.TemporaryDirectory() as d:
  x=query_persistent_evidence(database_path=str(Path(d)/"x.db"),request_id="REQ-1"); assert x["http_status"]==200 and x["body"]["count"]==0
def test_temporal_filter_is_supported():
 with tempfile.TemporaryDirectory() as d:
  x=query_persistent_evidence(database_path=str(Path(d)/"x.db"),request_id="REQ-1",query={"observed_from":"2026-10-01T00:00:00Z"}); assert x["http_status"]==200
