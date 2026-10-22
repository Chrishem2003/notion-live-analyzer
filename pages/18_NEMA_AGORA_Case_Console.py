"""NEMA-AGORA persisted case console — intentionally read-only."""
from __future__ import annotations
import streamlit as st
from nema_agora.client import NemaApiError, get_case, get_review_packet, get_storage_readiness, list_cases

st.set_page_config(page_title="NEMA-AGORA Case Console", page_icon="🌿", layout="wide")
st.title("🌿 NEMA-AGORA · Case Console")
st.caption("Read-only view of persisted environmental cases. This console does not create, edit, close, or enforce cases; write operations remain disabled until the governed write path is implemented and tested.")

with st.sidebar:
    st.subheader("Connection")
    st.write("API: Render-hosted NEMA case service")
    if st.button("↻ Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("Credentials are read only from the server environment and are never displayed.")

@st.cache_data(ttl=30, show_spinner=False)
def _readiness():
    return get_storage_readiness()

@st.cache_data(ttl=30, show_spinner=False)
def _cases(limit: int):
    return list_cases(limit=limit)

try:
    readiness = _readiness()
    status_value = str(readiness.get("status", "unknown")).lower()
    backend = readiness.get("storage_backend", "supabase_postgres")
    ready = status_value in {"configured", "ready"}
    metrics = st.columns(4)
    metrics[0].metric("Storage status", "Connected" if ready else status_value.replace("_", " ").title())
    metrics[1].metric("Backend", str(backend))
    metrics[2].metric("Production writes", "Enabled" if readiness.get("production_writes_enabled") else "Disabled")
    metrics[3].metric("Durability verified", "Yes" if readiness.get("storage_durability_verified") else "Not yet")
    if not readiness.get("production_writes_enabled"):
        st.info("Read-only safety mode is active. Storage connectivity does not yet certify backup/restore or production write readiness.")
except NemaApiError as exc:
    st.warning("The case API connection is not ready.")
    st.error(str(exc))
    st.markdown("Check that PLATFORM_API_KEY is configured on both Render services with the same value, and that the API service has SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and NEMA_CASE_STORAGE_BACKEND=supabase_postgres configured.")
    st.stop()

st.divider()
left, right = st.columns([1.2, 1])
with left:
    st.subheader("Persisted cases")
    limit = st.selectbox("Maximum cases to load", [25, 50, 100, 250, 500, 1000], index=2)
    try:
        result = _cases(limit)
        items = result.get("items", [])
        st.metric("Cases returned", int(result.get("count", len(items))))
        if not items:
            st.info("No case records are stored yet. Empty storage is expected until a reviewed, audited write workflow is implemented.")
        else:
            options = []
            by_label = {}
            for index, item in enumerate(items):
                record = item.get("record", {})
                case_id = str(record.get("case_id") or record.get("id") or f"record-{index + 1}")
                label = str(record.get("title") or record.get("name") or case_id)
                display = f"{label} · {case_id}"
                options.append(display)
                by_label[display] = case_id
            selected = st.selectbox("Select a case", options)
            if st.button("Load case details", type="primary"):
                st.session_state["nema_selected_case_id"] = by_label[selected]
    except NemaApiError as exc:
        st.error(str(exc))
        st.stop()

with right:
    st.subheader("Case details and audit")
    selected_case_id = st.session_state.get("nema_selected_case_id")
    if not selected_case_id:
        st.caption("Select a case and choose Load case details to inspect its record and audit history.")
    else:
        try:
            detail = get_case(selected_case_id)
            st.caption(f"Case ID: {selected_case_id} · Version: {detail.get('version', 'unknown')}")
            st.json(detail.get("record", {}), expanded=True)
            with st.expander("Audit history", expanded=False):
                st.json(detail.get("audit", []), expanded=True)
            if st.button("Generate review packet (read-only preview)", key="nema_generate_review_packet"):
                try:
                    packet = get_review_packet(selected_case_id)
                    st.session_state["nema_review_packet"] = {
                        "case_id": selected_case_id,
                        "packet": packet,
                    }
                except NemaApiError as exc:
                    st.error(str(exc))
            saved_packet = st.session_state.get("nema_review_packet", {})
            if saved_packet.get("case_id") == selected_case_id:
                st.subheader("Deterministic review packet")
                st.caption("Preview only: this does not create a workflow job or change case data. Human review is still required.")
                st.json(saved_packet.get("packet", {}), expanded=True)
        except NemaApiError as exc:
            st.error(str(exc))

st.divider()
st.caption("Governance note: API authentication is service-to-service, not individual-user authorization. Do not treat this read-only console as a production enforcement or compliance decision system.")
