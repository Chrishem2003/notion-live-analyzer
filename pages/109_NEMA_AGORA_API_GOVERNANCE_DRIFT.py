import streamlit as st
from nema_agora.api_governance_snapshot import build_snapshot
from nema_agora.api_governance_drift import detect_drift
st.set_page_config(page_title="NEMA-AGORA Governance Drift",layout="wide")
st.title("NEMA-AGORA — Governance Drift Detection")
def snap(n):
 o={"state":"READY_FOR_HUMAN_REVIEW","counts":{"audit_events":n},"control_required_sources":0};h={"state":"HEALTHY","coverage_state":"COMPLETE","finding_count":0}
 return build_snapshot(observatory=o,health=h,captured_at=f"2026-10-04T12:0{n}:00+00:00")
r=detect_drift(baseline=snap(1),current=snap(2));st.metric("State",r["state"]);st.metric("Severity",r["severity"]);st.json(r)
st.info("Synthetic drift trigger. Human review is required; no autonomous regulatory action is performed.")
