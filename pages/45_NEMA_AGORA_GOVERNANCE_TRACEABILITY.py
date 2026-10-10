"""NEMA-AGORA Phase 37 — End-to-End Governance Traceability."""
import json
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import mode_from_secrets
from nema_agora.governance_traceability import serialise_trace, validate_governance_trace

st.set_page_config(page_title="NEMA-AGORA Governance Traceability", page_icon="🧭", layout="wide")
st.title("🧭 NEMA-AGORA — End-to-End Governance Traceability")
st.caption("Phase 37-v1 — explicit artifact lineage and audit-event coverage")
st.warning(
    "Traceability is an engineering/research integrity control. It is not environmental truth, "
    "NEMA authorization, regulatory approval, production approval, enforcement authority, or emergency-response authority."
)
if mode_from_secrets(st.secrets) != "persistent":
    st.info("Persistent authenticated mode is required."); st.stop()
principal = principal_from_streamlit_user(st.user, st.secrets)
if not principal or not principal.is_authorised or not has_permission(principal.role, "intelligence:evidence"):
    st.error("Authenticated evidence access is required."); st.stop()

st.markdown(
    "Upload a **machine-readable trace bundle** containing explicit identifiers. "
    "The page is read-only and does not modify source evidence or the audit ledger."
)
st.code(
    '{"origin_event": {...}, "provenance_records": [...], "graph": {...}, '
    '"report": {...}, "publication_decision": {...}, "audit_entries": [...], '
    '"ledger_verification": {...}}',
    language="json",
)
uploaded = st.file_uploader("Trace bundle JSON", type=["json"])
if uploaded:
    try:
        bundle = json.load(uploaded)
        required = {
            "origin_event", "provenance_records", "graph", "report",
            "publication_decision", "audit_entries", "ledger_verification",
        }
        missing = sorted(required - set(bundle))
        if missing:
            st.error("CONTROL_REQUIRED — missing bundle sections: " + ", ".join(missing))
            st.stop()
        result = validate_governance_trace(
            origin_event=bundle["origin_event"],
            provenance_records=bundle["provenance_records"],
            graph=bundle["graph"],
            report=bundle["report"],
            publication_decision=bundle["publication_decision"],
            audit_entries=bundle["audit_entries"],
            ledger_verification=bundle["ledger_verification"],
        )
        if result["valid"]:
            st.success("TRACEABLE — all required explicit references passed.")
        else:
            st.error("CONTROL_REQUIRED — traceability validation failed closed.")
        st.json(result)
        if result["warnings"]:
            st.warning("Warnings: " + "; ".join(result["warnings"]))
        st.download_button(
            "Download traceability result",
            serialise_trace(result),
            "nema_agora_phase37_traceability_result.json",
            "application/json",
        )
    except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
        st.error(f"Invalid trace bundle: {exc}")

st.caption(
    "Phase 36 only instruments selected decision boundaries. Missing origin-event audit coverage is "
    "reported as a warning unless a required publication audit event is absent."
)
