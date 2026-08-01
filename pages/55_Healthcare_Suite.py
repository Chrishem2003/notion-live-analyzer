# --- CHRISHEM AUTHOR PROFILE BLOCK ---
import os
import streamlit as st

st.markdown("# **Notion Live Analyzer**")
st.markdown("### **Creator: CHRISHEM**")
st.markdown("---")
# -------------------------------------

import streamlit as st

st.title("🔍 Public Health & Healthcare Preparedness Suite")
st.caption("ICU Triage Forecasting, Supply-Chain Exhaustion, and Genomic Mutation Tracking")

col1, col2, col3 = st.columns(3)
col1.metric("Days to ICU Saturation", "42 Days", delta="5 Days")
col2.metric("Critical Pharma Stocks", "88% Capacity")
col3.metric("Pathogen Mutation Index", "Variant Risk: Low")

st.progress(0.74, text="Regional Medical Staff Allocation Balance")

