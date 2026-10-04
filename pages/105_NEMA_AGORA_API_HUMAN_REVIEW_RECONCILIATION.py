import streamlit as st
from nema_agora.api_human_review_reconciliation import reconcile_reviews,review_audit_fingerprint
st.set_page_config(page_title="NEMA-AGORA Human Review Reconciliation",layout="wide")
st.title("NEMA-AGORA — API Human Review Reconciliation")
q={"review_id":"R-97-DEMO","case_id":"C-97-DEMO","case_fingerprint":"a"*64,"request_id":"REQ-97-DEMO"}
c={"case_id":"C-97-DEMO","case_fingerprint":"a"*64}
a={"review_id":"R-97-DEMO","case_id":"C-97-DEMO","case_fingerprint":"a"*64,"request_id":"REQ-97-DEMO","reviewer_actor_id":"ACTOR-DEMO","reviewer_role":"coordinator","outcome":"CONFIRMED_TRACE","reviewed_at":"2026-10-04T12:00:00+00:00"};a["audit_fingerprint"]=review_audit_fingerprint(a)
st.json(reconcile_reviews(queue_items=[q],cases=[c],audits=[a]))
st.info("Synthetic reconciliation; integrity gaps require human control.")
