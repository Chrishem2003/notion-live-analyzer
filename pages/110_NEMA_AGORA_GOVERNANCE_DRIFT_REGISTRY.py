import tempfile
import streamlit as st
from nema_agora.api_governance_drift_registry import GovernanceDriftRegistry
st.set_page_config(page_title="NEMA-AGORA Drift Registry",layout="wide")
st.title("NEMA-AGORA — Governance Drift Registry")
e={"drift_id":"API-DRIFT-DEMO","baseline_snapshot_id":"API-SNAPSHOT-A","current_snapshot_id":"API-SNAPSHOT-B","state":"REVIEW_TRIGGERED","severity":"MEDIUM","review_required":True,"changes":[{"field":"finding_count","baseline":0,"current":1}],"drift_fingerprint":"b"*64}
with tempfile.NamedTemporaryFile(suffix=".db") as f:
 r=GovernanceDriftRegistry(f.name);r.append(e);st.metric("Stored drift events",len(r.list()));st.json(r.list())
st.info("Synthetic append-only registry demonstration; drift requires human review.")
