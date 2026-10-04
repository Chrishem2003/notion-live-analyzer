from nema_agora.spatial_review_reconciliation import reconcile_spatial_reviews
from nema_agora.spatial_review_casebook import build_spatial_review_casebook,fingerprint
def q():return {"review_item_id":"REVIEW-001","candidate_id":"CHANGE-001","record_fingerprint":"a"*64,"source_candidate_fingerprint":"b"*64,"priority_score":.82,"priority_tier":"HIGH","reason_codes":["COMBINED_CHANGE_SIGNAL"],"spatial":{"aoi_id":"AOI-01","grid_id":"GRID-10M"},"created_at":"2026-10-04T10:00:00+00:00","queue_state":"QUEUED"}
def a(fp="a"*64):
 e={"review_event_id":"SPATIAL-REVIEW-001","review_item_id":"REVIEW-001","candidate_id":"CHANGE-001","source_queue_fingerprint":fp,"reviewer_id":"REVIEWER-01","reviewer_role":"reviewer","outcome":"CONFIRMED_CHANGE","reviewed_at":"2026-10-04T11:00:00+00:00","audit_event_type":"SPATIAL_CHANGE_HUMAN_REVIEW","human_decision":True};e["event_fingerprint"]=fingerprint(e);return e
def r():
 x=q();y=a();return reconcile_spatial_reviews([x],[{"review_event_id":y["review_event_id"],"review_item_id":y["review_item_id"],"candidate_id":y["candidate_id"],"source_queue_fingerprint":y["source_queue_fingerprint"]}])
def test_ready_and_bound():
 x=q();y=a();b=build_spatial_review_casebook([x],[y],r());assert b["state"]=="CASEBOOK_READY";c=b["cases"][0];assert c["provenance"]["queue_fingerprint"]=="a"*64 and c["provenance"]["audit_event_fingerprint"]==y["event_fingerprint"] and c["provenance"]["reconciliation_fingerprint"]==r()["reconciliation_fingerprint"]
def test_tamper_fails_closed():
 x=q();y=a();y["outcome"]="ESCALATED";b=build_spatial_review_casebook([x],[y],r());assert b["state"]=="CONTROL_REQUIRED";assert any(z["code"]=="AUDIT_EVENT_FINGERPRINT_MISMATCH" for z in b["findings"])
def test_binding_mismatch_fails_closed():
 x=q();y=a("c"*64);b=build_spatial_review_casebook([x],[y],r());assert b["state"]=="CONTROL_REQUIRED"
def test_duplicate_cannot_form_case():
 x=q();y=a();r0=r();b=build_spatial_review_casebook([x],[y,dict(y,review_event_id="SPATIAL-REVIEW-002")],r0);assert b["state"]=="CONTROL_REQUIRED";assert any(z["code"]=="CASE_NOT_UNIQUELY_REVIEWED" for z in b["findings"])
def test_deterministic():
 x=q();y=a();assert build_spatial_review_casebook([x],[y],r())["casebook_fingerprint"]==build_spatial_review_casebook([x],[y],r())["casebook_fingerprint"]
def test_non_regulatory():
 b=build_spatial_review_casebook([q()],[a()],r())
 for k in ("environmental_conclusion","regulatory_conclusion","violation","enforcement_action"):assert b["interpretation"][k] is None
