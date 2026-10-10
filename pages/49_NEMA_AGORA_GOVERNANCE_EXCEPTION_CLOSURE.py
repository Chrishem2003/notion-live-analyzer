"""NEMA-AGORA Phase 41 — Governance Exception Closure."""
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.governance_exception_closure import reconcile_and_evaluate

st.set_page_config(page_title="NEMA-AGORA Exception Closure", page_icon="✓", layout="wide")
st.title("NEMA-AGORA — Governance Exception Closure")
st.caption("Phase 41-v1 • explicit closure rules and evidence requirements")
st.info(
    "Read-only derived governance state. This page never edits source decisions, "
    "rewrites reconciliation results, or changes historical audit events."
)

if mode_from_secrets(st.secrets) != "persistent":
    st.warning("Persistent authenticated mode is required.")
    st.stop()

principal = principal_from_streamlit_user(st.user, st.secrets)
if (
    not principal
    or not principal.is_authorised
    or principal.role not in {"reviewer", "coordinator", "admin"}
    or not has_permission(principal.role, "audit:read")
):
    st.error("Authorized reviewer, coordinator, or admin access is required.")
    st.stop()

try:
    database_path = database_path_from_secrets(st.secrets)
    result = reconcile_and_evaluate(database_path)
except Exception as exc:
    st.error(f"Closure evaluation failed closed: {exc}")
    st.stop()

status = result["overall_status"]
if status == "CLOSED":
    st.success("All currently detected exceptions satisfy the explicit closure rules.")
elif status == "CONTROL_REQUIRED":
    st.error("One or more exceptions remain unresolved or require human control.")
else:
    st.warning(f"Closure state: {status}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Exceptions", result["exception_count"])
m2.metric("Closed", result["closed_count"])
m3.metric("Unresolved", result["unresolved_count"])
m4.metric("Policy", result["policy_version"])

st.subheader("Closure results")
if result["results"]:
    st.dataframe(result["results"], use_container_width=True, hide_index=True)
else:
    st.success("No reconciliation exceptions are currently open.")

st.subheader("Required evidence")
st.markdown(
    "A closeable Phase 40 outcome must match the current reconciliation fingerprint "
    "and be supported by a stable non-identifying evidence ID plus a valid SHA-256 "
    "evidence hash. ACKNOWLEDGED does not close an exception; ESCALATED remains under "
    "human control."
)

st.subheader("Deterministic closure identity")
st.code(
    f"closure_id={result['closure_id']}\n"
    f"reconciliation_fingerprint={result['reconciliation_fingerprint']}\n"
    f"closure_fingerprint={result['closure_fingerprint']}"
)
st.caption(result["notice"])
