import streamlit as st
from nema_agora.api_governance_observatory import build_observatory
st.set_page_config(page_title="NEMA-AGORA API Governance Observatory",layout="wide")
st.title("NEMA-AGORA — API Governance Evidence Observatory")
r=build_observatory(events=[{"event_id":"AUD-98"}],reconciliations=[{"state":"RECONCILED"}],lifecycles=[{"state":"RETAINED"}],decisions=[{"decision_id":"DEC-98"}],cases=[{"case_id":"C-98"}],queue_items=[{"review_id":"R-98"}],reviews=[{"audit_id":"A-98"}],review_reconciliation={"state":"RECONCILED"})
st.metric("Observatory state",r["state"]);st.json(r);st.info("Read-only synthetic observatory; control gaps remain human-governed.")
