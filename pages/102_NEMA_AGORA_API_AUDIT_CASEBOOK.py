import streamlit as st
from nema_agora.api_audit_casebook import build_api_audit_case
st.set_page_config(page_title="NEMA-AGORA API Audit Casebook",layout="wide")
st.title("NEMA-AGORA — API Audit Governance Casebook")
e={"event_id":"API-94-DEMO","request_id":"REQ-94-DEMO","audit_fingerprint":"e"*64}
r={"state":"RECONCILED","reconciliation_fingerprint":"a"*64}
l={"event_id":"API-94-DEMO","lifecycle_fingerprint":"b"*64}
d={"event_id":"API-94-DEMO","reconciliation_fingerprint":"a"*64,"lifecycle_fingerprint":"b"*64,"decision_id":"DEC-94-DEMO","decision_fingerprint":"d"*64}
dr={"state":"RECONCILED","reconciliation_fingerprint":"c"*64}
st.json(build_api_audit_case(event=e,reconciliation=r,lifecycle=l,decision=d,decision_reconciliation=dr))
st.info("Synthetic governance casebook. Evidence packaging only; no regulatory conclusion.")
