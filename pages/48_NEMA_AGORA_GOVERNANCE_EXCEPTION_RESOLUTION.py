"""NEMA-AGORA Phase 40 — Controlled Governance Exception Resolution."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.governance_exception_resolution import GovernanceExceptionResolver, ALLOWED_CODES, ALLOWED_OUTCOMES
st.set_page_config(page_title="NEMA-AGORA Exception Resolution", page_icon="X", layout="wide")
st.title("NEMA-AGORA — Controlled Exception Resolution")
st.caption("Phase 40-v1 • append-only human governance")
st.warning("This workflow appends an immutable resolution event. It does not edit or delete the historical exception, source decision, or prior audit event.")
if mode_from_secrets(st.secrets) != "persistent": st.info("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or not has_permission(principal.role,"audit:read") or principal.role not in {"reviewer","coordinator","admin"}:
    st.error("Authorized reviewer, coordinator, or admin access is required."); st.stop()
db=database_path_from_secrets(st.secrets); resolver=GovernanceExceptionResolver(db)
st.subheader("Resolve an exception")
code=st.selectbox("Exception code",sorted(ALLOWED_CODES)); kind=st.text_input("Decision kind"); artifact=st.text_input("Artifact ID")
outcome=st.selectbox("Resolution outcome",sorted(ALLOWED_OUTCOMES)); reason=st.text_input("Reason code"); fp=st.text_input("Reconciliation fingerprint")
if st.button("Append resolution",type="primary"):
    try:
        result=resolver.resolve(exception_code=code,decision_kind=kind,artifact_id=artifact,actor_id=principal.subject_key,role=principal.role,outcome=outcome,reason_code=reason,reconciliation_fingerprint=fp)
        st.success("Resolution event appended to the immutable audit ledger."); st.json(result)
    except Exception as exc: st.error(str(exc))
st.subheader("Resolution history"); st.dataframe(resolver.list_resolutions(),use_container_width=True,hide_index=True)
