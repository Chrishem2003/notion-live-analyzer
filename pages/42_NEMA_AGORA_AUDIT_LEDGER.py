"""NEMA-AGORA Phase 34 — Audit Ledger."""
import json
import re
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.audit_ledger import AuditLedger
from nema_agora.audit_events import AuditEventCapture
from nema_agora.config import database_path_from_secrets, mode_from_secrets

st.set_page_config(page_title="NEMA-AGORA Audit Ledger",page_icon="🔗",layout="wide")
st.title("🔗 NEMA-AGORA — Tamper-Evident Audit Ledger")
st.caption("Phase 34-v1 — append-only records and hash-chain verification")
st.warning("This ledger is tamper-evident, not tamper-proof. A privileged database/file operator can alter records and triggers; protect backups and checkpoints independently.")
if mode_from_secrets(st.secrets)!="persistent":
    st.info("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or not has_permission(principal.role,"intelligence:evidence"):
    st.error("Authenticated evidence access is required."); st.stop()
db=database_path_from_secrets(st.secrets)
if not db: st.error("Persistent database path is required."); st.stop()
ledger=AuditLedger(db)
result=ledger.verify()
a,b=st.columns(2); a.metric("Ledger entries",result["entries"]); b.metric("Integrity","VALID" if result["valid"] else "CONTROL REQUIRED")
st.json(result)
st.subheader("Append an audit entry")
with st.form("append_ledger_entry"):
    entry_id=st.text_input("Unique entry ID")
    event_type=st.selectbox("Event type",["EVIDENCE_REVIEW","PUBLICATION_REVIEW","INTEGRITY_CHECK","GOVERNANCE_NOTE"])
    payload_text=st.text_area("JSON payload",value='{"note":"Human-reviewed audit entry"}')
    submitted=st.form_submit_button("Append entry")
if submitted:
    try:
        payload=json.loads(payload_text)
        entry=ledger.append(entry_id=entry_id,actor_id=principal.subject_key,event_type=event_type,payload=payload)
        st.success("Entry appended."); st.json(entry)
    except (ValueError,json.JSONDecodeError) as exc:
        st.error(str(exc))
st.subheader("Verified ledger entries")
st.json(ledger.list_entries(limit=500))
st.subheader("Checkpoint")
with st.form("checkpoint"):
    checkpoint_id=st.text_input("Checkpoint ID (letters/numbers/._:- only)", max_chars=80)
    submitted_checkpoint=st.form_submit_button("Record current verified head")
if submitted_checkpoint:
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,80}", checkpoint_id.strip()):
        st.error("Use a stable, non-identifying technical checkpoint ID.")
    else:
        try:
            checkpoint=ledger.create_checkpoint(checkpoint_id=checkpoint_id.strip(),actor_id=principal.subject_key)
            st.json(checkpoint)
            try:
                captured=AuditEventCapture(ledger).record(
                    event_id="checkpoint-"+checkpoint_id.strip(),
                    event_type="CHECKPOINT_CREATED",
                    actor_id=principal.subject_key,
                    payload={"checkpoint_id":checkpoint_id.strip(),"checkpoint_sequence":checkpoint["sequence"],
                             "source_module":"checkpoint","status":"COMPLETED",
                             "recorded_by_role":principal.role,"policy_version":"phase36-v1"},
                )
                st.caption("Checkpoint creation event captured in the audit ledger.")
                st.json({"event_capture":captured})
            except Exception as capture_exc:
                st.warning(f"Checkpoint exists, but its follow-up audit event was not captured: {capture_exc}")
        except Exception as exc:
            st.error(str(exc))
st.json(ledger.list_checkpoints())
