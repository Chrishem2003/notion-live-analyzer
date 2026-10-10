"""NEMA-AGORA Phase 39 — Governance Reconciliation."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.governance_reconciliation import reconcile_database

st.set_page_config(page_title="NEMA-AGORA Governance Reconciliation", page_icon="🔎", layout="wide")
st.title("🔎 NEMA-AGORA — Governance Reconciliation")
st.caption("Phase 39-v1 • exception detection • human-controlled resolution")
st.warning("Read-only reconciliation. It detects gaps or inconsistencies between authoritative application decisions and governed audit events. It never repairs, deletes, or rewrites history.")
if mode_from_secrets(st.secrets) != "persistent":
    st.info("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user, st.secrets)
if not principal or not principal.is_authorised or not has_permission(principal.role,"audit:read"):
    st.error("Authenticated audit access is required."); st.stop()
result=reconcile_database(database_path_from_secrets(st.secrets))
c1,c2,c3=st.columns(3)
c1.metric("Status",result["status"])
c2.metric("Matched",result["matched"])
c3.metric("Exceptions",len(result["exceptions"]))
if result["status"]=="TRACEABLE":
    st.success("Authoritative decision records and governed audit coverage are synchronized for the inspected stores.")
else:
    st.error("CONTROL REQUIRED — reconciliation found discrepancies that require human investigation.")
if result["exceptions"]:
    st.subheader("Reconciliation exceptions")
    st.dataframe(result["exceptions"],use_container_width=True,hide_index=True)
else:
    st.info("No reconciliation exceptions detected.")
with st.expander("Reconciliation metadata"):
    st.json({k:result[k] for k in ("reconciliation_id","reconciliation_fingerprint","policy_version","source_count","audit_count","notice")})
st.info("Resolution is intentionally outside this phase. An exception may be investigated and resolved through an explicit human-governed workflow; no automatic repair is performed.")
