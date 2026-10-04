import tempfile,streamlit as st
from nema_agora.api_governance_drift_review_queue import build_drift_review_item,DriftReviewQueue
st.set_page_config(page_title="NEMA-AGORA Drift Review Queue",layout="wide")
st.title("NEMA-AGORA — Governance Drift Review Queue")
d={"drift_id":"API-DRIFT-DEMO","drift_fingerprint":"c"*64,"baseline_snapshot_id":"API-SNAPSHOT-A","current_snapshot_id":"API-SNAPSHOT-B","severity":"HIGH","state":"REVIEW_TRIGGERED"}
i=build_drift_review_item(d)
with tempfile.NamedTemporaryFile(suffix=".db") as f:
 q=DriftReviewQueue(f.name);q.enqueue(i);st.metric("Queued reviews",len(q.list()));st.json(q.list())
st.info("Synthetic queue; all review outcomes remain human-governed.")
