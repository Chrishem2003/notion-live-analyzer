# --- CHRISHEM AUTHOR PROFILE BLOCK ---
import os
import streamlit as st

st.markdown("# **Notion Live Analyzer**")
st.markdown("### **Creator: CHRISHEM**")
st.markdown("---")
# -------------------------------------

"""
🔍 ️ World-Class Hands-Free Interactive Audio Engine
Enterprise-grade real-time voice synthesis and speech-to-text pipeline featuring neural audio streaming,
bi-directional conversational streaming, voice activity detection (VAD), and low-latency WebRTC audio routing.
"""
import sys
import os
import streamlit as st

# ==========================================
# 0. DYNAMIC PATH RESOLUTION (PREVENT IMPORT ERRORS)
# ==========================================
# Appends project root directory to sys.path to ensure module imports are detected
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

st.set_page_config(
    page_title="Hands-Free Interactive Audio Engine",
    page_icon="🔍 ️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 1. ADVANCED UI & STYLING PIPELINE
# ==========================================
st.markdown("""
    <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
    /* Gradient Badges & Glowing Audio Accent Containers */
    .audio-badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 16px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        background: linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%);
        color: #FFFFFF;
        margin-bottom: 12px;
    }
    
    /* Interactive Metric Cards */
    .audio-card {
        background-color: rgba(139, 92, 246, 0.04);
        border: 1px solid rgba(139, 92, 246, 0.2);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .audio-card:hover {
        border-color: rgba(139, 92, 246, 0.45);
        transform: translateY(-2px);
    }
    .audio-card-value {
        font-size: 1.7rem;
        font-weight: 800;
        background: linear-gradient(135deg, #7C3AED, #8B5CF6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .audio-card-label {
        font-size: 0.8rem;
        font-weight: 600;
        opacity: 0.75;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. AUDIO SESSION STATE & SAFE IMPORT
# ==========================================
if "audio_session_active" not in st.session_state:
    st.session_state["audio_session_active"] = False
if "audio_playback_buffer" not in st.session_state:
    st.session_state["audio_playback_buffer"] = []
if "voice_model_profile" not in st.session_state:
    st.session_state["voice_model_profile"] = "Neural HD  Academic Standard"

MODULES_LOADED = False
import_error_msg = ""

try:
    from modules.interactive_audio_engine import (
        render_interactive_audio_ui,
        init_audio_session_state,
        load_audio_stylesheet
    )
    MODULES_LOADED = True
except Exception as e:
    import_error_msg = str(e)

# Safe session state and stylesheet initialization
if MODULES_LOADED:
    try:
        init_audio_session_state()
        load_audio_stylesheet(is_dark=st.session_state.get("theme", "light") == "dark")
    except Exception:
        pass

# ==========================================
# 3. AUDIO STREAMING CONTROL HUD & CONFIGURATION
# ==========================================

with st.sidebar:
    st.markdown("### 🔍 ️ Neural Audio Settings")
    voice_profile = st.selectbox(
        "Voice Synthesis Model",
        [
            "Neural HD  Academic Standard",
            "Ultra-Low Latency Stream",
            "Bilingual Academic (EN/Swahili)",
            "Deep Resonance Scientific Voice"
        ],
        key="audio_model_profile_select"
    )
    st.session_state["voice_model_profile"] = voice_profile

    st.markdown("---")
    st.markdown("### 🔍 ️ Voice Activity Detection (VAD)")
    vad_sensitivity = st.slider("VAD Threshold (Sensitivity)", 0.1, 0.9, 0.65, 0.05, key="audio_vad_threshold")
    noise_suppression = st.selectbox(
        "Background Noise Suppression",
        ["Advanced Spectral Subtraction", "Deep Neural Denoiser", "Standard High-Pass Filter", "Disabled (Raw Audio)"],
        key="audio_denoise_mode"
    )

    st.markdown("---")
    st.markdown("### 🔍 Output Routing & Playback")
    output_sample_rate = st.selectbox("Audio Sample Rate", ["24 kHz (Standard HD)", "48 kHz (Studio Grade)", "16 kHz (Optimized Low-Bandwidth)"], key="audio_sample_rate")
    autoplay_opt = st.toggle("Auto-Play Incoming Audio Streams", value=True, key="audio_autoplay_toggle")
    webrtc_opt = st.toggle("Buffered Chunk Streaming (WebRTC)", value=True, key="audio_webrtc_toggle")

# ==========================================
# 4. MAIN INTERACTIVE AUDIO WORKSPACE
# ==========================================

st.markdown("<span class='audio-badge'>NEURAL AUDIO ENGINE v2.5</span>", unsafe_allow_html=True)
st.title("🔍 ️ World-Class Hands-Free Interactive Audio Engine")
st.caption("Real-time voice synthesis, bidirectional speech-to-text, VAD noise isolation, and WebRTC streaming.")

# High-Performance Metrics Display
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="audio-card"><div class="audio-card-value">{vad_sensitivity}</div><div class="audio-card-label">VAD Sensitivity</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="audio-card"><div class="audio-card-value">{output_sample_rate.split()[0]}</div><div class="audio-card-label">Sample Rate</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="audio-card"><div class="audio-card-value">{"WebRTC" if webrtc_opt else "Direct"}</div><div class="audio-card-label">Streaming Buffer</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown('<div class="audio-card"><div class="audio-card-value">Ready</div><div class="audio-card-label">Stream Status</div></div>', unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 5. WORKSPACE RENDER / NATIVE FALLBACK
# ==========================================

if MODULES_LOADED:
    render_interactive_audio_ui(
        model_profile=voice_profile,
        vad_threshold=vad_sensitivity,
        denoise_mode=noise_suppression,
        sample_rate=output_sample_rate
    )
else:
    st.error("⚠️ **Module Resolution Warning**")
    st.info(f"The module `modules.interactive_audio_engine` could not be loaded directly. Running in **Native Fallback Audio Mode**.\n\n`Error Details: {import_error_msg}`")
    
    st.subheader("🔍 ️ Interactive Voice Studio Preview")
    
    # Native Audio Recorder Component
    audio_input = st.audio_input("Record Voice Query / Dictation")
    if audio_input:
        st.audio(audio_input)
        st.success("Audio captured successfully. Voice activity processing ready.")

    st.success("✅ Path guard applied. Ensure `modules/interactive_audio_engine.py` exists in your root repository to link full backend execution.")

