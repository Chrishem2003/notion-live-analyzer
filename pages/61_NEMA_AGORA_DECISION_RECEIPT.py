"""NEMA-AGORA Phase 53 — Decision Receipt & Audit Binding."""
import streamlit as st
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import mode_from_secrets
from nema_agora.access import has_permission
st.set_page_config(page_title="NEMA-AGORA Decision Receipt",layout="wide")
st.title("NEMA-AGORA — Decision Receipt & Audit Binding")
st.caption("Phase 53-v1 • append-only evidentiary receipt")
if mode_from_secrets(st.secrets)!="persistent": st.warning("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or principal.role not in {"reviewer","coordinator","admin"} or not has_permission(principal.role,"audit:read"):
 st.error("Authorized access required."); st.stop()
st.info("This surface is evidentiary only. It does not execute or change a governance decision.")
st.metric("Mode","Read-only receipt view")
st.write("Human lifecycle decisions remain authoritative in the existing Phase 44 ledger. Receipts bind evidence after execution.")
