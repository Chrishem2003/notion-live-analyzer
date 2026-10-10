from pathlib import Path
import sqlite3,pytest
from nema_agora.spatial_change_review_audit import *
def item():return {"queue_state":"QUEUED","review_item_id":"REVIEW-001","candidate_id":"CHANGE-001","record_fingerprint":"a"*64}
def test_valid_human_review_is_deterministic():
 a=build_review_event(item=item(),reviewer_id="USER-01",role="reviewer",outcome="CONFIRMED_CHANGE",notes="Reviewed evidence.",reviewed_at="2026-10-04T10:00:00+00:00")
 b=build_review_event(item=item(),reviewer_id="USER-01",role="reviewer",outcome="CONFIRMED_CHANGE",notes="Reviewed evidence.",reviewed_at="2026-10-04T10:00:00+00:00")
 assert a["state"]=="VALID" and a["review_event_id"]==b["review_event_id"] and a["human_decision"]
def test_fail_closed_on_bad_role_or_item():
 assert validate_review_input(item(),"USER-01","observer","CONFIRMED_CHANGE")["state"]=="CONTROL_REQUIRED"
 bad=item();bad["queue_state"]="REVIEWED"
 assert validate_review_input(bad,"USER-01","reviewer","NOT_CONFIRMED")["state"]=="CONTROL_REQUIRED"
def test_append_only_and_one_outcome(tmp_path:Path):
 db=str(tmp_path/"audit.sqlite");r=SpatialChangeReviewAuditRegistry(db)
 e=r.record(item=item(),reviewer_id="USER-01",role="reviewer",outcome="NOT_CONFIRMED",reviewed_at="2026-10-04T10:00:00+00:00")
 assert r.list()[0]["review_event_id"]==e["review_event_id"]
 with pytest.raises(ValueError,match="REVIEW_ALREADY_RECORDED"):r.record(item=item(),reviewer_id="USER-02",role="admin",outcome="ESCALATED")
 with sqlite3.connect(db) as c:
  with pytest.raises(sqlite3.IntegrityError):c.execute("UPDATE spatial_change_review_audit SET outcome='ESCALATED'")
  with pytest.raises(sqlite3.IntegrityError):c.execute("DELETE FROM spatial_change_review_audit")
def test_non_regulatory():
 e=build_review_event(item=item(),reviewer_id="USER-01",role="reviewer",outcome="CONFIRMED_CHANGE")
 assert all(e["interpretation"][x] is None for x in ("environmental_conclusion","regulatory_conclusion","violation","enforcement_action"))
