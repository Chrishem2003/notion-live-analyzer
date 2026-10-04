import streamlit as st
from nema_agora.api_audit_lifecycle import evaluate_lifecycle
st.set_page_config(page_title="NEMA-AGORA API Audit Lifecycle",layout="wide")
st.title("NEMA-AGORA — API Audit Lifecycle & Retention")
event={"state":"RECORDED","event_id":"API-AUDIT-DEMO","request_id":"REQ-91-DEMO","occurred_at":"2026-10-04T12:00:00+00:00"}
recon={"state":"RECONCILED","reconciliation_fingerprint":"a"*64}
st.json(evaluate_lifecycle(event,recon,now="2026-10-05T12:00:00+00:00",retention_days=365))
st.info("Synthetic lifecycle evaluation. EXPIRED never means deleted.")
