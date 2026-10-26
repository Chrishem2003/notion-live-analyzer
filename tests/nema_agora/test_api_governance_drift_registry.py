import tempfile
from nema_agora.api_governance_drift_registry import GovernanceDriftRegistry
def event():
 return {"drift_id":"API-DRIFT-1","baseline_snapshot_id":"API-SNAPSHOT-A","current_snapshot_id":"API-SNAPSHOT-B","state":"REVIEW_TRIGGERED","severity":"MEDIUM","review_required":True,"changes":[{"field":"finding_count","baseline":0,"current":1}],"drift_fingerprint":"a"*64}
def test_append_list():
 with tempfile.NamedTemporaryFile(suffix=".db") as f:
  r=GovernanceDriftRegistry(f.name);r.append(event());assert len(r.list())==1
def test_duplicate():
 with tempfile.NamedTemporaryFile(suffix=".db") as f:
  r=GovernanceDriftRegistry(f.name);r.append(event())
  try:r.append(event());assert False
  except ValueError as e:assert str(e)=="DRIFT_EVENT_CONFLICT"
def test_immutable():
 with tempfile.NamedTemporaryFile(suffix=".db") as f:
  r=GovernanceDriftRegistry(f.name);r.append(event())
  try:r.db.execute("DELETE FROM governance_drift_events");r.db.commit();assert False
  except Exception:pass
