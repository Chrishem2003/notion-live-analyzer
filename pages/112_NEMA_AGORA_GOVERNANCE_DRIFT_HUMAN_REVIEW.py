import streamlit as st
from nema_agora.api_governance_drift_human_review import review_drift
st.set_page_config(page_title="NEMA-AGORA Drift Human Review",layout="wide")
st.title("NEMA-AGORA — Governance Drift Human Review")
i={"review_id":"R-104-DEMO","drift_id":"D-104-DEMO","drift_fingerprint":"d"*64,"baseline_snapshot_id":"S-A","current_snapshot_id":"S-B","state":"QUEUED"}
r=review_drift(i,actor_id="ACTOR-DEMO",role="coordinator",outcome="INVESTIGATE",reviewed_at="2026-10-04T12:00:00+00:00")
st.metric("Review state",r["state"]);st.json(r)
st.info("Synthetic human-review audit. No autonomous action is executed.")
