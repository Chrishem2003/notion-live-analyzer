import streamlit as st
from nema_agora.api_governance_health import evaluate_health
st.set_page_config(page_title="NEMA-AGORA API Governance Health",layout="wide")
st.title("NEMA-AGORA — API Governance Evidence Health")
keys=("audit_events","reconciliations","lifecycles","decisions","cases","queued_reviews","human_reviews","review_reconciliation")
o={"state":"READY_FOR_HUMAN_REVIEW","counts":{k:1 for k in keys}}
r=evaluate_health(o);st.metric("Health",r["state"]);st.metric("Coverage",r["coverage_state"]);st.json(r)
st.info("Synthetic engineering-health view. It does not establish environmental truth, regulatory status, enforcement, or emergency authority.")
