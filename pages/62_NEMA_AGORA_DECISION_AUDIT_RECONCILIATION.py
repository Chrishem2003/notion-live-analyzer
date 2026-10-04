"""NEMA-AGORA Phase 54 — Governance Decision Audit Reconciliation."""
import streamlit as st
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import mode_from_secrets
from nema_agora.access import has_permission
from nema_agora.decision_receipt_reconciliation import reconcile_decision_receipts
st.set_page_config(page_title="NEMA-AGORA Decision Audit Reconciliation",layout="wide")
st.title("NEMA-AGORA — Decision Audit Reconciliation")
st.caption("Phase 54-v1 • evidence-integrity reconciliation")
if mode_from_secrets(st.secrets)!="persistent": st.warning("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or principal.role not in {"reviewer","coordinator","admin"} or not has_permission(principal.role,"audit:read"):
 st.error("Authorized access required."); st.stop()
st.info("This is a read-only evidence reconciliation surface. The authoritative lifecycle ledger remains the source of decisions.")
st.write("Provide authoritative decisions, Phase 53 receipts and the exact current snapshot to evaluate reconciliation.")
decisions=st.session_state.get("nema_agora_demo_decisions",[])
receipts=st.session_state.get("nema_agora_demo_receipts",[])
result=reconcile_decision_receipts(decisions=decisions,receipts=receipts,current_snapshot={})
st.metric("State",result["state"]); st.metric("Findings",result["finding_count"]); st.json(result)
