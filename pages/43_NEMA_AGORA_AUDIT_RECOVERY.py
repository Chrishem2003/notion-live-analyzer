"""NEMA-AGORA Phase 35 — Independent Audit Verification & Recovery."""
import json
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.audit_ledger import AuditLedger
from nema_agora.audit_recovery import export_checkpoint, verify_ledger_against_checkpoint
from nema_agora.config import database_path_from_secrets, mode_from_secrets

st.set_page_config(page_title="NEMA-AGORA Audit Recovery", page_icon="🧭", layout="wide")
st.title("🧭 NEMA-AGORA — Independent Audit Verification & Recovery")
st.caption("Phase 35-v1 — verify against a separately preserved checkpoint; read-only recovery checks")
st.warning(
    "This page verifies and compares; it does not repair, restore, or modify the ledger. "
    "A checkpoint saved only inside the same database is not an independent trust anchor. "
    "Export it and preserve it separately. Exports are not digitally signed."
)
if mode_from_secrets(st.secrets) != "persistent":
    st.info("Persistent authenticated mode is required."); st.stop()
principal = principal_from_streamlit_user(st.user, st.secrets)
if not principal or not principal.is_authorised or not has_permission(principal.role, "intelligence:evidence"):
    st.error("Authenticated evidence access is required."); st.stop()
db = database_path_from_secrets(st.secrets)
if not db:
    st.error("Persistent database path is required."); st.stop()
ledger = AuditLedger(db)

st.subheader("Export a checkpoint for independent preservation")
checkpoints = ledger.list_checkpoints()
if checkpoints:
    labels = [f'{c["checkpoint_id"]} — sequence {c["sequence"]}' for c in checkpoints]
    chosen = st.selectbox("Stored checkpoint", labels)
    checkpoint = checkpoints[labels.index(chosen)]
    checkpoint["policy_version"] = "phase34-v1"
    try:
        envelope = export_checkpoint(checkpoint)
        st.download_button(
            "Download checkpoint JSON",
            json.dumps(envelope, sort_keys=True, indent=2),
            file_name=f'nema_agora_checkpoint_{checkpoint["checkpoint_id"]}.json',
            mime="application/json",
        )
        st.caption("Copy the downloaded file to a separately controlled location. The export is not signed.")
    except ValueError as exc:
        st.error(f"Stored checkpoint cannot be exported: {exc}")
else:
    st.info("No stored checkpoints found. Create one on the Audit Ledger page, then export it here.")

st.divider()
st.subheader("Verify the current ledger against an exported checkpoint")
uploaded = st.file_uploader("Upload previously exported checkpoint JSON", type=["json"])
if uploaded is not None:
    try:
        checkpoint_value = json.loads(uploaded.getvalue().decode("utf-8"))
        result = verify_ledger_against_checkpoint(ledger, checkpoint_value)
        st.metric("Verification", "VALID" if result["valid"] else "CONTROL REQUIRED")
        st.json(result)
        st.download_button(
            "Download verification report",
            json.dumps(result, sort_keys=True, indent=2),
            file_name="nema_agora_audit_recovery_report.json",
            mime="application/json",
        )
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        st.error(f"Checkpoint could not be verified: {exc}")

st.subheader("Verification boundaries")
st.markdown(
    "- A matching checkpoint binds the ledger at a recorded sequence and hash.\n"
    "- A ledger shorter than the checkpoint, a hash mismatch, broken chain, or invalid entry fails verification.\n"
    "- Backup comparison is available through the service API; this page does not restore backups.\n"
    "- Preserve exported checkpoints outside the database. A local database owner may alter both the ledger and checkpoints stored in that same database.\n"
    "- Results are integrity evidence only—not environmental truth, environmental impact, regulatory status, NEMA authorization, or production approval."
)
