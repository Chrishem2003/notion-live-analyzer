"""Page 45: Project Collaboration & Meeting System — Live Collaborative Workspace"""
import streamlit as st
from modules.project_collaboration_ui import render_collaboration_shell, setup_demo_session, COLLAB_CSS

st.set_page_config(
    page_title="Project Collaboration & Meeting System",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Inject Global CSS ──────────────────────────────────────────────────
st.markdown(COLLAB_CSS, unsafe_allow_html=True)

# ── Demo Mode Toggle (top-level, shown before the shell) ───────────────
if "collab_webrtc" not in st.session_state or st.session_state["collab_webrtc"] is None:
    st.markdown("""
    <div style="padding:1rem 1rem 0 1rem;max-width:900px;margin:0 auto;">
        <div style="background:linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                    border:1px solid #312e81;border-radius:20px;padding:2rem;text-align:center;">
            <div style="font-size:3rem;margin-bottom:0.5rem;">🎯</div>
            <h1 style="color:#f1f5f9;font-size:1.8rem;font-weight:800;margin-bottom:0.5rem;">
                Project Collaboration & Meeting System
            </h1>
            <p style="color:#94a3b8;font-size:0.95rem;max-width:600px;margin:0 auto 1.5rem auto;">
                A world-class, hybrid project collaboration & live meeting platform
                combining Zoom-quality video, Figma-like collaborative canvas,
                and Google Classroom-style research management.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 Launch Demo Session", type="primary", use_container_width=True):
            with st.spinner("Setting up demo collaboration session..."):
                setup_demo_session()
            st.rerun()

    # ── Feature Cards ──────────────────────────────────────────────
    st.markdown("""
    <div style="max-width:900px;margin:1rem auto;display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.75rem;">
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:1rem;text-align:center;">
            <div style="font-size:2rem;">🎥</div>
            <div style="color:#f1f5f9;font-weight:700;font-size:0.85rem;margin:0.5rem 0 0.25rem;">WebRTC Engine</div>
            <div style="color:#64748b;font-size:0.7rem;">Adaptive HD video · Spatial audio · Noise suppression · Dual-track publishing</div>
        </div>
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:1rem;text-align:center;">
            <div style="font-size:2rem;">🎨</div>
            <div style="color:#f1f5f9;font-weight:700;font-size:0.85rem;margin:0.5rem 0 0.25rem;">CRDT Canvas</div>
            <div style="color:#64748b;font-size:0.7rem;">Real-time collaboration · Multi-user cursors · Viewport sync · Ghost staging</div>
        </div>
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:1rem;text-align:center;">
            <div style="font-size:2rem;">🤖</div>
            <div style="color:#f1f5f9;font-weight:700;font-size:0.85rem;margin:0.5rem 0 0.25rem;">AI Researcher</div>
            <div style="color:#64748b;font-size:0.7rem;">Action item detection · Live meeting notes · Topic extraction · Sentiment analysis</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Connect Form ───────────────────────────────────────────────
    with st.expander("🔐 Configure Custom Session", expanded=False):
        st.markdown("Enter credentials to connect or generate a new session token.")
        from modules.project_collaboration.project_auth import render_project_auth_ui
        from modules.project_collaboration import ProjectAuthManager

        auth = ProjectAuthManager()
        render_project_auth_ui(auth)

else:
    # ── Render the Collaboration Shell ──────────────────────────────
    render_collaboration_shell()

