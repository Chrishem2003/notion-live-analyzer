import streamlit as st
from nema_agora.spatial_api_auth import authorize_request
st.set_page_config(page_title="NEMA-AGORA API Authorization",layout="wide")
st.title("NEMA-AGORA — API Authentication & Authorization")
st.info("Phase 85 • deterministic policy • synthetic actors • read-only")
st.json(authorize_request(actor_id="ACTOR-DEMO",role="coordinator",permission="spatial:evidence:query",request_id="REQ-DEMO-085"))
