import streamlit as st
import os

st.set_page_config(page_title="Sovereign Apex Hub", page_icon="🚀", layout="wide")

# Route directly to portal if available, otherwise present home dashboard
if os.path.exists("portal.py"):
    with open("portal.py", "r", encoding="utf-8") as f:
        exec(f.read())
else:
    st.title("🚀 Sovereign Apex Hub")
    st.info("Select a studio from the sidebar navigation to get started.")
