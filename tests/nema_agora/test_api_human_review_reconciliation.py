from nema_agora.api_human_review_reconciliation import reconcile_reviews,review_audit_fingerprint
def data():
 q={"review_id":"R-1","case_id":"C-1","case_fingerprint":"a"*64,"request_id":"REQ-1"};c={"case_id":"C-1","case_fingerprint":"a"*64}
 a={"review_id":"R-1","case_id":"C-1","case_fingerprint":"a"*64,"request_id":"REQ-1","reviewer_actor_id":"A-1","reviewer_role":"coordinator","outcome":"CONFIRMED_TRACE","reviewed_at":"2026-10-04T12:00:00+00:00"};a["audit_fingerprint"]=review_audit_fingerprint(a)
 return q,c,a
def test_reconciled():
 q,c,a=data();assert reconcile_reviews(queue_items=[q],cases=[c],audits=[a])["state"]=="RECONCILED"
def test_orphan():
 q,c,a=data();a["review_id"]="R-X";assert reconcile_reviews(queue_items=[q],cases=[c],audits=[a])["state"]=="CONTROL_REQUIRED"
def test_tamper():
 q,c,a=data();a["outcome"]="ESCALATED";assert reconcile_reviews(queue_items=[q],cases=[c],audits=[a])["state"]=="CONTROL_REQUIRED"
