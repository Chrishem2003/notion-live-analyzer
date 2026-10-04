from nema_agora.api_governance_drift_human_review import review_drift
def item(): return {"review_id":"R-1","drift_id":"D-1","drift_fingerprint":"a"*64,"baseline_snapshot_id":"S-A","current_snapshot_id":"S-B","state":"QUEUED"}
def test_review(): assert review_drift(item(),actor_id="A-1",role="coordinator",outcome="INVESTIGATE",reviewed_at="2026-10-04T12:00:00+00:00")["state"]=="REVIEW_RECORDED"
def test_unauthorized():
 try:review_drift(item(),actor_id="A",role="reviewer",outcome="INVESTIGATE",reviewed_at="x");assert False
 except ValueError as e:assert str(e)=="REVIEWER_NOT_AUTHORIZED"
def test_not_queued():
 d=item();d["state"]="CLOSED"
 try:review_drift(d,actor_id="A",role="admin",outcome="ACKNOWLEDGED",reviewed_at="x");assert False
 except ValueError as e:assert str(e)=="REVIEW_ITEM_NOT_QUEUED"
