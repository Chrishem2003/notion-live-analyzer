# --- CHRISHEM AUTHOR PROFILE BLOCK ---
import os
import streamlit as st

st.sidebar.markdown("---")
st.sidebar.markdown("### ?? App Author")

# Use absolute path relative to the script's directory to avoid working directory mismatches
script_dir = os.path.dirname(os.path.abspath(__file__))
img_path = os.path.join(script_dir, "background.jpg")

if os.path.exists(img_path):
    st.sidebar.image(img_path, caption="CHRISHEM", use_container_width=True)
else:
    st.sidebar.warning(f"Image not found at: {img_path}")

st.sidebar.markdown("**CHRISHEM**")
st.sidebar.markdown("*Data Analyst & Lead Developer*")
st.sidebar.markdown("---")
# -------------------------------------








import streamlit as st
import pandas as pd
import numpy as np

# --- SAFE IMPORT FOR PANDAS PROFILING ---
try:
    from ydata_profiling import ProfileReport
    from streamlit_pandas_profiling import st_profile_report
except ImportError:
    from ydata_profiling import ProfileReport
    def st_profile_report(profile):
        st.components.v1.html(profile.to_html(), height=1000, scrolling=True)

st.header("?? Automated Data Profiling Engine")
st.caption("One-click statistical analysis and correlation mapping.")

if st.button("Generate Environmental Data Profile"):
    with st.spinner("Compiling statistical report..."):
        np.random.seed(42)
        dates = pd.date_range(start="2026-01-01", periods=100)
        env_df = pd.DataFrame({
            "Date": dates,
            "Sea_Level_mm": np.random.normal(loc=150, scale=5, size=100)  np.linspace(0, 10, 100),
            "Water_Temperature_C": np.random.normal(loc=22, scale=2, size=100),
            "Salinity_psu": np.random.uniform(low=32.0, high=37.0, size=100),
            "Sensor_Status": np.random.choice(["Active", "Maintenance", "Offline"], p=[0.8, 0.15, 0.05], size=100)
        })
        
        env_df.loc[10:15, "Water_Temperature_C"] = np.nan 

        st.write("### Raw Dataset Snapshot")
        st.dataframe(env_df.head(), use_container_width=True)

        pr = ProfileReport(env_df, explorative=True, title="Environmental Metrics Profiling Report")
        
        st.write("### Comprehensive Analysis")
        st_profile_report(pr)





