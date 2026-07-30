import streamlit as st

st.title("⚡ Energy Grids & Infrastructure Resiliency")
st.caption("Cascading Grid Failure Simulation, Reservoir Strain, and Intermittent Renewable Limits")

col1, col2 = st.columns(2)
col1.metric("Power Grid Cascade Risk", "0.012 (Stable)")
col2.metric("Municipal Water Reservoir Level", "68.5% Capacity")

st.success("⚡ Renewable Grid Penetration safe threshold: Current load at 32% / Max tolerance 45%")
