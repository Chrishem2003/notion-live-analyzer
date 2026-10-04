"""NEMA-AGORA Phase 36 — governed audit event capture."""
import json
import re
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.audit_events import AuditEventCapture, ALLOWED_EVENT_TYPES
from nema_agora.audit_ledger import AuditLedger
from nema_agora.config import database_path_from_secrets, mode_from_secrets

st.set_page_config(page_title="NEMA-AGORA Audit Event Capture", page_icon="🧾", layout="wide")
st.title("🧾 NEMA-AGORA — Governed Audit Event Capture")
st.caption("Phase 36-v1 — allowlisted, idempotent, metadata-only audit events")
st.warning(
    "Do not enter names, contact details, raw observations, free-text narratives, credentials, "
    "or personal data. This captures selected event metadata; it does not yet automatically hook "
    "every application workflow."
)
if mode_from_secrets(st.secrets) != "persistent":
    st.info("Persistent authenticated mode is required."); st.stop()
principal = principal_from_streamlit_user(st.user, st.secrets)
if not principal or not principal.is_authorised or not has_permission(principal.role, "intelligence:evidence"):
    st.error("Authenticated evidence access is required."); st.stop()
db = database_path_from_secrets(st.secrets)
if not db:
    st.error("Persistent database path is required."); st.stop()

capture = AuditEventCapture(AuditLedger(db))
event_type = st.selectbox("Governed event type", sorted(ALLOWED_EVENT_TYPES))
st.caption("Only approved event types are accepted. Event IDs must be stable, non-identifying technical IDs.")
with st.form("audit_event_capture"):
    event_id = st.text_input("Stable event ID", placeholder="evaluation-run-001", max_chars=128)
    source_module = st.selectbox("Source module", [
        "evaluation", "review", "checkpoint", "publication_control",
        "model_governance", "audit_recovery", "access_control",
    ])
    status = st.selectbox("Status code", [
        "COMPLETED", "FAILED", "VALID", "INVALID", "CONTROL_REQUIRED",
        "APPROVED_FOR_PUBLICATION", "REJECTED", "PENDING_HUMAN_REVIEW",
    ])
    decision = st.selectbox("Decision code (if applicable)", [
        "HUMAN_REVIEW_REQUIRED", "APPROVE", "REJECT", "DEFER",
        "ADMITTED_FOR_CONTROLLED_SHADOW", "CONTROL_REQUIRED",
    ])
    artifact_id = st.text_input("Artifact ID (optional; no personal identifiers)", max_chars=128)
    reason_code = st.selectbox("Reason code", [
        "NONE", "POLICY_GATE", "EVIDENCE_INCOMPLETE", "HUMAN_REVIEW",
        "INTEGRITY_CHECK", "BACKUP_CHECK", "ACCESS_DENIED",
    ])
    submitted = st.form_submit_button("Record governed audit event")
if submitted:
    safe_id = re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", event_id.strip())
    safe_artifact = not artifact_id.strip() or re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", artifact_id.strip())
    if not safe_id or not safe_artifact:
        st.error("Use only letters, numbers, period, underscore, colon, or hyphen for technical IDs.")
    else:
        payload = {
            "source_module": source_module,
            "status": status,
            "decision": decision,
            "reason_code": reason_code,
            "recorded_by_role": principal.role,
            "policy_version": "phase36-v1",
        }
        if artifact_id.strip():
            payload["artifact_id"] = artifact_id.strip()
        try:
            result = capture.record(
                event_id=event_id.strip(), event_type=event_type,
                actor_id=principal.subject_key, payload=payload,
            )
            st.success("Matching event already recorded; no duplicate added." if result.get("duplicate")
                       else "Audit event appended to the hash-chained ledger.")
            st.json(result)
        except (ValueError, PermissionError) as exc:
            st.error(str(exc))

st.divider()
st.subheader("Current ledger verification")
verification = capture.ledger.verify()
st.metric("Ledger status", "VALID" if verification["valid"] else "CONTROL REQUIRED")
st.json(verification)
st.download_button(
    "Download ledger verification JSON",
    json.dumps(verification, sort_keys=True, indent=2),
    file_name="nema_agora_phase36_ledger_verification.json",
    mime="application/json",
)
st.markdown(
    "**Scope:** this page records explicit, human-triggered events. Existing workflows are not "
    "automatically instrumented unless they call the capture service. Audit records support "
    "traceability only; they do not establish environmental truth, environmental impact, "
    "regulatory status, NEMA authorization, or production approval."
)
