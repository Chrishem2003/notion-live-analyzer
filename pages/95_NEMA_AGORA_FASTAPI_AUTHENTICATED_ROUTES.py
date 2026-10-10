import streamlit as st
st.set_page_config(page_title="NEMA-AGORA Authenticated Routes",layout="wide")
st.title("NEMA-AGORA — Authenticated FastAPI Routes")
st.info("Phase 87 • HTTP authorization boundary • synthetic demonstration")
st.code("""GET /api/v1/spatial-evidence/query
Authorization: Bearer <credential>
request_id=REQ-87
actor_id=ACTOR-1
role=coordinator
""")
st.success("Unauthorized requests terminate before persistent evidence access.")
