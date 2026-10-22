import os,tempfile
from nema_agora.api_governance_human_review import review_queue_item,ApiHumanReviewAuditRegistry
def item():return {"state":"QUEUED","review_id":"API-REVIEW-1","case_id":"API-CASE-1","case_fingerprint":"a"*64,"request_id":"REQ-96"}
def test_review_and_append():
 a=review_queue_item(item(),actor_id="ACTOR-1",role="coordinator",outcome="CONFIRMED_TRACE",reviewed_at="2026-10-04T12:00:00+00:00")
 assert a["state"]=="REVIEW_RECORDED"
 with tempfile.TemporaryDirectory() as d:
  r=ApiHumanReviewAuditRegistry(os.path.join(d,"a.db"));r.append(a);assert len(r.list())==1
def test_unauthorized():assert review_queue_item(item(),actor_id="x",role="reviewer",outcome="CONFIRMED_TRACE",reviewed_at="2026-10-04T12:00:00+00:00")["state"]=="CONTROL_REQUIRED"
def test_duplicate():
 a=review_queue_item(item(),actor_id="ACTOR-1",role="coordinator",outcome="ESCALATED",reviewed_at="2026-10-04T12:00:00+00:00")
 with tempfile.TemporaryDirectory() as d:
  r=ApiHumanReviewAuditRegistry(os.path.join(d,"a.db"));r.append(a)
  try:r.append(a);assert False
  except ValueError as x:assert str(x)=="REVIEW_ALREADY_RECORDED"
