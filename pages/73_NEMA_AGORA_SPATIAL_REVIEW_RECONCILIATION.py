"""Phase 65 — spatial review reconciliation demo."""
import streamlit as st
from nema_agora.spatial_review_reconciliation import reconcile_spatial_reviews

st.set_page_config(page_title="NEMA-AGORA Spatial Review Reconciliation", layout="wide")
st.title("NEMA-AGORA — Spatial Review Reconciliation")
st.caption("Phase 65 • immutable queue ↕ human-review audit integrity")

queue=[{"review_item_id":"REVIEW-DEMO-001","candidate_id":"CHANGE-DEMO-001","record_fingerprint":"a"*64,"queue_state":"QUEUED"}]
audit=[{"review_event_id":"SPATIAL-REVIEW-DEMO-001","review_item_id":"REVIEW-DEMO-001","candidate_id":"CHANGE-DEMO-001","source_queue_fingerprint":"a"*64}]
result=reconcile_spatial_reviews(queue,audit)

c1,c2,c3,c4=st.columns(4)
c1.metric("State",result["state"])
c2.metric("Queue items",result["summary"]["queue_items"])
c3.metric("Audit events",result["summary"]["audit_events"])
c4.metric("Findings",len(result["findings"]))

st.subheader("Integrity findings")
if result["findings"]:
    st.dataframe(result["findings"],use_container_width=True)
else:
    st.success("RECONCILED — every demo queue item has one matching human-review audit event.")

st.json(result)
st.info("Read-only evidence reconciliation. It does not repair records, establish environmental or regulatory truth, authorize NEMA action, enforce compliance, dispatch emergencies, or make autonomous decisions.")
