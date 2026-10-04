import streamlit as st
from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_audit_lifecycle_reconciliation import reconcile_lifecycle_decisions
st.set_page_config(page_title="NEMA-AGORA API Lifecycle Reconciliation",layout="wide")
st.title("NEMA-AGORA — API Lifecycle Decision Reconciliation")
e={"event_id":"API-93-DEMO","request_id":"REQ-93-DEMO"};r={"state":"RECONCILED","reconciliation_fingerprint":"a"*64};l={"event_id":"API-93-DEMO","reconciliation_fingerprint":"a"*64,"lifecycle_fingerprint":"b"*64}
p={"event_id":"API-93-DEMO","request_id":"REQ-93-DEMO","reconciliation_fingerprint":"a"*64,"lifecycle_fingerprint":"b"*64,"decision":"RETAIN","actor_id":"ACTOR-DEMO","role":"coordinator"}
d=dict(p,decision_id="DEC-93-DEMO",decision_fingerprint=fingerprint(p))
st.json(reconcile_lifecycle_decisions(events=[e],reconciliations=[r],lifecycles=[l],decisions=[d]))
st.info("Synthetic reconciliation. Any integrity gap becomes CONTROL_REQUIRED.")
