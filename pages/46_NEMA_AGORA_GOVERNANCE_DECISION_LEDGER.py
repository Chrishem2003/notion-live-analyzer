"""NEMA-AGORA Phase 38 — Governance Decision Ledger."""
import json
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.audit_ledger import AuditLedger
from nema_agora.config import database_path_from_secrets, mode_from_secrets

st.set_page_config(page_title="NEMA-AGORA Governance Decision Ledger", page_icon="📜", layout="wide")
st.title("📜 NEMA-AGORA — Governance Decision Ledger")
st.caption("Phase 38-v1 • decision-boundary integration • metadata-only audit trail")
st.warning(
    "This ledger records already-made governance decisions. It does not make decisions, "
    "change model status, establish environmental truth, authorize enforcement, or represent NEMA approval."
)
if mode_from_secrets(st.secrets) != "persistent":
    st.info("Persistent authenticated mode is required."); st.stop()
principal = principal_from_streamlit_user(st.user, st.secrets)
if not principal or not principal.is_authorised or not has_permission(principal.role, "audit:read"):
    st.error("Authenticated audit access is required."); st.stop()
db = database_path_from_secrets(st.secrets)
ledger = AuditLedger(db)

verification = ledger.verify()
c1,c2,c3=st.columns(3)
c1.metric("Integrity", "VALID" if verification["valid"] else "CONTROL REQUIRED")
c2.metric("Entries", verification["entries"])
c3.metric("Verified", verification["verified_entries"])
if not verification["valid"]:
    st.error("Ledger integrity verification failed closed.")
    st.json(verification)

entries = ledger.list_entries(limit=500)
st.subheader("Governed decision events")
governed = [e for e in entries if e.get("event_type") == "GOVERNED_AUDIT_EVENT"]
if governed:
    st.dataframe(
        [
            {
                "sequence": e["sequence"],
                "entry_id": e["entry_id"],
                "event_id": e["payload"].get("event_id"),
                "event_type": e["payload"].get("event_type"),
                "artifact_id": (e["payload"].get("metadata") or {}).get("artifact_id"),
                "decision": (e["payload"].get("metadata") or {}).get("decision"),
                "status": (e["payload"].get("metadata") or {}).get("status"),
                "actor": e["actor_id"],
                "recorded_by_role": (e["payload"].get("metadata") or {}).get("recorded_by_role"),
            }
            for e in governed
        ],
        use_container_width=True, hide_index=True,
    )
else:
    st.info("No governed decision events have been captured yet.")

with st.expander("Machine-readable ledger entries"):
    st.json(governed[-25:])

st.info(
    "Phase 38 currently connects the application service's evaluation, human-review and lifecycle "
    "decision boundaries. Checkpoint creation and publication-gate decisions remain connected from "
    "Phase 36. Backup verification has a dedicated adapter available for the recovery workflow."
)
