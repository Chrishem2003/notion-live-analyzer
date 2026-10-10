"""NEMA-AGORA Phase 52 — Governance Decision Execution Boundary."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import mode_from_secrets
from nema_agora.governance_decision_execution import validate_execution_request

st.set_page_config(page_title="NEMA-AGORA Decision Boundary",page_icon="⚖",layout="wide")
st.title("NEMA-AGORA — Governance Decision Execution Boundary")
st.caption("Phase 52-v1 • prerequisite validation • no automatic execution")
st.info("This page validates prerequisites only. Actual governance decisions remain in the existing human-governed lifecycle workflow.")
if mode_from_secrets(st.secrets)!="persistent": st.warning("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or principal.role not in {"coordinator","admin"} or not has_permission(principal.role,"audit:read"):
    st.error("Authorized coordinator or admin access is required."); st.stop()
st.warning("No execution control is exposed here. The result below is never an approval and never writes a lifecycle decision.")
st.write("Use a prepared decision package from Phase 51.")
decision=st.selectbox("Intended human decision",["APPROVE","REJECT","REVOKE","SUPERSEDE"])
st.caption("Selection records nothing; it only validates a hypothetical request.")
example_package={"case_id":"MANUAL_REVIEW_REQUIRED","decision_status":"NOT_DECIDED","current_snapshot":{}}
result=validate_execution_request(prepared_package=example_package,decision=decision,actor_id=str(principal.actor_id),role=principal.role,current_snapshot={})
st.subheader("Boundary result")
st.json(result)
st.caption(result["notice"])
