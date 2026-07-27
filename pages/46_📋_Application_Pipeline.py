"""Page 46: Application Pipeline, Document Vault & Currency Module"""
import streamlit as st
from modules.application_pipeline import render_pipeline_ui

st.set_page_config(
    page_title="Application Pipeline & Document Vault",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)
render_pipeline_ui()

import uuid

# ... inside _render_feed_card(opp, manager, user_id):
# Make the key universally unique to avoid Streamlit collisions
safe_opp_id = opp.get("id", "no_id")
add_key = f"add_pipe_{safe_opp_id}_{uuid.uuid4().hex[:8]}"

if st.button(f"➕ Add '{title[:40]}...' to Pipeline", key=add_key, use_container_width=True):
    # (keep your existing button logic here)