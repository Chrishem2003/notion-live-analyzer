import os,tempfile,streamlit as st
from nema_agora.api_governance_human_review import review_queue_item,ApiHumanReviewAuditRegistry
st.set_page_config(page_title="NEMA-AGORA API Human Review",layout="wide")
st.title("NEMA-AGORA — API Governance Human Review")
item={"state":"QUEUED","review_id":"API-REVIEW-DEMO","case_id":"API-CASE-DEMO","case_fingerprint":"a"*64,"request_id":"REQ-96-DEMO"}
with tempfile.TemporaryDirectory() as d:
 r=ApiHumanReviewAuditRegistry(os.path.join(d,"a.db"))
 a=review_queue_item(item,actor_id="ACTOR-DEMO",role="coordinator",outcome="CONFIRMED_TRACE",reviewed_at="2026-10-04T12:00:00+00:00");r.append(a);st.json(r.list())
st.info("Synthetic human review. Audit evidence is immutable and non-regulatory.")
