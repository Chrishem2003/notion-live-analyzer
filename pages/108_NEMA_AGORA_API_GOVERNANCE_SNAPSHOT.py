import streamlit as st
from nema_agora.api_governance_snapshot import build_snapshot,diff_snapshots
st.set_page_config(page_title="NEMA-AGORA API Governance Snapshot",layout="wide")
st.title("NEMA-AGORA — API Governance Snapshot & Baseline")
def make(n):
 o={"state":"READY_FOR_HUMAN_REVIEW","counts":{"audit_events":n,"reconciliations":1},"control_required_sources":0};h={"state":"HEALTHY","coverage_state":"COMPLETE","finding_count":0}
 return build_snapshot(observatory=o,health=h,captured_at=f"2026-10-04T12:0{n}:00+00:00")
a,b=make(1),make(2)
st.json(a);st.subheader("Baseline → Current");st.json(diff_snapshots(a,b))
st.info("Synthetic snapshot/diff demonstration; changes require human review and do not establish environmental or regulatory truth.")
