
"""
Unified Split-Screen Collaboration Shell UI
Production-grade Tailwind-styled (custom CSS) split-screen collaboration interface featuring:
  - Main Panel: Interactive Yjs research canvas with viewport sync
  - Floating Dock: Live participant video grid  secondary presentation player
  - Interactive Bar: Professional reactions, Ghost Stage toggle, and AI Action-Item feed
  - Role-based UI controls adapted to user permissions

Architecture:
  - Modular panel system with responsive layout
  - Floating dock overlay for video grid
  - Collapsible side panels for reactions, AI feed, and canvas tools
  - Dark theme matching the vault/collaboration design system
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable

import streamlit as st

# Import collaboration modules
from modules.project_collaboration import (
    ProjectAuthManager,
    ProjectRole,
    ProjectTokenPayload,
    WebRTCProvider,
    CollaborativeCanvas,
    ViewportState,
    ViewportSyncMode,
    GhostStage,
    GhostStageState,
    AIResearcher,
    TranscriptSource,
    NoteCategory,
    ActionItem,
    ActionItemPriority,
    ActionItemStatus,
    CursorPosition,
    CursorType,
    CRDTElement,
    CanvasElementType,
    CanvasSnapshot,
    AudioSpatialPosition,
    NoiseSuppressionEngine,
    Participant,
    TrackType,
    TrackQuality,
    ConnectionState,
    get_role_permissions as get_role_permissions_from_auth,
)


# ═══════════════════════════════════════════════════════════════════════
# CSS  Dark Theme Split-Screen Layout
# ═══════════════════════════════════════════════════════════════════════

COLLAB_CSS = """
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
/* ─── Main Layout ──────────────────────────────────────────────── */
.collab-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: #020617;
    color: #e2e8f0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* ─── Top Bar ──────────────────────────────────────────────────── */
.collab-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 1rem;
    background: #0f172a;
    border-bottom: 1px solid #1e293b;
    gap: 1rem;
    flex-wrap: wrap;
}
.collab-topbar-left { display: flex; align-items: center; gap: 0.75rem; }
.collab-topbar-center { display: flex; align-items: center; gap: 0.5rem; }
.collab-topbar-right { display: flex; align-items: center; gap: 0.5rem; }
.collab-topbar-title {
    color: #f1f5f9;
    font-weight: 700;
    font-size: 0.95rem;
    white-space: nowrap;
}
.collab-topbar-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    font-size: 0.65rem;
    font-weight: 700;
}
.collab-badge-host { background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
.collab-badge-cohost { background: rgba(99,102,241,0.15); color: #818cf8; border: 1px solid rgba(99,102,241,0.3); }
.collab-badge-researcher { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
.collab-badge-viewer { background: rgba(100,116,139,0.15); color: #94a3b8; border: 1px solid rgba(100,116,139,0.3); }

/* ─── Split Layout ─────────────────────────────────────────────── */
.collab-split {
    display: flex;
    flex: 1;
    overflow: hidden;
    position: relative;
}
.collab-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    position: relative;
}
.collab-sidebar {
    width: 320px;
    background: #0f172a;
    border-left: 1px solid #1e293b;
    overflow-y: auto;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
}
.collab-sidebar.collapsed { width: 0; border-left: none; overflow: hidden; }

/* ─── Canvas Area ──────────────────────────────────────────────── */
.collab-canvas {
    flex: 1;
    background: #0f172a;
    background-image:
        radial-gradient(circle, #1e293b 1px, transparent 1px);
    background-size: 24px 24px;
    position: relative;
    overflow: hidden;
    cursor: grab;
}
.collab-canvas:active { cursor: grabbing; }
.collab-canvas-element {
    position: absolute;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 0.75rem;
    min-width: 120px;
    min-height: 80px;
    cursor: pointer;
    transition: box-shadow 0.2s, border-color 0.2s;
}
.collab-canvas-element:hover {
    border-color: #6366f1;
    box-shadow: 0 8px 24px rgba(99,102,241,0.15);
}
.collab-canvas-element.selected {
    border-color: #818cf8;
    box-shadow: 0 0 0 2px rgba(129,140,248,0.3);
}
.collab-canvas-cursor {
    position: absolute;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid;
    pointer-events: none;
    transition: left 0.1s, top 0.1s;
    z-index: 100;
}
.collab-canvas-cursor-label {
    position: absolute;
    left: 16px;
    top: -4px;
    font-size: 0.6rem;
    white-space: nowrap;
    color: #94a3b8;
    background: rgba(15,23,42,0.8);
    padding: 1px 4px;
    border-radius: 4px;
}

/* ─── Floating Dock ────────────────────────────────────────────── */
.collab-dock {
    position: absolute;
    bottom: 1rem;
    right: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    z-index: 50;
}
.collab-dock-video-grid {
    display: flex;
    gap: 0.5rem;
    background: rgba(15,23,42,0.9);
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 0.75rem;
    backdrop-filter: blur(12px);
    max-width: 500px;
    overflow-x: auto;
}
.collab-dock-video {
    width: 120px;
    height: 90px;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    flex-shrink: 0;
    position: relative;
    overflow: hidden;
}
.collab-dock-video.active { border-color: #6366f1; }
.collab-dock-video.speaking { border-color: #22c55e; box-shadow: 0 0 12px rgba(34,197,94,0.3); }
.collab-dock-video-label {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(0,0,0,0.7);
    padding: 0.15rem 0.4rem;
    font-size: 0.6rem;
    text-align: center;
    color: #94a3b8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.collab-dock-presentation {
    background: #1e293b;
    border: 1px solid #6366f1;
    border-radius: 12px;
    padding: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* ─── Interactive Bar ──────────────────────────────────────────── */
.collab-ibar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: #0f172a;
    border-top: 1px solid #1e293b;
    flex-wrap: wrap;
}
.collab-ibar-section {
    display: flex;
    align-items: center;
    gap: 0.25rem;
}
.collab-ibar-divider {
    width: 1px;
    height: 24px;
    background: #1e293b;
    margin: 0 0.25rem;
}
.collab-ibar-btn {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 0.35rem 0.6rem;
    font-size: 0.75rem;
    color: #94a3b8;
    cursor: pointer;
    transition: all 0.15s;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    white-space: nowrap;
}
.collab-ibar-btn:hover {
    background: #334155;
    border-color: #6366f1;
    color: #e2e8f0;
}
.collab-ibar-btn.active {
    background: rgba(99,102,241,0.15);
    border-color: #6366f1;
    color: #818cf8;
}
.collab-ibar-btn.danger:hover {
    border-color: #ef4444;
    color: #f87171;
}

/* ─── Sidebar Tabs ─────────────────────────────────────────────── */
.collab-sb-tabs {
    display: flex;
    border-bottom: 1px solid #1e293b;
    background: #0f172a;
    flex-shrink: 0;
}
.collab-sb-tab {
    flex: 1;
    padding: 0.5rem;
    text-align: center;
    font-size: 0.7rem;
    color: #64748b;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.15s;
}
.collab-sb-tab:hover { color: #94a3b8; background: rgba(99,102,241,0.05); }
.collab-sb-tab.active {
    color: #818cf8;
    border-bottom-color: #6366f1;
    font-weight: 600;
}
.collab-sb-content {
    flex: 1;
    overflow-y: auto;
    padding: 0.75rem;
}

/* ─── AI Feed Items ────────────────────────────────────────────── */
.collab-ai-item {
    background: #1e293b;
    border-left: 3px solid #6366f1;
    border-radius: 8px;
    padding: 0.6rem;
    margin-bottom: 0.5rem;
    font-size: 0.75rem;
}
.collab-ai-item.action-item { border-left-color: #f59e0b; }
.collab-ai-item.note { border-left-color: #6366f1; }
.collab-ai-item.summary { border-left-color: #22c55e; }
.collab-ai-item-header {
    display: flex;
    justify-content: space-between;
    color: #64748b;
    font-size: 0.65rem;
    margin-bottom: 0.25rem;
}

/* ─── Professional Reactions ───────────────────────────────────── */
.collab-reactions {
    display: flex;
    gap: 0.25rem;
    flex-wrap: wrap;
}
.collab-reaction-btn {
    background: transparent;
    border: 1px solid #334155;
    border-radius: 999px;
    padding: 0.25rem 0.5rem;
    font-size: 0.7rem;
    color: #94a3b8;
    cursor: pointer;
    transition: all 0.15s;
}
.collab-reaction-btn:hover {
    background: rgba(99,102,241,0.1);
    border-color: #6366f1;
    color: #e2e8f0;
}
.collab-reaction-btn.active {
    background: rgba(99,102,241,0.2);
    border-color: #818cf8;
    color: #818cf8;
}

/* ─── Ghost Stage Banner ───────────────────────────────────────── */
.collab-ghost-banner {
    background: linear-gradient(135deg, rgba(245,158,11,0.1), rgba(217,119,6,0.05));
    border: 1px solid rgba(245,158,11,0.3);
    border-radius: 8px;
    padding: 0.5rem 0.75rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.75rem;
    margin-bottom: 0.5rem;
}
.collab-ghost-banner span { color: #fbbf24; }

/* ─── Responsive ───────────────────────────────────────────────── */
@media (max-width: 1024px) {
    .collab-sidebar { width: 260px; }
    .collab-dock-video-grid { max-width: 300px; }
    .collab-dock-video { width: 90px; height: 68px; }
}
@media (max-width: 768px) {
    .collab-sidebar { display: none; }
    .collab-topbar { font-size: 0.8rem; }
    .collab-ibar { font-size: 0.7rem; }
}
</style>
"""

# ═══════════════════════════════════════════════════════════════════════
# PROFESSIONAL REACTIONS
# ═══════════════════════════════════════════════════════════════════════

PROFESSIONAL_REACTIONS = [
    {"emoji": "✅", "label": "Approve", "id": "approve"},
    {"emoji": "🤔", "label": "Clarify", "id": "clarify"},
    {"emoji": "", "label": "Data Verify", "id": "data_verify"},
    {"emoji": "✋", "label": "Raise Hand", "id": "raise_hand"},
    {"emoji": "💡", "label": "Suggestion", "id": "suggestion"},
    {"emoji": "🔬", "label": "Methodology", "id": "methodology"},
    {"emoji": "⚠️", "label": "Concern", "id": "concern"},
    {"emoji": "🎯", "label": "Action Item", "id": "action_item"},
]


# ═══════════════════════════════════════════════════════════════════════
# COLLABORATION SHELL UI
# ═══════════════════════════════════════════════════════════════════════

def render_collaboration_shell():
    """
    Render the Unified Split-Screen Collaboration Shell.
    This is the main entry point for the collaboration page,
    combining all four modules into a cohesive interface.

    Layout:
      ┌─────────────────────────────────────────────┐
      │  Top Bar (Project info, role, controls)     │
      ├──────────────────────┬──────────────────────┤
      │                      │                      │
      │  Main Canvas         │  Sidebar             │
      │  (Yjs collaborative  │  (Reactions, AI      │
      │   workspace with     │   feed, canvas       │
      │   viewport sync)     │   tools, ghost       │
      │                      │   stage)             │
      │                      │                      │
      ├──────────────────────┴──────────────────────┤
      │  Floating Dock (Video Grid  Presentation)  │
      ├─────────────────────────────────────────────┤
      │  Interactive Bar (Reactions, Controls, AI)  │
      └─────────────────────────────────────────────┘
    """

    # ── Inject CSS ──────────────────────────────────────────────
    st.markdown(COLLAB_CSS, unsafe_allow_html=True)

    # ── Initialize Session State ────────────────────────────────
    _init_collab_state()

    # ── Get State ───────────────────────────────────────────────
    webrtc: Optional[WebRTCProvider] = st.session_state.get("collab_webrtc")
    canvas: Optional[CollaborativeCanvas] = st.session_state.get("collab_canvas")
    ai_researcher: Optional[AIResearcher] = st.session_state.get("collab_ai")
    auth: ProjectAuthManager = st.session_state.get("collab_auth", ProjectAuthManager())
    token_payload: Optional[ProjectTokenPayload] = st.session_state.get("collab_token")
    show_sidebar = st.session_state.get("collab_show_sidebar", True)
    side_tab = st.session_state.get("collab_sidebar_tab", "reactions")
    ghost_active = st.session_state.get("collab_ghost_active", False)
    ghost_stage: Optional[GhostStage] = st.session_state.get("collab_ghost_stage")

    # ─────────────────────────────────────────────────────────────
    # CONNECTION GATE
    # ─────────────────────────────────────────────────────────────
    if not webrtc or webrtc.connection_state == ConnectionState.DISCONNECTED:
        _render_connection_gate(auth, token_payload)
        return

    # ─────────────────────────────────────────────────────────────
    # TOP BAR
    # ─────────────────────────────────────────────────────────────
    local = webrtc.get_local_participant()
    role_badge_class = {
        "host": "collab-badge-host",
        "co_host": "collab-badge-cohost",
        "co-host": "collab-badge-cohost",
        "researcher": "collab-badge-researcher",
    }.get(local.role if local else "viewer", "collab-badge-viewer")

    role_icons = {"host": "", "co_host": "🤝", "researcher": "🔬", "viewer": "👁️"}

    st.markdown(f"""
    <div class="collab-topbar">
        <div class="collab-topbar-left">
            <span class="collab-topbar-title">🎯 {canvas.project_id if canvas else 'Collaborative Workspace'}</span>
            <span class="collab-topbar-badge {role_badge_class}">
                {role_icons.get(local.role if local else 'viewer', '👁️')} {local.role.replace('_', ' ').title() if local else 'Viewer'}
            </span>
            <span class="collab-topbar-badge collab-badge-researcher">
                👥 {webrtc.get_participant_count()}
            </span>
        </div>
        <div class="collab-topbar-center">
            <span style="color:#64748b;font-size:0.75rem;">
                {webrtc.quality_preset.value.upper()} · {'🔇 NS' if webrtc.noise_suppression.is_active else '🎤 Raw'}
            </span>
        </div>
        <div class="collab-topbar-right">
            <span style="font-size:0.7rem;color:#64748b;">
                🟢 {canvas.viewport_sync_mode.value.replace('_', ' ').title() if canvas else 'Free'}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────
    # MAIN SPLIT LAYOUT
    # ─────────────────────────────────────────────────────────────
    split_cols = st.columns([1, 0.3] if show_sidebar else [1, 0.01])

    with split_cols[0]:
        # ── Main Canvas ─────────────────────────────────────────
        _render_canvas_panel(canvas, webrtc, ai_researcher, token_payload, ghost_stage)

        # ── Floating Dock ───────────────────────────────────────
        _render_floating_dock(webrtc, token_payload)

        # ── Interactive Bar ─────────────────────────────────────
        _render_interactive_bar(webrtc, canvas, ai_researcher, token_payload,
                               ghost_active, ghost_stage)

    with split_cols[1]:
        if show_sidebar:
            # ── Sidebar ─────────────────────────────────────────
            _render_sidebar(side_tab, webrtc, canvas, ai_researcher, token_payload)
        else:
            st.markdown("")

    # ── Ghost Stage Banner ──────────────────────────────────────
    if ghost_active and ghost_stage:
        state_icon = {
            GhostStageState.EDITING: "✏️",
            GhostStageState.PENDING_REVIEW: "🔍",
            GhostStageState.MERGING: "🔄",
            GhostStageState.MERGED: "✅",
        }.get(ghost_stage.state, "📝")

        st.markdown(f"""
        <div class="collab-ghost-banner">
            <span>{state_icon} Ghost Stage Active  <strong>{ghost_stage.display_name}</strong></span>
            <span style="color:#94a3b8;">{ghost_stage.state.value.replace('_', ' ').title()} · {len(ghost_stage.elements)} elements staged</span>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# CONNECTION GATE
# ═══════════════════════════════════════════════════════════════════════

def _render_connection_gate(auth: ProjectAuthManager,
                            token_payload: Optional[ProjectTokenPayload]):
    """Render the initial connection/setup screen."""
    st.markdown("""
    <div style="max-width:640px;margin:3rem auto;text-align:center;">
        <div style="font-size:3rem;margin-bottom:1rem;">🎯</div>
        <h1 style="color:#f1f5f9;font-size:1.5rem;font-weight:800;margin-bottom:0.5rem;">
            Project Collaboration Workspace
        </h1>
        <p style="color:#64748b;font-size:0.9rem;margin-bottom:2rem;">
            Connect to a collaborative research session with real-time canvas, 
            video conferencing, spatial audio, and AI-assisted note-taking.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 🎟️ Generate Token")
        with st.form("collab_gate_form"):
            user_id = st.text_input("User ID", value=f"user_{uuid.uuid4().hex[:8]}",
                                    key="gate_user_id")
            project_id = st.text_input("Project ID", value=f"proj_{uuid.uuid4().hex[:8]}",
                                       key="gate_project_id")
            display_name = st.text_input("Display Name", value=f"Researcher_{uuid.uuid4().hex[:4]}",
                                        key="gate_display_name")
            role_str = st.selectbox("Role", options=["host", "co_host", "researcher", "viewer"],
                                    index=2, key="gate_role")

            if st.form_submit_button("🎟️ Generate & Connect", type="primary",
                                     use_container_width=True):
                # Generate token
                role = ProjectRole.from_string(role_str)
                token, payload = auth.create_access_token(
                    user_id=user_id,
                    project_id=project_id,
                    role=role,
                    display_name=display_name,
                )
                st.session_state["collab_token"] = payload
                st.session_state["collab_auth"] = auth
                st.session_state["collab_last_token"] = token

                # Initialize WebRTC
                webrtc = WebRTCProvider(project_id)
                webrtc.connect(user_id, display_name, role_str)
                st.session_state["collab_webrtc"] = webrtc

                # Initialize Canvas
                canvas = CollaborativeCanvas(project_id)
                canvas.set_local_user(user_id, role_str)
                canvas.add_cursor(user_id, display_name)
                canvas.add_viewport(user_id)
                st.session_state["collab_canvas"] = canvas

                # Initialize AI Researcher
                ai = AIResearcher(project_id, user_id)
                ai.start_meeting(f"Research Sync  {project_id[:12]}")
                st.session_state["collab_ai"] = ai

                st.rerun()

    with col2:
        st.markdown("### 🔗 Quick Join")
        st.info("Enter an existing token or session ID to join a running session.")
        with st.form("collab_join_form"):
            token_input = st.text_area("JWT Token or Session ID",
                                       placeholder="eyJhbGciOiJIUzI1NiIs...",
                                       height=100, key="gate_token_input")

            if st.form_submit_button("🔗 Join Session", use_container_width=True):
                token_input = token_input.strip()
                if token_input.startswith("eyJ"):
                    # Validate as JWT
                    is_valid, payload, msg = auth.validate_token(token_input)
                    if is_valid and payload:
                        st.session_state["collab_token"] = payload
                        st.session_state["collab_auth"] = auth
                        # Initialize with payload data
                        webrtc = WebRTCProvider(payload.project_id)
                        webrtc.connect(payload.sub, payload.display_name,
                                       payload.role.label.lower())
                        st.session_state["collab_webrtc"] = webrtc

                        canvas = CollaborativeCanvas(payload.project_id)
                        canvas.set_local_user(payload.sub, payload.role.label.lower())
                        canvas.add_cursor(payload.sub, payload.display_name)
                        canvas.add_viewport(payload.sub)
                        st.session_state["collab_canvas"] = canvas

                        ai = AIResearcher(payload.project_id, payload.sub)
                        ai.start_meeting(f"Research Sync  {payload.project_id[:12]}")
                        st.session_state["collab_ai"] = ai
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    # Assume session ID
                    st.info(f"🔍 Looking up session: {token_input[:16]}...")
                    st.warning("Session lookup not implemented in demo mode. Generate a new token to start.")

    # Show token if generated
    if st.session_state.get("collab_last_token"):
        with st.expander("📝 Generated Token", expanded=False):
            st.code(st.session_state["collab_last_token"], language="text")


# ═══════════════════════════════════════════════════════════════════════
# CANVAS PANEL
# ═══════════════════════════════════════════════════════════════════════

def _render_canvas_panel(canvas: Optional[CollaborativeCanvas],
                         webrtc: Optional[WebRTCProvider],
                         ai_researcher: Optional[AIResearcher],
                         token_payload: Optional[ProjectTokenPayload],
                         ghost_stage: Optional[GhostStage]):
    """Render the main collaborative canvas panel."""
    if not canvas or not webrtc:
        st.info("Canvas not initialized.")
        return

    local = webrtc.get_local_participant()
    permissions = get_role_permissions_from_auth(ProjectRole.from_string(local.role if local else "viewer"))
    can_edit = permissions.get("edit_canvas", False)

    st.markdown("""
    <div style="position:relative;flex:1;display:flex;flex-direction:column;height:500px;border:1px solid #1e293b;border-radius:12px;overflow:hidden;background:#0f172a;">
    """, unsafe_allow_html=True)

    # ── Canvas Toolbar ─────────────────────────────────────────
    tool_cols = st.columns([2, 1, 1, 1, 1, 1])
    with tool_cols[0]:
        st.caption(f"📍 Canvas · {len(canvas.list_elements())} elements")
    with tool_cols[1]:
        if st.button("➕ Add Note", key="canvas_add_note", use_container_width=True,
                    disabled=not can_edit):
            elem = canvas.add_element(
                CanvasElementType.STICKY,
                local.id if local else "unknown",
                x=100 + len(canvas.elements) * 30,
                y=100 + len(canvas.elements) * 30,
                width=220, height=150,
                content={"text": "New research note...", "color": "#1e293b"},
            )
            st.rerun()
    with tool_cols[2]:
        if st.button(" Add Chart", key="canvas_add_chart", use_container_width=True,
                    disabled=not can_edit):
            canvas.add_element(
                CanvasElementType.DATA_VIEW,
                local.id if local else "unknown",
                x=400, y=200, width=300, height=250,
                content={"type": "bar", "title": "New Chart"},
            )
            st.rerun()
    with tool_cols[3]:
        if canvas.grid_enabled:
            if st.button("⊞ Grid On", key="canvas_grid", use_container_width=True):
                canvas.grid_enabled = False
                st.rerun()
        else:
            if st.button("⊟ Grid Off", key="canvas_grid", use_container_width=True):
                canvas.grid_enabled = True
                st.rerun()
    with tool_cols[4]:
        sync_mode = canvas.viewport_sync_mode
        mode_label = {"free": "🔄 Free", "follow_host": " Follow", "follow_cohost": "🤝 Follow"}.get(sync_mode.value, "Free")
        if st.button(mode_label, key="canvas_sync_mode", use_container_width=True):
            if sync_mode == ViewportSyncMode.FREE:
                canvas.set_presenter(local.id if local else "")
            else:
                canvas.clear_presenter()
            st.rerun()

    # ── Canvas simulation ──────────────────────────────────────
    st.markdown('<div style="padding:0.75rem;flex:1;overflow-y:auto;min-height:350px;">', unsafe_allow_html=True)

    # Show ghost stage elements if active
    active_elements = ghost_stage.elements if ghost_stage else canvas.elements

    # Simulate canvas elements display
    visible_elements = [
        e for e in active_elements.values()
        if not e.is_deleted
    ]

    if visible_elements:
        for elem in visible_elements[:8]:
            type_icons = {
                CanvasElementType.STICKY: "📝",
                CanvasElementType.TEXT_NOTE: "📄",
                CanvasElementType.DATA_VIEW: "",
                CanvasElementType.CHART: "📈",
                CanvasElementType.IMAGE: "🖼️",
                CanvasElementType.CODE_BLOCK: "💻",
                CanvasElementType.ARROW: "➡️",
            }
            icon = type_icons.get(elem.type, "📦")
            content_text = elem.content.get("text", "") or elem.content.get("title", elem.type.value)

            # Check if ghost stage (highlight)
            ghost_border = "border:1px solid rgba(245,158,11,0.4);" if ghost_stage and elem.id in ghost_stage.elements else ""

            st.markdown(f"""
            <div class="collab-canvas-element" style="left:{elem.x % 800}px;top:{elem.y % 300}px;{ghost_border}">
                <div style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.3rem;">
                    <span>{icon}</span>
                    <span style="color:#f1f5f9;font-weight:600;font-size:0.8rem;">{elem.type.value.replace('_', ' ').title()}</span>
                    <span style="color:#64748b;font-size:0.6rem;margin-left:auto;">v{elem.version}</span>
                </div>
                <div style="color:#94a3b8;font-size:0.75rem;">{content_text[:80]}</div>
                {f'<div style="color:#64748b;font-size:0.6rem;margin-top:0.3rem;">✏️ {elem.owner_id[:8]}</div>' if can_edit else ''}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Canvas is empty. Add elements using the toolbar above.")

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Cursor positions (simulated) ───────────────────────────
    if canvas.cursors:
        with st.expander("👆 Active Cursors", expanded=False):
            for cid, cursor in canvas.cursors.items():
                if cid == canvas.local_user_id:
                    continue
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:0.5rem;padding:0.2rem 0;font-size:0.75rem;">
                    <span style="display:inline-block;width:10px;height:10px;border-radius:50%;
                                background:{cursor.color};"></span>
                    <span style="color:#f1f5f9;">{cursor.display_name}</span>
                    <span style="color:#64748b;">({cursor.x:.0f}, {cursor.y:.0f})</span>
                </div>
                """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# FLOATING DOCK
# ═══════════════════════════════════════════════════════════════════════

def _render_floating_dock(webrtc: Optional[WebRTCProvider],
                          token_payload: Optional[ProjectTokenPayload]):
    """Render the floating video dock and presentation player."""
    if not webrtc:
        return

    st.markdown('<div class="collab-dock">', unsafe_allow_html=True)

    # ── Video Grid ─────────────────────────────────────────────
    participants = list(webrtc.participants.values())
    if participants:
        video_html = '<div class="collab-dock-video-grid">'
        for p in participants[:6]:
            speaking_class = " speaking" if p.is_speaking else ""
            active_class = " active" if p.id == webrtc.local_participant_id else ""
            initials = p.name[0].upper() if p.name else "?"
            mic_icon = "🎤" if p.is_audio_on else "🔇"
            role_icon = "" if p.role == "host" else "🤝" if p.role == "co_host" else ""
            # Kept on one line: indented lines would be rendered as a markdown code block.
            video_html = (
                f'<div class="collab-dock-video{speaking_class}{active_class}">'
                f'<span style="font-size:1.5rem;font-weight:700;color:#475569;">{initials}</span>'
                f'<div class="collab-dock-video-label">{p.name[:12]} {mic_icon} {role_icon}</div>'
                '</div>'
            )
        video_html = "</div>"
        st.markdown(video_html, unsafe_allow_html=True)

    # ── Presentation Player ────────────────────────────────────
    if webrtc._presentation_active:
        st.markdown("""
        <div class="collab-dock-presentation">
            <span style="font-size:1.2rem;">📺</span>
            <div style="flex:1;">
                <div style="color:#f1f5f9;font-size:0.75rem;font-weight:600;">Presentation Active</div>
                <div style="color:#64748b;font-size:0.65rem;">Dual-track overlay streaming</div>
            </div>
            <span class="collab-ibar-btn" style="font-size:0.65rem;">🔴 LIVE</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# INTERACTIVE BAR
# ═══════════════════════════════════════════════════════════════════════

def _render_interactive_bar(webrtc: Optional[WebRTCProvider],
                            canvas: Optional[CollaborativeCanvas],
                            ai_researcher: Optional[AIResearcher],
                            token_payload: Optional[ProjectTokenPayload],
                            ghost_active: bool,
                            ghost_stage: Optional[GhostStage]):
    """Render the bottom interactive bar with reactions and controls."""
    local = webrtc.get_local_participant() if webrtc else None
    permissions = get_role_permissions_from_auth(
        ProjectRole.from_string(local.role if local else "viewer")
    ) if local else {}

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
    .collab-ibar-st { gap: 0.25rem; display: flex; flex-wrap: wrap; align-items: center; }
    .collab-ibar-st > div { display: flex; gap: 0.25rem; align-items: center; flex-wrap: wrap; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="collab-ibar">', unsafe_allow_html=True)

    # ── Section: Reactions ─────────────────────────────────────
    st.markdown('<div class="collab-ibar-section">', unsafe_allow_html=True)
    for r in PROFESSIONAL_REACTIONS[:4]:
        btn_key = f"reaction_{r['id']}"
        is_active = st.session_state.get(f"collab_reaction_active") == r['id']
        active_class = " active" if is_active else ""

        if st.button(f"{r['emoji']} {r['label']}", key=btn_key,
                    help=f"Send '{r['label']}' reaction"):
            if ai_researcher:
                ai_researcher.generate_note(
                    title=f"Reaction: {r['label']}",
                    content=f"**{r['label']}**  {local.name if local else 'Someone'} reacted with {r['emoji']}",
                    category=NoteCategory.GENERAL,
                    tags=["reaction", r['id']],
                )
            st.session_state["collab_reaction_active"] = r['id']
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<span class="collab-ibar-divider"></span>', unsafe_allow_html=True)

    # ── Section: More Reactions ────────────────────────────────
    st.markdown('<div class="collab-ibar-section">', unsafe_allow_html=True)
    for r in PROFESSIONAL_REACTIONS[4:]:
        if st.button(f"{r['emoji']} {r['label']}", key=f"reaction_{r['id']}_2",
                    help=f"Send '{r['label']}' reaction"):
            if ai_researcher:
                ai_researcher.generate_note(
                    title=f"Reaction: {r['label']}",
                    content=f"**{r['label']}**  {local.name if local else 'Someone'} reacted",
                    category=NoteCategory.GENERAL,
                    tags=["reaction", r['id']],
                )
            st.session_state["collab_reaction_active"] = r['id']
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<span class="collab-ibar-divider"></span>', unsafe_allow_html=True)

    # ── Section: Media Controls ────────────────────────────────
    st.markdown('<div class="collab-ibar-section">', unsafe_allow_html=True)
    if local:
        # Audio toggle
        if st.button("🔇 Mute" if local.is_audio_on else "🎤 Unmute",
                    key="ibar_mute", help="Toggle microphone"):
            webrtc.toggle_mute(local.id, TrackType.AUDIO)
            st.rerun()

        # Video toggle
        if st.button("📹 Off" if local.is_video_on else "📹 On",
                    key="ibar_video", help="Toggle camera"):
            webrtc.toggle_mute(local.id, TrackType.CAMERA)
            st.rerun()

    # Presentation toggle
    if permissions.get("present_screen", False) and local:
        if webrtc._presentation_active:
            if st.button("🛑 Stop Pres", key="ibar_stop_pres", help="Stop presentation"):
                webrtc.stop_presentation(local.id)
                st.rerun()
        else:
            if st.button(" Present", key="ibar_start_pres", help="Start presentation overlay"):
                webrtc.start_presentation(local.id)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<span class="collab-ibar-divider"></span>', unsafe_allow_html=True)

    # ── Section: Ghost Stage ───────────────────────────────────
    if permissions.get("use_ghost_stage", False) and canvas:
        st.markdown('<div class="collab-ibar-section">', unsafe_allow_html=True)

        if not ghost_active:
            if st.button("👻 Ghost Stage", key="ibar_ghost_start",
                        help="Open private sandbox for staging changes"):
                ghost = canvas.start_ghost_stage(
                    local.id if local else "unknown",
                    local.name if local else "Anonymous",
                )
                st.session_state["collab_ghost_stage"] = ghost
                st.session_state["collab_ghost_active"] = True
                st.rerun()
        else:
            if st.button("👻 Merge", key="ibar_ghost_merge", help="Push staged changes live"):
                if ghost_stage:
                    result = ghost_stage.merge_to_main(canvas.elements)
                    st.success(f"Merged: {result['added']} ~{result['updated']} -{result['deleted']}")
                    st.session_state["collab_ghost_active"] = False
                    st.session_state["collab_ghost_stage"] = None
                    st.rerun()

            if st.button("🗑️ Discard", key="ibar_ghost_discard", help="Discard staged changes"):
                if ghost_stage:
                    ghost_stage.discard()
                    st.session_state["collab_ghost_active"] = False
                    st.session_state["collab_ghost_stage"] = None
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<span class="collab-ibar-divider"></span>', unsafe_allow_html=True)

    # ── Section: AI Feed Indicator ─────────────────────────────
    st.markdown('<div class="collab-ibar-section">', unsafe_allow_html=True)
    ai_count = len(ai_researcher.get_open_action_items()) if ai_researcher else 0
    note_count = len(ai_researcher.notes) if ai_researcher else 0
    st.markdown(f"""
    <span style="color:#64748b;font-size:0.7rem;">
        🤖 AI: {ai_count} actions · {note_count} notes
    </span>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# SIDEBAR PANEL
# ═══════════════════════════════════════════════════════════════════════

def _render_sidebar(active_tab: str, webrtc: Optional[WebRTCProvider],
                    canvas: Optional[CollaborativeCanvas],
                    ai_researcher: Optional[AIResearcher],
                    token_payload: Optional[ProjectTokenPayload]):
    """Render the right sidebar with multiple tabbed panels."""

    # ── Tabs ───────────────────────────────────────────────────
    tabs = [
        {"id": "reactions", "label": "💬", "tooltip": "Reactions & Notes"},
        {"id": "aifeed", "label": "🤖", "tooltip": "AI Feed"},
        {"id": "tools", "label": "🔧", "tooltip": "Canvas Tools"},
        {"id": "participants", "label": "👥", "tooltip": "Participants"},
    ]

    tab_html = '<div class="collab-sb-tabs">'
    for t in tabs:
        active = " active" if active_tab == t["id"] else ""
        tab_html = f'<div class="collab-sb-tab{active}" onclick="alert(\'tab\')">{t["label"]}</div>'
    tab_html = '</div>'
    st.markdown(tab_html, unsafe_allow_html=True)

    # Use Streamlit tabs for actual functionality
    actual_tabs = st.tabs([t["tooltip"] for t in tabs])
    tab_map = {t["tooltip"]: t["id"] for t in tabs}

    for tab_idx, (tab_name, tab_id) in enumerate(tab_map.items()):
        with actual_tabs[tab_idx]:
            if tab_id == "reactions":
                _render_reactions_tab(ai_researcher)
            elif tab_id == "aifeed":
                _render_aifeed_tab(ai_researcher)
            elif tab_id == "tools":
                _render_tools_tab(canvas, webrtc)
            elif tab_id == "participants":
                _render_participants_tab(webrtc, canvas)


def _render_reactions_tab(ai_researcher: Optional[AIResearcher]):
    """Render the reactions and notes tab."""
    st.markdown("### 💬 Meeting Notes")
    if ai_researcher and ai_researcher.notes:
        for note in sorted(ai_researcher.notes.values(),
                          key=lambda x: x.generated_at, reverse=True)[:10]:
            cat_icons = {
                NoteCategory.ACTION_ITEM: "🎯",
                NoteCategory.DECISION: "✅",
                NoteCategory.QUESTION: "❓",
                NoteCategory.FINDING: "💡",
                NoteCategory.GENERAL: "📝",
            }
            icon = cat_icons.get(note.category, "📝")
            ts = datetime.fromtimestamp(note.generated_at).strftime("%H:%M")
            st.markdown(f"""
            <div class="collab-ai-item note">
                <div class="collab-ai-item-header">
                    <span>{icon} {note.category.value}</span>
                    <span>{ts}</span>
                </div>
                <div style="color:#e2e8f0;">{note.title[:60]}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No notes yet. Use the reactions bar or AI researcher to generate notes.")


def _render_aifeed_tab(ai_researcher: Optional[AIResearcher]):
    """Render the AI action items feed tab."""
    st.markdown("### 🤖 AI Action Items")

    if ai_researcher:
        open_items = ai_researcher.get_open_action_items()
        if open_items:
            for item in open_items[:10]:
                priority_colors = {
                    ActionItemPriority.CRITICAL: "#ef4444",
                    ActionItemPriority.HIGH: "#f59e0b",
                    ActionItemPriority.MEDIUM: "#6366f1",
                    ActionItemPriority.LOW: "#64748b",
                }
                color = priority_colors.get(item.priority, "#64748b")
                st.markdown(f"""
                <div class="collab-ai-item action-item" style="border-left-color:{color};">
                    <div class="collab-ai-item-header">
                        <span>{item.priority.value.upper()}</span>
                        <span>{item.confidence:.0%} confidence</span>
                    </div>
                    <div style="color:#e2e8f0;">{item.description[:80]}</div>
                    {f'<div style="color:#64748b;font-size:0.65rem;margin-top:0.2rem;">👤 {item.assignee_name}</div>' if item.assignee_name else ''}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No action items detected. Start a meeting with AI recording.")

        # Transcript input mini
        st.markdown("### 🎤 Quick Transcript")
        text = st.text_area("", placeholder="Type meeting transcription...",
                           height=60, key="ai_feed_transcript",
                           label_visibility="collapsed")
        speaker = st.text_input("Speaker", value="You", key="ai_feed_speaker")
        if st.button("📝 Process", use_container_width=True) and text:
            ai_researcher.ingest_transcript(
                text=text,
                speaker_id=speaker.lower().replace(" ", "_"),
                speaker_name=speaker,
            )
            st.rerun()
    else:
        st.info("AI Researcher not initialized. Connect to enable.")


def _render_tools_tab(canvas: Optional[CollaborativeCanvas],
                      webrtc: Optional[WebRTCProvider]):
    """Render the canvas tools tab."""
    st.markdown("### 🔧 Canvas Tools")

    if not canvas:
        st.info("Canvas not available.")
        return

    # --- Element type buttons ---
    st.markdown("**Add Elements**")
    can_edit = False
    if webrtc and webrtc.get_local_participant():
        can_edit = get_role_permissions_from_auth(
            ProjectRole.from_string(webrtc.get_local_participant().role)
        ).get("edit_canvas", False)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Sticky Note", key="tool_sticky", disabled=not can_edit):
            canvas.add_element(CanvasElementType.STICKY, "user", 200, 200,
                              content={"text": "New sticky note...", "color": "#1e293b"})
            st.rerun()
        if st.button("📄 Text", key="tool_text", disabled=not can_edit):
            canvas.add_element(CanvasElementType.TEXT_NOTE, "user", 300, 300,
                              content={"text": "Enter text here..."})
            st.rerun()
    with col2:
        if st.button(" Chart", key="tool_chart", disabled=not can_edit):
            canvas.add_element(CanvasElementType.DATA_VIEW, "user", 400, 200,
                              content={"type": "line", "title": "Data View"})
            st.rerun()
        if st.button("💻 Code", key="tool_code", disabled=not can_edit):
            canvas.add_element(CanvasElementType.CODE_BLOCK, "user", 500, 300,
                              content={"language": "python", "code": "# code here"})
            st.rerun()

    # --- Canvas settings ---
    st.markdown("**Canvas Settings**")
    canvas.grid_enabled = st.toggle("Show Grid", value=canvas.grid_enabled, key="tool_grid")
    canvas.snap_to_grid = st.toggle("Snap to Grid", value=canvas.snap_to_grid, key="tool_snap")

    # --- Viewport sync ---
    st.markdown("**Viewport Sync**")
    sync_mode = st.selectbox(
        "Mode",
        options=[m.value for m in ViewportSyncMode],
        index=[m.value for m in ViewportSyncMode].index(canvas.viewport_sync_mode.value),
        key="tool_sync_mode",
    )
    canvas.viewport_sync_mode = ViewportSyncMode(sync_mode)


def _render_participants_tab(webrtc: Optional[WebRTCProvider],
                              canvas: Optional[CollaborativeCanvas]):
    """Render the participants list tab."""
    st.markdown("### 👥 Participants")

    if not webrtc:
        st.info("No participants.")
        return

    for pid, p in webrtc.participants.items():
        is_local = pid == webrtc.local_participant_id
        role_icons = {
            "host": "", "co_host": "🤝", "researcher": "🔬", "viewer": "👁️",
        }
        role_icon = role_icons.get(p.role, "👤")
        local_tag = " (You)" if is_local else ""

        # Cursor position info
        cursor_info = ""
        if canvas and pid in canvas.cursors:
            c = canvas.cursors[pid]
            cursor_info = f"📍 ({c.x:.0f}, {c.y:.0f})"

        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:0.5rem;padding:0.4rem 0;
                    border-bottom:1px solid #1e293b;font-size:0.8rem;">
            <div style="width:32px;height:32px;border-radius:8px;
                        background:linear-gradient(135deg,#1e293b,#334155);
                        display:flex;align-items:center;justify-content:center;font-weight:700;color:#94a3b8;">
                {p.name[0].upper()}
            </div>
            <div style="flex:1;min-width:0;">
                <div style="color:#f1f5f9;font-weight:600;font-size:0.75rem;overflow:hidden;text-overflow:ellipsis;">
                    {p.name[:16]}{local_tag}
                </div>
                <div style="display:flex;gap:0.3rem;align-items:center;font-size:0.65rem;">
                    <span>{role_icon} {p.role.replace('_', ' ').title()}</span>
                    <span>{'🎤' if p.is_audio_on else '🔇'}</span>
                    <span>{'📹' if p.is_video_on else '📹❌'}</span>
                    {f'<span style="color:#64748b;">{cursor_info}</span>' if cursor_info else ''}
                </div>
            </div>
            {f'<span class="collab-ibar-btn">🤚</span>' if p.is_hand_raised else ''}
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _init_collab_state():
    """Initialize collaboration session state."""
    defaults = {
        "collab_webrtc": None,
        "collab_canvas": None,
        "collab_ai": None,
        "collab_auth": ProjectAuthManager(),
        "collab_token": None,
        "collab_last_token": None,
        "collab_show_sidebar": True,
        "collab_sidebar_tab": "reactions",
        "collab_ghost_active": False,
        "collab_ghost_stage": None,
        "collab_reaction_active": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ═══════════════════════════════════════════════════════════════════════
# DEMO SETUP
# ═══════════════════════════════════════════════════════════════════════

def setup_demo_session():
    """Set up a full demo collaboration session with sample data."""
    from modules.project_collaboration.webrtc_provider import create_demo_session

    # Create demo WebRTC session
    webrtc = create_demo_session()
    st.session_state["collab_webrtc"] = webrtc

    # Create demo canvas with sample elements
    canvas = CollaborativeCanvas("demo_research_project")
    canvas.set_local_user("host_001", "host")
    canvas.add_cursor("host_001", "Dr. Sarah Chen")

    # Add demo elements
    sample_elements = [
        ("Research Question: How does AI impact clinical outcomes?",
         CanvasElementType.STICKY, 50, 50),
        ("Literature Review: 23 papers analyzed, 15 show significant effects",
         CanvasElementType.TEXT_NOTE, 350, 80),
        ("Data View: Correlation Matrix",
         CanvasElementType.DATA_VIEW, 100, 280),
        ("Python Analysis Code",
         CanvasElementType.CODE_BLOCK, 500, 250),
    ]
    for text, etype, x, y in sample_elements:
        canvas.add_element(etype, "host_001", x, y,
                          content={"text": text, "type": "analysis"})

    # Add remote cursors
    remote_users = [
        ("cohost_001", "Prof. Miller", "#818cf8"),
        ("researcher_001", "Dr. Watson", "#34d399"),
        ("viewer_001", "Alex Kim", "#fbbf24"),
    ]
    for uid, name, color in remote_users:
        c = canvas.add_cursor(uid, name)
        import random
        c.update(random.randint(100, 700), random.randint(50, 350))
        canvas.add_viewport(uid)

    st.session_state["collab_canvas"] = canvas

    # Create demo AI Researcher
    ai = AIResearcher("demo_research_project", "host_001")
    ai.start_meeting("Research Sync  AI in Clinical Outcomes")
    ai.add_participant("host_001", "Dr. Sarah Chen")
    ai.add_participant("cohost_001", "Prof. Miller")
    ai.add_participant("researcher_001", "Dr. Watson")

    # Feed some demo transcript
    demo_texts = [
        ("Let's analyze the correlation between AI adoption and patient outcomes.",
         "host_001", "Dr. Sarah Chen"),
        ("I'll check the literature for recent meta-analyses on this topic.",
         "cohost_001", "Prof. Miller"),
        ("The preliminary data shows a 23% improvement in diagnostic accuracy.",
         "researcher_001", "Dr. Watson"),
        ("We should control for hospital size and patient demographics.",
         "host_001", "Dr. Sarah Chen"),
        ("I'll prepare a multiple regression model for the next meeting.",
         "cohost_001", "Prof. Miller"),
    ]
    for text, sid, name in demo_texts:
        ai.ingest_transcript(text, sid, name)

    st.session_state["collab_ai"] = ai

    # Generate auth token
    auth = ProjectAuthManager()
    token, payload = auth.create_access_token(
        user_id="host_001",
        project_id="demo_research_project",
        role=ProjectRole.HOST,
        display_name="Dr. Sarah Chen",
    )
    st.session_state["collab_auth"] = auth
    st.session_state["collab_token"] = payload

    return webrtc



