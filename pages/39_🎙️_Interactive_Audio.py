"""
🎙️ World-Class Hands-Free Interactive Audio Engine
Enterprise-grade real-time voice synthesis and speech-to-text pipeline featuring neural audio streaming,
bi-directional conversational streaming, voice activity detection (VAD), and low-latency WebRTC audio routing.
"""
import streamlit as st

st.set_page_config(
    page_title="Hands-Free Interactive Audio Engine",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 1. AUDIO SESSION STATE & ENGINE INITIALIZATION
# ==========================================
if "audio_session_active" not in st.session_state:
    st.session_state["audio_session_active"] = False
if "audio_playback_buffer" not in st.session_state:
    st.session_state["audio_playback_buffer"] = []
if "voice_model_profile" not in st.session_state:
    st.session_state["voice_model_profile"] = "Neural HD — Academic Standard"

from modules.interactive_audio_engine import (
    render_interactive_audio_ui,
    init_audio_session_state,
    load_audio_stylesheet
)

# Initialize secure session state and responsive styling pipelines
init_audio_session_state()
load_audio_stylesheet(is_dark=st.session_state.get("theme", "light") == "dark")

# ==========================================
# 2. AUDIO STREAMING CONTROL HUD & CONFIGURATION
# ==========================================

with st.sidebar:
    st.markdown("### 🎛️ Neural Audio Settings")
    voice_profile = st.selectbox(
        "Voice Synthesis Model",
        [
            "Neural HD — Academic Standard",
            "Ultra-Low Latency Stream",
            "Bilingual Academic (EN/Swahili)",
            "Deep Resonance Scientific Voice"
        ],
        key="audio_model_profile_select"
    )
    st.session_state["voice_model_profile"] = voice_profile

    st.markdown("---")
    st.markdown("### 🎙️ Voice Activity Detection (VAD)")
    vad_sensitivity = st.slider("VAD Threshold (Sensitivity)", 0.1, 0.9, 0.65, 0.05, key="audio_vad_threshold")
    noise_suppression = st.selectbox(
        "Background Noise Suppression",
        ["Advanced Spectral Subtraction", "Deep Neural Denoiser", "Standard High-Pass Filter", "Disabled (Raw Audio)"],
        key="audio_denoise_mode"
    )

    st.markdown("---")
    st.markdown("### 🔊 Output Routing & Playback")
    output_sample_rate = st.selectbox("Audio Sample Rate", ["24 kHz (Standard HD)", "48 kHz (Studio Grade)", "16 kHz (Optimized Low-Bandwidth)"], key="audio_sample_rate")
    st.toggle("Auto-Play Incoming Audio Streams", value=True, key="audio_autoplay_toggle")
    st.toggle("Buffered Chunk Streaming (WebRTC)", value=True, key="audio_webrtc_toggle")

# ==========================================
# 3. MAIN INTERACTIVE AUDIO WORKSPACE
# ==========================================

# Render high-performance audio engine interface with bound parameters and active stream handlers
render_interactive_audio_ui(
    model_profile=voice_profile,
    vad_threshold=vad_sensitivity,
    denoise_mode=noise_suppression,
    sample_rate=output_sample_rate
)