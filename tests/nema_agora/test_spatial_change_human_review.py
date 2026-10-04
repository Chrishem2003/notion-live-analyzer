from pathlib import Path
import sqlite3,pytest
from nema_agora.spatial_change_human_review import create_review_event,validate_review
from nema_agora.spatial_review_audit_registry import SpatialReviewAuditRegistry
def item():return {"queue_state":"QUEUED","review_item_id":"REVIEW-001","candidate_id":"CHANGE-001","record_fingerprint":"a"*64}
def test_valid_review_is_deterministic():
 a=create_review_event(item=item(),reviewer_id="REVIEWER-01",role="reviewer",outcome="CONFIRMED_CHANGE",notes="Reviewed.",reviewed_at="2026-10-04T10:00:00+00:00")
 b=create_review_event(item=item(),reviewer_id="REVIEWER-01",role="reviewer",outcome="CONFIRMED_CHANGE",notes="Reviewed.",reviewed_at="2026-10-04T10:00:00+00:00")
 assert a["state"]=="VALID" and a["review_event_id"]==b["review_event_id"]
def test_bad_role_and_queue_fail_closed():
 assert validate_review(item(),"observer","reviewer","CONFIRMED_CHANGE")["state"]=="CONTROL_REQUIRED"
 bad=item();bad["queue_state"]="REVIEWED"
 assert validate_review(bad,"REVIEWER-01","reviewer","NOT_CONFIRMED")["state"]=="CONTROL_REQUIRED"
def test_append_only_audit(tmp_path:Path):
 db=str(tmp_path/"audit.sqlite");r=SpatialReviewAuditRegistry(db)
 e=r.record(item=item(),reviewer_id="REVIEWER-01",role="reviewer",outcome="NOT_CONFIRMED")
 assert r.list()[0]["review_event_id"]==e["review_event_id"]
 with pytest.raises(ValueError,match="REVIEW_ALREADY_RECORDED"):r.record(item=item(),reviewer_id="REVIEWER-02",role="admin",outcome="ESCALATED")
 with sqlite3.connect(db) as c:
  with pytest.raises(sqlite3.IntegrityError):c.execute("UPDATE spatial_review_audit SET outcome='ESCALATED'")
  with pytest.raises(sqlite3.IntegrityError):c.execute("DELETE FROM spatial_review_audit")
def test_review_event_is_not_regulatory():
 e=create_review_event(item=item(),reviewer_id="REVIEWER-01",role="reviewer",outcome="CONFIRMED_CHANGE")
 assert e["human_decision"] is True
