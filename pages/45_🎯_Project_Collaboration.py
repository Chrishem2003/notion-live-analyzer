"""
🎯 World-Class Project Collaboration & Meeting System — Live Collaborative Workspace
Enterprise-grade hybrid video conferencing and research workspace featuring WebRTC real-time media streaming,
low-latency camera/mic integration, CRDT-powered infinite canvas syncing, and AI-driven automated meeting transcription.
"""
import streamlit as st

st.set_page_config(
    page_title="Project Collaboration & Meeting System",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==========================================
# 1. SESSION STATE & WEBRTC PIPELINE CONFIGURATION
# ==========================================
if "collab_webrtc" not in st.session_state:
    st.session_state["collab_webrtc"] = None
if "meeting_active_status" not in st.session_state:
    st.session_state["meeting_active_status"] = False
if "media_stream_config" not in st.session_state:
    st.session_state["media_stream_config"] = {
        "video_codec": "VP8 / H.264 Adaptive",
        "audio_processing": "Acoustic Echo Cancellation (AEC) + Noise Suppression",
        "resolution": "720p HD @ 30fps"
    }

from modules.project_collaboration_ui import (
    render_collaboration_shell,
    setup_demo_session,
    COLLAB_CSS
)

# Inject Global Collaboration CSS
st.markdown(COLLAB_CSS, unsafe_allow_html=True)

# ==========================================
# 2. LAUNCHER & CONFIGURATION SHELL
# ==========================================

if st.session_state["collab_webrtc"] is None:
    st.markdown("""
    <div style="padding:1rem 1rem 0 1rem;max-width:950px;margin:0 auto;">
        <div style="background:linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                    border:1px solid #312e81;border-radius:24px;padding:2.5rem;text-align:center;box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);">
            <div style="font-size:3.5rem;margin-bottom:0.75rem;">🎯</div>
            <h1 style="color:#f1f5f9;font-size:2rem;font-weight:800;margin-bottom:0.75rem;letter-spacing: -0.025em;">
                Project Collaboration & Meeting System
            </h1>
            <p style="color:#94a3b8;font-size:1.05rem;max-width:680px;margin:0 auto 1.75rem auto;line-height: 1.6;">
                World-class hybrid research infrastructure combining low-latency WebRTC video conferencing,
                real-time CRDT whiteboard canvas sharing, and automated AI transcription pipelines.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Centered Action Controls ──────────────────────────────────────
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        if st.button("🚀 Launch Secure Live Session", type="primary", use_container_width=True):
            with st.spinner("Initializing WebRTC peer connection & media streams..."):
                setup_demo_session()
            st.rerun()

    # ── Advanced Feature Breakdown Grid ───────────────────────────────
    st.markdown("""
    <div style="max-width:950px;margin:1.5rem auto;display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;">
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:18px;padding:1.25rem;text-align:center;">
            <div style="font-size:2.2rem;">🎥</div>
            <div style="color:#f1f5f9;font-weight:700;font-size:0.95rem;margin:0.5rem 0 0.25rem;">WebRTC Media Engine</div>
            <div style="color:#64748b;font-size:0.75rem;line-height: 1.4;">Direct camera/mic stream capture · Hardware acceleration · Echo cancellation</div>
        </div>
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:18px;padding:1.25rem;text-align:center;">
            <div style="font-size:2.2rem;">🎨</div>
            <div style="color:#f1f5f9;font-weight:700;font-size:0.95rem;margin:0.5rem 0 0.25rem;">CRDT Canvas Workspace</div>
            <div style="color:#64748b;font-size:0.75rem;line-height: 1.4;">Conflict-free replicated data types · Multi-user cursor tracking · Live annotation</div>
        </div>
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:18px;padding:1.25rem;text-align:center;">
            <div style="font-size:2.2rem;">🤖</div>
            <div style="color:#f1f5f9;font-weight:700;font-size:0.95rem;margin:0.5rem 0 0.25rem;">AI Research Assistant</div>
            <div style="color:#64748b;font-size:0.75rem;line-height: 1.4;">Automated action item extraction · Real-time transcription · Summarization</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Secure Session Customizer Expander ────────────────────────────
    with st.expander("🔐 Configure Advanced Media & Session Credentials", expanded=False):
        st.markdown("Customize your WebRTC signaling channels, STUN/TURN server endpoints, and room parameters.")
        from modules.project_collaboration.project_auth import render_project_auth_ui
        from modules.project_collaboration import ProjectAuthManager

        auth = ProjectAuthManager()
        render_project_auth_ui(auth)

else:
    # ==========================================
    # 3. ACTIVE COLLABORATION SHELL EXECUTION
    # ==========================================
    render_collaboration_shell()