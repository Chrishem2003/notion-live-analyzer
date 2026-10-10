import os,tempfile,streamlit as st
from nema_agora.api_governance_review_queue import build_review_item,ApiGovernanceReviewQueue
st.set_page_config(page_title="NEMA-AGORA API Governance Review Queue",layout="wide")
st.title("NEMA-AGORA — API Governance Review Queue")
case={"state":"CASEBOOK_READY","case_id":"API-CASE-DEMO","case_fingerprint":"a"*64,"request_id":"REQ-95-DEMO"}
with tempfile.TemporaryDirectory() as d:
 q=ApiGovernanceReviewQueue(os.path.join(d,"q.db"));q.enqueue(build_review_item(case,90));st.json(q.list())
st.info("Synthetic review queue. Admission does not execute a governance decision.")
