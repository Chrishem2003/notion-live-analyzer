import streamlit as st

st.title("🌾 Agriculture & Food Security Monitor")
st.caption("Grain Reserve Timers, Drought Risk, and Supply Chain Bottleneck Mapping")

c1, c2 = st.columns(2)
c1.metric("National Grain Reserve Timer", "184 Days Buffer")
c2.metric("Fertilizer Price Pass-Through", "+8.4% Cost Burden")

st.error("🚨 **Supply Chain Alert:** Regional border crossing experiencing 36-hour transit delays.")
