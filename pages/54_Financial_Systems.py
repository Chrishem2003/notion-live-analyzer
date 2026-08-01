# --- CHRISHEM AUTHOR PROFILE BLOCK ---
import os
import streamlit as st

st.markdown("# **Notion Live Analyzer**")
st.markdown("### **Creator: CHRISHEM**")
st.markdown("---")
# -------------------------------------

import streamlit as st

st.title("🔍 Financial & Macroeconomic Risk Engine")
st.caption("Sovereign Debt Restructuring, Capital Flight Velocity, and Inflation Pass-Through")

col1, col2 = st.columns(2)
with col1:
    st.metric("Capital Flight Velocity Index", "Low (14.2)", delta="-2.1")
    st.info("🔍 **Bond Buyback Signal:** Optimal yield curve window detected for foreign debt refinancing.")

with col2:
    st.metric("Liquidity Coverage Ratio (LCR)", "118.4%", delta="1.2%")
    st.warning("⚠️ **Inflation Warning:** Currency depreciation pass-through predicted to impact food costs in 14 days.")

