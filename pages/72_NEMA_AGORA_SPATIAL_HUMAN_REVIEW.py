"""Phase 64 — human review and audit binding demo."""
import tempfile
import streamlit as st
from nema_agora.spatial_review_audit_registry import SpatialReviewAuditRegistry
st.set_page_config(page_title="NEMA-AGORA Human Review",layout="wide")
st.title("NEMA-AGORA — Spatial Change Human Review")
st.caption("Phase 64 • explicit human outcome → immutable audit event")
item={"queue_state":"QUEUED","review_item_id":"REVIEW-DEMO-001","candidate_id":"CHANGE-DEMO-001","record_fingerprint":"a"*64}
reviewer=st.text_input("Reviewer ID","REVIEWER-DEMO-01")
role=st.selectbox("Role",["reviewer","coordinator","admin"])
outcome=st.selectbox("Outcome",["CONFIRMED_CHANGE","NOT_CONFIRMED","INSUFFICIENT_EVIDENCE","ESCALATED"])
notes=st.text_area("Review notes","Human review of the analytical evidence.")
if "phase64_db" not in st.session_state:st.session_state.phase64_db=tempfile.NamedTemporaryFile(suffix=".sqlite",delete=False).name
registry=SpatialReviewAuditRegistry(st.session_state.phase64_db)
if st.button("Record review"):
 try:registry.record(item=item,reviewer_id=reviewer,role=role,outcome=outcome,notes=notes);st.success("Immutable review audit event recorded.")
 except ValueError as exc:st.warning(str(exc))
rows=registry.list()
st.metric("Audit events",len(rows))
if rows:st.dataframe(rows,use_container_width=True)
st.json(item)
st.info("Review outcomes are human evidence records. This page does not make official environmental or regulatory determinations.")