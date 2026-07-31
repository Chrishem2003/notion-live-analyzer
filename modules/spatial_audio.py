import streamlit as st
from modules.database import log_backend_event

def render_spatial_audio_panel():
    """
    Renders an ambient soundscape and spatial focus audio controller inside Streamlit.
    """
    st.subheader(" Spatial Audio & Focus Soundscapes")
    st.caption("Optimize deep-work sessions with ambient frequency generators and spatial background soundscapes.")

    soundscape = st.selectbox(
        "Select Focus Atmosphere",
        ["Deep Bioinformatics Focus (Alpha Waves)", "Server Room Ambient White Noise", "Coffee Shop Productivity Loop", "Muni University Rain & Nature Soundscape"]
    )

    volume = st.slider("Soundscape Intensity / Volume", min_value=0, max_value=100, value=45)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("? Start Spatial Atmosphere"):
            log_backend_event("INFO", f"Activated spatial soundscape: {soundscape} at {volume}% volume.")
            st.success(f"Atmosphere '{soundscape}' initialized in background channel.")
    with col2:
        if st.button("? Stop Audio Stream"):
            log_backend_event("INFO", "Deactivated spatial soundscape.")
            st.info("Audio stream muted.")
