import tempfile
from nema_agora.api_governance_drift_review_queue import build_drift_review_item,DriftReviewQueue
def drift(): return {"drift_id":"API-DRIFT-1","drift_fingerprint":"a"*64,"baseline_snapshot_id":"API-SNAPSHOT-A","current_snapshot_id":"API-SNAPSHOT-B","severity":"HIGH","state":"REVIEW_TRIGGERED"}
def test_build_and_queue():
 i=build_drift_review_item(drift())
 with tempfile.NamedTemporaryFile(suffix=".db") as f:q=DriftReviewQueue(f.name);q.enqueue(i);assert q.list()[0]["review_id"]==i["review_id"]
def test_duplicate():
 i=build_drift_review_item(drift())
 with tempfile.NamedTemporaryFile(suffix=".db") as f:
  q=DriftReviewQueue(f.name);q.enqueue(i)
  try:q.enqueue(i);assert False
  except ValueError as e:assert str(e)=="DRIFT_REVIEW_ALREADY_QUEUED"
def test_non_trigger_rejected():
 d=drift();d["state"]="NO_DRIFT"
 try:build_drift_review_item(d);assert False
 except ValueError as e:assert str(e)=="DRIFT_REVIEW_NOT_REQUIRED"
