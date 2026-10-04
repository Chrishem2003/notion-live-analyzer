import os,tempfile
from nema_agora.api_governance_review_queue import build_review_item,ApiGovernanceReviewQueue
def case():return {"state":"CASEBOOK_READY","case_id":"API-CASE-1","case_fingerprint":"a"*64,"request_id":"REQ-95"}
def test_queue():
 item=build_review_item(case(),90);assert item["state"]=="QUEUED"
 with tempfile.TemporaryDirectory() as d:
  q=ApiGovernanceReviewQueue(os.path.join(d,"q.db"));q.enqueue(item);assert q.list()[0]["review_id"]==item["review_id"]
def test_requires_casebook():assert build_review_item({"state":"CONTROL_REQUIRED"})["state"]=="CONTROL_REQUIRED"
def test_duplicate():
 item=build_review_item(case())
 with tempfile.TemporaryDirectory() as d:
  q=ApiGovernanceReviewQueue(os.path.join(d,"q.db"));q.enqueue(item)
  try:q.enqueue(item);assert False
  except ValueError as x:assert str(x)=="API_REVIEW_ALREADY_QUEUED"
