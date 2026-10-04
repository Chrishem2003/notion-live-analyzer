"""Phase 66 — spatial review evidence casebook demo."""
import streamlit as st
from nema_agora.spatial_review_reconciliation import reconcile_spatial_reviews
from nema_agora.spatial_review_casebook import build_spatial_review_casebook,fingerprint
st.set_page_config(page_title="NEMA-AGORA Spatial Review Casebook",layout="wide")
st.title("NEMA-AGORA — Spatial Review Evidence Casebook")
st.caption("Phase 66 • exact queue + human review + reconciliation provenance")
queue=[{"review_item_id":"REVIEW-DEMO-001","candidate_id":"CHANGE-DEMO-001","record_fingerprint":"a"*64,"source_candidate_fingerprint":"b"*64,"priority_score":.82,"priority_tier":"HIGH","reason_codes":["COMBINED_CHANGE_SIGNAL"],"spatial":{"aoi_id":"AOI-DEMO","grid_id":"GRID-10M"},"created_at":"2026-10-04T10:00:00+00:00","queue_state":"QUEUED"}]
audit={"review_event_id":"SPATIAL-REVIEW-DEMO-001","review_item_id":"REVIEW-DEMO-001","candidate_id":"CHANGE-DEMO-001","source_queue_fingerprint":"a"*64,"reviewer_id":"REVIEWER-DEMO","reviewer_role":"reviewer","outcome":"CONFIRMED_CHANGE","reviewed_at":"2026-10-04T11:00:00+00:00","audit_event_type":"SPATIAL_CHANGE_HUMAN_REVIEW","human_decision":True}
audit["event_fingerprint"]=fingerprint(audit)
recon=reconcile_spatial_reviews(queue,[{k:audit[k] for k in ("review_event_id","review_item_id","candidate_id","source_queue_fingerprint")}])
book=build_spatial_review_casebook(queue,[audit],recon)
c1,c2,c3=st.columns(3);c1.metric("State",book["state"]);c2.metric("Cases",book["case_count"]);c3.metric("Findings",len(book["findings"]))
if book["findings"]:st.dataframe(book["findings"],use_container_width=True)
else:st.success("CASEBOOK_READY — exact queue, human review and reconciliation provenance are bound.")
st.json(book)
st.info("Evidence packaging only. Human outcomes remain human evidence and are not regulatory or environmental truth.")
