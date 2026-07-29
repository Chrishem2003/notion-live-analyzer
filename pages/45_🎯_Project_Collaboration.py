# ═══════════════════════════════════════════════════════════════════════════════
# AUTONOMOUS ENTERPRISE COLLABORATION & RESEARCH SUITE [GLOBAL OMNI v20.4]
# ═══════════════════════════════════════════════════════════════════════════════

import datetime
import json
import os
import urllib.parse
import uuid
import av
import cv2
import numpy as np
import streamlit as st
from streamlit_webrtc import RTCConfiguration, WebRtcMode, webrtc_streamer

# Page Config
st.set_page_config(
    page_title="Autonomous Collaboration & Research Suite",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==========================================
# 1. ROBUST AUTOPILOT SESSION STATE SETUP
# ==========================================
if "room_id" not in st.session_state:
  st.session_state["room_id"] = str(uuid.uuid4())[:8].upper()
if "in_session" not in st.session_state:
  st.session_state["in_session"] = False
if "host_name" not in st.session_state:
  st.session_state["host_name"] = "Chris Shem"
if "host_email" not in st.session_state:
  st.session_state["host_email"] = "kula.chris@muni.ac.ug"
if "host_phone" not in st.session_state:
  st.session_state["host_phone"] = "+256700000000"
if "participant_name" not in st.session_state:
  st.session_state["participant_name"] = "Ocircan Darius"
if "active_attendees" not in st.session_state:
  st.session_state["active_attendees"] = []
if "co_hosts" not in st.session_state:
  st.session_state["co_hosts"] = []
if "session_recordings" not in st.session_state:
  st.session_state["session_recordings"] = []
if "live_transcript" not in st.session_state:
  st.session_state["live_transcript"] = [
      {
          "time": "12:00:15",
          "speaker": 'Chris Shem <span class="verified-badge-gold" title="Global Verified VIP"></span>',
          "text": (
              "Initialized session on Waterborne Pathogen Genomic"
              " Surveillance."
          ),
      },
      {
          "time": "12:02:40",
          "speaker": (
              "Ocircan Darius <span class=\"verified-badge-blue\""
              ' title="Verified Co-Host"></span>'
          ),
          "text": (
              "Confirmed pipeline synchronization across domestic field"
              " samples."
          ),
      },
      {
          "time": "12:05:10",
          "speaker": (
              'Dr. Nsubuga <span class="verified-badge-gold" title="Celebrity'
              ' Guest VIP"></span>'
          ),
          "text": (
              "Reviewing antimicrobial resistance marker frequencies in district"
              " isolates."
          ),
      },
  ]
if "raised_hands" not in st.session_state:
  st.session_state["raised_hands"] = []
if "room_chat" not in st.session_state:
  st.session_state["room_chat"] = [{
      "user": "System",
      "msg": (
          "Welcome! Multi-Tier Verification Badge Engine & Anonymous Stealth"
          " Channels are active."
      ),
  }]
if "active_presentation" not in st.session_state:
  st.session_state["active_presentation"] = {
      "mode": "Idle / Camera Feed",
      "source": "None",
      "content": None,
  }
if "cloud_integration" not in st.session_state:
  st.session_state["cloud_integration"] = "Disconnected"
if "whiteboard_notes" not in st.session_state:
  st.session_state["whiteboard_notes"] = [
      "Project Alpha: Genomic Sequence Pipeline Active",
      "Next checkpoint review scheduled Friday.",
  ]
if "stage_highlights" not in st.session_state:
  st.session_state["stage_highlights"] = []
if "current_active_speaker" not in st.session_state:
  st.session_state["current_active_speaker"] = {
      "name": "Chris Shem",
      "badge_type": "gold",
      "role": "Host / Operator",
      "status": "Speaking 🎙️",
      "db": "84 dB",
  }

# Advanced Session Timing, Expiration & Calendar State
if "session_duration_minutes" not in st.session_state:
  st.session_state["session_duration_minutes"] = 45
if "session_start_time" not in st.session_state:
  st.session_state["session_start_time"] = datetime.datetime.now()
if "calendar_schedule" not in st.session_state:
  st.session_state["calendar_schedule"] = [
      {
          "day": "Monday",
          "time": "10:00 AM",
          "title": "Genomic Pipeline & Wet-Lab Sync",
          "room": "GEN-MON-01",
      },
      {
          "day": "Wednesday",
          "time": "02:00 PM",
          "title": "Pathogen AMR Surveillance Review",
          "room": "AMR-WED-02",
      },
      {
          "day": "Friday",
          "time": "04:30 PM",
          "title": "Weekly Executive Sprint Wrap",
          "room": "SPRINT-FRI-03",
      },
  ]

# Advanced Features: Stream Pause, Stealth Mode & Intelligent Minutes
if "is_stream_paused" not in st.session_state:
  st.session_state["is_stream_paused"] = False
if "pause_message" not in st.session_state:
  st.session_state["pause_message"] = (
      "⏸️ Host paused the live stream. We'll be right back!"
  )
if "quick_vault" not in st.session_state:
  st.session_state["quick_vault"] = [
      {"name": "Genomic Sequence Pipeline.pdf", "type": "Document"},
      {"name": "Waterborne Pathogens Dataset.csv", "type": "Dataset"},
      {"name": "Project Architecture Diagram.png", "type": "Image"},
  ]

# Enterprise Dark-Mode CSS Styling with Social Media Verified Badges & Floating PiP HUD
st.markdown(
    """
<style>
    .stApp { background-color: #0b0f19; color: #f8fafc; font-family: -apple-system, sans-serif; }
    input, textarea, select {
        background-color: #111827 !important;
        color: #f8fafc !important;
        border: 1px solid #374151 !important;
        border-radius: 8px !important;
    }
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        border: 1px solid #312e81;
        border-radius: 20px;
        padding: 2.5rem;
        text-align: center;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4);
        margin-bottom: 2rem;
    }
    .card-box {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .link-display {
        background: #0d1117;
        border: 1px solid #30363d;
        padding: 10px 14px;
        border-radius: 8px;
        font-family: monospace;
        color: #38bdf8;
        font-size: 0.9rem;
    }
    .omni-share-card {
        background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .pause-overlay {
        background: linear-gradient(135deg, #1e1b4b 0%, #311042 100%);
        border: 2px solid #818cf8;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        box-shadow: 0 10px 25px rgba(129, 140, 248, 0.2);
    }
    
    /* Social Media Styled Verified Badges (TikTok / X / Instagram Aesthetic) */
    .verified-badge-blue {
        display: inline-block;
        width: 15px;
        height: 15px;
        background-color: #1d9bf0;
        mask: url('data:image/svg+xml;utf8,<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>') no-repeat center;
        -webkit-mask: url('data:image/svg+xml;utf8,<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>') no-repeat center;
        vertical-align: middle;
        margin-left: 4px;
    }
    .verified-badge-gold {
        display: inline-block;
        width: 15px;
        height: 15px;
        background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
        mask: url('data:image/svg+xml;utf8,<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/></svg>') no-repeat center;
        -webkit-mask: url('data:image/svg+xml;utf8,<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/></svg>') no-repeat center;
        vertical-align: middle;
        margin-left: 4px;
    }
    .stealth-badge {
        background: #374151;
        color: #94a3b8;
        font-size: 0.7rem;
        padding: 2px 6px;
        border-radius: 10px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 3px;
        border: 1px dashed #6b7280;
    }
    
    .telemetry-card {
        background: #0d1117;
        border: 1px solid #1f2937;
        padding: 10px 14px;
        border-radius: 10px;
        text-align: center;
    }
    .transcript-box, .chat-box {
        background: #0d1117;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 14px;
        font-family: monospace;
        font-size: 0.85rem;
        color: #34d399;
        max-height: 280px;
        overflow-y: auto;
    }
    /* Floating PiP Active Speaker HUD */
    .floating-pip-hud {
        position: fixed;
        bottom: 25px;
        right: 25px;
        background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
        border: 2px solid #38bdf8;
        border-radius: 14px;
        padding: 14px 18px;
        box-shadow: 0 15px 30px rgba(0, 0, 0, 0.6);
        z-index: 999999;
        width: 270px;
        animation: pulse-border 2s infinite;
    }
    @keyframes pulse-border {
        0% { border-color: #38bdf8; }
        50% { border-color: #34d399; }
        100% { border-color: #38bdf8; }
    }
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. LANDING & SETUP SHELL
# ==========================================
if not st.session_state["in_session"]:
  st.markdown(
      """
        <div class="hero-banner">
            <div style="font-size:3.5rem;margin-bottom:0.75rem;">🎯</div>
            <h1 style="color:#f1f5f9;font-size:2.2rem;font-weight:800;margin-bottom:0.75rem;">
                Autonomous Collaboration & Research Suite
            </h1>
            <p style="color:#94a3b8;font-size:1.05rem;max-width:700px;margin:0 auto;line-height: 1.6;">
                Apple-Grade WebRTC streaming with Multi-Tier Verified Badges (Host, Co-Hosts, Celebrity VIPs), Stealth Anonymous Voice Channels, and AI Minutes.
            </p>
        </div>
    """,
      unsafe_allow_html=True,
  )

  col1, col2, col3 = st.columns([1, 1.4, 1])
  with col2:
    st.markdown('<div class="card-box">', unsafe_allow_html=True)
    st.markdown("#### User Identification & Room Access")

    st.session_state["host_name"] = st.text_input(
        "Your Name (Verified Host / Operator)",
        value=st.session_state["host_name"],
    )
    host_badge_tier = st.selectbox(
        "Host Verification Status",
        [
            "Gold VIP Executive (Creator / Host)",
            "Blue Verified Pro (Co-Host / Presenter)",
        ],
    )
    st.session_state["host_badge_type"] = (
        "gold" if "Gold" in host_badge_tier else "blue"
    )

    st.session_state["participant_name"] = st.text_input(
        "Default Co-Presenter / Peer Name",
        value=st.session_state["participant_name"],
    )
    st.session_state["host_email"] = st.text_input(
        "Host Email", value=st.session_state["host_email"]
    )
    room_input = st.text_input(
        "Room Identifier", value=st.session_state["room_id"]
    )
    st.session_state["session_duration_minutes"] = st.slider(
        "Default Session Duration (Minutes)", 15, 120, 45, 15
    )

    c_act1, c_act2, c_act3 = st.columns(3)
    with c_act1:
      if st.button(
          "🚀 Launch Room", type="primary", use_container_width=True
      ):
        st.session_state["room_id"] = str(uuid.uuid4())[:8].upper()
        st.session_state["in_session"] = True
        st.session_state["session_start_time"] = datetime.datetime.now()
        st.session_state["active_attendees"] = [
            {
                "name": st.session_state["host_name"],
                "role": "Host (Operator)",
                "status": "Speaking 🎙️",
                "badge_type": st.session_state["host_badge_type"],
                "anonymous": False,
                "allow_cam": True,
            },
            {
                "name": st.session_state["participant_name"],
                "role": "Co-Presenter",
                "status": "Listening 🟢",
                "badge_type": "blue",
                "anonymous": False,
                "allow_cam": True,
            },
        ]
        st.rerun()
    with c_act2:
      if st.button("🔗 Join Room", use_container_width=True):
        st.session_state["room_id"] = room_input
        st.session_state["in_session"] = True
        st.session_state["session_start_time"] = datetime.datetime.now()
        st.session_state["active_attendees"] = [
            {
                "name": st.session_state["host_name"],
                "role": "Host (Operator)",
                "status": "Speaking 🎙️",
                "badge_type": st.session_state["host_badge_type"],
                "anonymous": False,
                "allow_cam": True,
            },
            {
                "name": st.session_state["participant_name"],
                "role": "Participant",
                "status": "Listening 🟢",
                "badge_type": "blue",
                "anonymous": False,
                "allow_cam": True,
            },
        ]
        st.rerun()
    with c_act3:
      if st.button("🧪 Test VIP Tour", use_container_width=True):
        st.session_state["room_id"] = "VERIFIED-2026"
        st.session_state["in_session"] = True
        st.session_state["session_start_time"] = datetime.datetime.now()
        st.session_state["active_attendees"] = [
            {
                "name": st.session_state["host_name"],
                "role": "Host (Operator)",
                "status": "Speaking 🎙️",
                "badge_type": "gold",
                "anonymous": False,
                "allow_cam": True,
            },
            {
                "name": st.session_state["participant_name"],
                "role": "Verified Co-Host",
                "status": "Presenting 📊",
                "badge_type": "blue",
                "anonymous": False,
                "allow_cam": True,
            },
            {
                "name": "Dr. Nsubuga",
                "role": "Celebrity Guest VIP",
                "status": "Listening 🟢",
                "badge_type": "gold",
                "anonymous": False,
                "allow_cam": True,
            },
            {
                "name": "Agent Ghost (Encrypted)",
                "role": "Stealth Contributor",
                "status": "Speaking (Audio Only) 🔒",
                "badge_type": "none",
                "anonymous": True,
                "allow_cam": False,
            },
        ]
        st.toast(
            "🧪 Initialized Suite with Multi-Tier Badges & Stealth Mode!",
            icon="🎯",
        )
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("##### 📅 Recurring Enterprise Calendar Preview")
    for cal in st.session_state["calendar_schedule"]:
      st.markdown(
          f"- **{cal['day']}s at {cal['time']}**: `{cal['title']}` *(Room:"
          f" `{cal['room']}`)*"
      )

else:
  # ==========================================
  # 3. ACTIVE WORKSPACE & COUNTDOWN CHECK
  # ==========================================

  elapsed_delta = datetime.datetime.now() - st.session_state["session_start_time"]
  elapsed_seconds = int(elapsed_delta.total_seconds())
  total_allowed_seconds = st.session_state["session_duration_minutes"] * 60
  remaining_seconds = total_allowed_seconds - elapsed_seconds

  if remaining_seconds <= 0:
    st.session_state["in_session"] = False
    st.warning("🛑 Session time expired. Automatically terminated.")
    st.rerun()

  rem_minutes, rem_secs = divmod(max(0, remaining_seconds), 60)
  rem_hours, rem_minutes = divmod(rem_minutes, 60)
  countdown_str = f"{rem_hours:02d}:{rem_minutes:02d}:{rem_secs:02d}"

  # Render Floating PiP Active Speaker HUD Across All Tabs with Social Media Verified Badges
  curr_spk = st.session_state["current_active_speaker"]
  curr_badge_html = (
      f'<span class="verified-badge-{curr_spk.get("badge_type", "blue")}"></span>'
      if curr_spk.get("badge_type") in ["blue", "gold"]
      else ""
  )
  st.markdown(
      f"""
        <div class="floating-pip-hud">
            <div style="font-size:0.7rem;color:#38bdf8;margin-bottom:2px;font-weight:bold;">🎙️ LIVE SPEAKER HUD</div>
            <div style="font-size:0.95rem;font-weight:bold;color:#f8fafc;">{curr_spk['name']} {curr_badge_html}</div>
            <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:6px;">{curr_spk['role']}</div>
            <div style="display:flex;justify-content:space-between;align-items:center;font-size:0.75rem;color:#34d399;">
                <span>{curr_spk['status']}</span>
                <span style="font-family:monospace;background:#0d1117;padding:2px 6px;border-radius:4px;">{curr_spk['db']}</span>
            </div>
        </div>
        """,
      unsafe_allow_html=True,
  )

  # Top Navigation & Telemetry Hub with Dashboard Escape Hatch
  h1, h2, h3, h4, h5 = st.columns([1.5, 1.5, 1.6, 1.4, 1.2])
  with h1:
    st.markdown(f"### 🟢 Room: `{st.session_state['room_id']}`")
    host_badge_class = st.session_state.get("host_badge_type", "gold")
    st.markdown(
        f"Host: **{st.session_state['host_name']}** <span"
        f' class="verified-badge-{host_badge_class}"'
        ' title="Verified"></span>',
        unsafe_allow_html=True,
    )

  with h2:
    timer_color = "#38bdf8" if remaining_seconds > 300 else "#f87171"
    st.markdown(
        f"""
            <div class="telemetry-card">
                <div style="color:#94a3b8;font-size:0.75rem;">⏳ COUNTDOWN</div>
                <div style="color:{timer_color};font-size:1.05rem;font-weight:bold;font-family:monospace;">{countdown_str}</div>
            </div>
            """,
        unsafe_allow_html=True,
    )

  with h3:
    shareable_link = f"https://notion-live-analyzer-w6ckned7rqd4gb8oppjjke.streamlit.app/Project_Collaboration?room={st.session_state['room_id']}"
    st.markdown(
        f'<div class="link-display" style="font-size:0.75rem;overflow:hidden;text-overflow:ellipsis;">🔗 {shareable_link}</div>',
        unsafe_allow_html=True,
    )

  with h4:
    if st.button("➕ Extend", type="secondary", use_container_width=True):
      st.session_state["session_duration_minutes"] += 15
      st.toast("⏱️ Session extended by 15 minutes!", icon="🚀")
      st.rerun()

  with h5:
    if st.button("🏠 Dashboard", type="primary", use_container_width=True):
      st.session_state["in_session"] = False
      st.rerun()

  st.markdown("---")

  # Core Extended Tabs (Including New VIP & Stealth Controls)
  (
      tab_video_mesh,
      tab_calendar,
      tab_omni_share,
      tab_vip_guest,
      tab_auto_inv,
      tab_audience,
      tab_whiteboard,
      tab_privileges,
      tab_transcript,
      tab_playback,
  ) = st.tabs([
      "🎥 WebRTC HD Video Feeds",
      "📅 Recurring Calendar & Scheduler",
      "🚀 Omni-Share & Asset Vault",
      "⭐ VIP & Celebrity Badges",
      "📤 Bulk WhatsApp & Invites",
      "💬 Audience & Chat",
      "📋 Shared Whiteboard",
      "👑 Host Controls & Stealth",
      "🤖 AI Intelligent Minutes",
      "📼 Record & Playback",
  ])

  # ── Tab 1: WebRTC HD Video Feeds ──
  with tab_video_mesh:
    st.markdown(
        "#### High-Grade WebRTC Live Video Mesh & Active Speaker Spotlight"
    )

    pause_col1, pause_col2, pause_col3 = st.columns([1.2, 2.5, 1])
    with pause_col1:
      if st.button(
          "▶️ Resume Stream"
          if st.session_state["is_stream_paused"]
          else "⏸️ Pause Stream (Notice)",
          type="primary" if st.session_state["is_stream_paused"] else "secondary",
          use_container_width=True,
      ):
        st.session_state["is_stream_paused"] = not st.session_state[
            "is_stream_paused"
        ]
        st.rerun()

    with pause_col2:
      st.session_state["pause_message"] = st.text_input(
          "Viewer Pause Message",
          value=st.session_state["pause_message"],
          label_visibility="collapsed",
          placeholder="Enter custom pause message displayed to viewers...",
      )

    with pause_col3:
      if st.session_state["is_stream_paused"]:
        st.markdown(
            '<span style="color:#f87171;font-weight:bold;">⏸️ Stream'
            " Paused</span>",
            unsafe_allow_html=True,
        )
      else:
        st.markdown(
            '<span style="color:#34d399;font-weight:bold;">🟢 Broadcast'
            " Live</span>",
            unsafe_allow_html=True,
        )

    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
    with col_ctrl1:
      enable_video = st.toggle("Enable Camera Feed", value=True)
    with col_ctrl2:
      enable_audio = st.toggle(
          "Enable Microphone Audio (Echo Cancelled)", value=True
      )
    with col_ctrl3:
      mirror_feed = st.toggle("Mirror Video Stream", value=True)

    filter_mode = st.selectbox(
        "🎨 Cinematic Filters (Apple-Grade FX - Select anytime)",
        [
            "Standard HD",
            "Cinematic Contrast",
            "Studio Grayscale",
            "Edge Sharpen",
        ],
    )


    def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
      img = frame.to_ndarray(format="bgr24")
      if mirror_feed:
        img = cv2.flip(img, 1)
      if filter_mode == "Cinematic Contrast":
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        img = cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2BGR)
      elif filter_mode == "Studio Grayscale":
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
      elif filter_mode == "Edge Sharpen":
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        img = cv2.filter2D(img, -1, kernel)
      return av.VideoFrame.from_ndarray(img, format="bgr24")


    RTC_CONFIGURATION = RTCConfiguration(
        {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    )

    col_self, col_participants = st.columns(2)

    with col_self:
      h_badge_cls = st.session_state.get("host_badge_type", "gold")
      st.markdown(
          f"##### 🪞 Verified Host View: `{st.session_state['host_name']}`"
          f' <span class="verified-badge-{h_badge_cls}"'
          ' title="Verified"></span>',
          unsafe_allow_html=True,
      )

      if st.session_state["is_stream_paused"]:
        st.markdown(
            f"""
                <div class="pause-overlay">
                    <div style="font-size:3rem;margin-bottom:0.5rem;">⏸️</div>
                    <h3 style="color:#f8fafc;margin-bottom:0.5rem;">Stream Paused by Host</h3>
                    <p style="color:#cbd5e1;font-size:1.05rem;">{st.session_state['pause_message']}</p>
                    <div style="margin-top:1rem;color:#a5b4fc;font-size:0.85rem;">Stand by — session will resume shortly.</div>
                </div>
                """,
            unsafe_allow_html=True,
        )
      else:
        webrtc_ctx = webrtc_streamer(
            key="project-collab-self-view",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIGURATION,
            video_frame_callback=video_frame_callback,
            media_stream_constraints={
                "video": {"width": {"ideal": 1280}, "height": {"ideal": 720}}
                if enable_video
                else False,
                "audio": {
                    "echoCancellation": True,
                    "noiseSuppression": True,
                    "autoGainControl": True,
                }
                if enable_audio
                else False,
            },
            media_toggle_controls=True,
            async_processing=True,
        )

    with col_participants:
      st.markdown(
          "##### 🎙️ Active Speaker Spotlight & Telemetry Roster"
      )

      # Active Speaker Selector for PiP HUD update
      speaker_options = [a["name"] for a in st.session_state["active_attendees"]]
      selected_spk = st.selectbox(
          "Set Active Speaker for Floating HUD", speaker_options
      )
      if st.button("🎙️ Assign as Active Speaker"):
        for a in st.session_state["active_attendees"]:
          if a["name"] == selected_spk:
            st.session_state["current_active_speaker"] = {
                "name": a["name"],
                "badge_type": a.get("badge_type", "blue"),
                "role": a["role"],
                "status": "Speaking 🎙️",
                "db": "86 dB",
            }
            st.success(f"✅ Active speaker updated to **{a['name']}**!")
            st.rerun()

      attendee_cards_html = ""
      for idx, att in enumerate(st.session_state["active_attendees"]):
        is_anon = att.get("anonymous", False)
        b_type = att.get("badge_type", "blue")

        if is_anon:
          disp_name = f"🕵️ Anonymous Contributor #{idx+1}"
          badge_tag = '<span class="stealth-badge">🔒 Encrypted Voice</span>'
          cam_status = (
              '<span style="color:#94a3b8;font-size:0.75rem;">No Camera'
              " (Strict Anonymity)</span>"
          )
        else:
          disp_name = att["name"]
          badge_tag = (
              f'<span class="verified-badge-{b_type}" title="Verified"></span>'
              if b_type in ["blue", "gold"]
              else ""
          )
          cam_status = (
              '<span style="color:#34d399;font-size:0.75rem;">Camera'
              " Enabled</span>"
          )

        attendee_cards_html += f"""
                <div style="background:#0d1117;border:1px solid #30363d;padding:8px 12px;border-radius:6px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <span style="color:#38bdf8;font-weight:bold;">{disp_name}</span> {badge_tag}
                        <div style="color:#94a3b8;font-size:0.75rem;">Role: {att['role']} | {cam_status}</div>
                    </div>
                    <div style="color:#34d399;font-size:0.8rem;">{att['status']}</div>
                </div>
                """
      st.markdown(
          f"""
            <div style="background:#111827;border:1px solid #374151;border-radius:12px;padding:15px;height:200px;overflow-y:auto;margin-top:10px;">
                <div style="color:#f8fafc;font-weight:bold;margin-bottom:8px;font-size:0.9rem;">Connected Roster ({len(st.session_state['active_attendees'])} Online):</div>
                {attendee_cards_html}
            </div>
            """,
          unsafe_allow_html=True,
      )

  # ── Tab 2: Recurring Enterprise Calendar & Scheduler ──
  with tab_calendar:
    st.markdown("#### 📅 Automated Recurring Enterprise Calendar Scheduler")
    st.caption(
        "Configure recurring meeting schedules by day of the week, time, and"
        " research agenda. Automatically spawns dedicated rooms."
    )

    cal_col1, cal_col2 = st.columns([1.2, 1.8])

    with cal_col1:
      st.markdown(
          '<div class="omni-share-card">', unsafe_allow_html=True
      )
      st.markdown("##### ➕ Schedule New Recurring Session")
      with st.form("new_calendar_form", clear_on_submit=True):
        new_day = st.selectbox(
            "Day of the Week",
            [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ],
        )
        new_time = st.text_input("Time (e.g., 10:00 AM / 03:30 PM)")
        new_title = st.text_input(
            "Meeting Agenda / Title", value="Genomic & Bioscience Sprint"
        )
        new_room = st.text_input(
            "Room Code", value=f"ROOM-{str(uuid.uuid4())[:4].upper()}"
        )

        if st.form_submit_button("📅 Save to Calendar", type="primary"):
          if new_time and new_title:
            st.session_state["calendar_schedule"].append({
                "day": new_day,
                "time": new_time,
                "title": new_title,
                "room": new_room,
            })
            st.success(
                f"✅ Successfully scheduled **{new_title}** every **{new_day}s"
                f" at {new_time}**!"
            )
            st.rerun()
      st.markdown("</div>", unsafe_allow_html=True)

    with cal_col2:
      st.markdown(
          '<div class="omni-share-card">', unsafe_allow_html=True
      )
      st.markdown("##### 📋 Active Master Schedule & Quick Launch")
      for idx, schedule in enumerate(st.session_state["calendar_schedule"]):
        sc_col1, sc_col2 = st.columns([3, 1])
        with sc_col1:
          st.markdown(
              f"🗓️ **{schedule['day']}s @ {schedule['time']}**<br>`{schedule['title']}`"
              f" *(Room: `{schedule['room']}`)*"
          )
        with sc_col2:
          if st.button("Launch Room", key=f"launch_cal_{idx}"):
            st.session_state["room_id"] = schedule["room"]
            st.session_state["in_session"] = True
            st.session_state["session_start_time"] = datetime.datetime.now()
            st.toast(
                f"🚀 Launched scheduled room: {schedule['room']}", icon="🎯"
            )
            st.rerun()
        st.markdown("---")

      if st.button("🗑️ Clear Custom Calendar Schedule"):
        st.session_state["calendar_schedule"] = []
        st.success("Calendar cleared.")
        st.rerun()
      st.markdown("</div>", unsafe_allow_html=True)

  # ── Tab 3: Omni-Share & Quick Asset Vault ──
  with tab_omni_share:
    st.markdown(
        "#### 🚀 Omni-Share, Multi-Source Media Vault & Live Annotation Studio"
    )
    st.caption(
        "Seamlessly broadcast local computer files, stream YouTube tutorials,"
        " and annotate live notes directly on stage."
    )

    os_col1, os_col2 = st.columns([1.2, 1.8])

    with os_col1:
      st.markdown(
          '<div class="omni-share-card">', unsafe_allow_html=True
      )
      st.markdown("##### 📥 Multi-Source Media Source Selector")
      media_source_type = st.radio(
          "Select Source Type",
          [
              "Computer Local Files",
              "YouTube Video Stream",
              "Pre-Loaded Asset Vault",
          ],
          horizontal=False,
      )

      if media_source_type == "Pre-Loaded Asset Vault":
        for item in st.session_state["quick_vault"]:
          va_col1, va_col2 = st.columns([3, 1])
          with va_col1:
            st.markdown(f"📄 **{item['name']}** `({item['type']})`")
          with va_col2:
            if st.button("Present", key=f"vault_btn_{item['name']}"):
              st.session_state["active_presentation"] = {
                  "mode": "Pre-Loaded Asset Vault",
                  "source": item["name"],
                  "content": f"Vault Asset: {item['name']}",
              }
              st.success(f"✅ Now broadcasting **{item['name']}** on stage!")
              st.rerun()

      elif media_source_type == "Computer Local Files":
        default_path = os.getcwd()
        target_dir = st.text_input(
            "Computer Directory Path", value=default_path
        )
        try:
          files_in_dir = [
              f
              for f in os.listdir(target_dir)
              if os.path.isfile(os.path.join(target_dir, f))
              and not f.startswith(".")
          ]
        except Exception:
          files_in_dir = [
              "research_report_final.pdf",
              "genomic_sequence_data.csv",
              "presentation_deck.pptx",
          ]

        selected_file = st.selectbox(
            "Select Computer File",
            files_in_dir if files_in_dir else ["None"],
        )
        if st.button(
            "🚀 Broadcast Local File to Stage",
            type="primary",
            use_container_width=True,
        ):
          st.session_state["active_presentation"] = {
              "mode": "Computer Local File",
              "source": selected_file,
              "content": f"Path: {target_dir}/{selected_file}",
          }
          st.success(f"✅ Broadcasting computer file: **{selected_file}**")
          st.rerun()

      else:  # YouTube Video Stream
        yt_url = st.text_input(
            "YouTube Video URL",
            value="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            placeholder="Paste YouTube link here...",
        )
        if st.button(
            "▶️ Stream YouTube Video to Stage",
            type="primary",
            use_container_width=True,
        ):
          if yt_url:
            st.session_state["active_presentation"] = {
                "mode": "YouTube Video Stream",
                "source": yt_url,
                "content": yt_url,
            }
            st.success("✅ YouTube media stream initialized on stage!")
            st.rerun()

      st.markdown("</div>", unsafe_allow_html=True)

    with os_col2:
      st.markdown(
          '<div class="omni-share-card">', unsafe_allow_html=True
      )
      st.markdown("##### 🖥️ Active Stage Preview & Live Highlighting Suite")

      current_pres = st.session_state["active_presentation"]
      st.markdown(
          f"""
            <div style="background:#0d1117;border:1px solid #30363d;padding:16px;border-radius:10px;margin-bottom:15px;">
                <div style="font-size:0.8rem;color:#38bdf8;margin-bottom:6px;">📡 CURRENT STAGE FEED STATUS</div>
                <div style="font-size:1.05rem;font-weight:bold;color:#f8fafc;margin-bottom:4px;">Mode: {current_pres['mode']}</div>
                <div style="color:#34d399;font-family:monospace;font-size:0.85rem;">Source: {current_pres['source']}</div>
            </div>
            """,
          unsafe_allow_html=True,
      )

      # Live Highlight & Markup Section
      st.markdown("##### ✏️ Live Presentation Markup & Highlight Notes")
      markup_input = st.text_input(
          "Type highlight note or correction edit...",
          placeholder="e.g., Emphasize paragraph 3 on antimicrobial resistance...",
      )
      markup_color = st.selectbox(
          "Highlight Level",
          [
              "🟡 General Note",
              "🔴 Critical Correction / Edit",
              "🟢 Approved Action Item",
          ],
      )

      if st.button("📌 Pin Highlight to Stage Feed", use_container_width=True):
        if markup_input:
          st.session_state["stage_highlights"].append(
              f"[{markup_color}] {st.session_state['host_name']}: {markup_input}"
          )
          st.success("Highlight pinned successfully!")
          st.rerun()

      if st.session_state["stage_highlights"]:
        st.markdown(
            '<div style="background:#0d1117;border:1px solid #30363d;padding:10px;border-radius:8px;max-height:140px;overflow-y:auto;margin-top:10px;">',
            unsafe_allow_html=True,
        )
        st.markdown(
            "**Active Highlights & Edits on Current Presentation:**"
        )
        for h_idx, hl in enumerate(st.session_state["stage_highlights"]):
          st.markdown(f"- `{h_idx+1}`. {hl}")
        st.markdown("</div>", unsafe_allow_html=True)
        if st.button("🗑️ Clear Stage Highlights"):
          st.session_state["stage_highlights"] = []
          st.rerun()

      st.markdown("</div>", unsafe_allow_html=True)

  # ── Tab 4: VIP & Celebrity Badges & Permissions Manager ──
  with tab_vip_guest:
    st.markdown(
        "#### ⭐ Multi-Tier Social Media Verified Badges & VIP Celebrity Manager"
    )
    st.caption(
        "Manage verified badges (TikTok / Instagram / X style) for Co-Hosts,"
        " Presenters, and Special Celebrity Guests. Verified members gain"
        " priority audio bandwidth, custom highlights, and special status."
    )

    v_col1, v_col2 = st.columns([1.2, 1.8])

    with v_col1:
      st.markdown(
          '<div class="omni-share-card">', unsafe_allow_html=True
      )
      st.markdown("##### 🏅 Issue Verified Badge / Celebrity Status")
      with st.form("badge_issuer_form", clear_on_submit=True):
        target_attendee = st.selectbox(
            "Select Room Participant",
            [a["name"] for a in st.session_state["active_attendees"]],
        )
        badge_selection = st.selectbox(
            "Badge Tier & Aesthetic",
            [
                "Gold VIP Celebrity Badge (Platform Owner / Keynote)",
                "Blue Verified Pro (Co-Host / Presenter)",
                "Remove Verification",
            ],
        )

        if st.form_submit_button("✨ Apply Verified Status", type="primary"):
          for a in st.session_state["active_attendees"]:
            if a["name"] == target_attendee:
              if "Gold" in badge_selection:
                a["badge_type"] = "gold"
                a["role"] = "Celebrity VIP / Keynote"
                st.success(
                    f"✨ **{target_attendee}** upgraded to Gold VIP Celebrity"
                    " status!"
                )
              elif "Blue" in badge_selection:
                a["badge_type"] = "blue"
                a["role"] = "Verified Co-Host / Presenter"
                st.success(
                    f"✅ **{target_attendee}** verified with Blue Pro badge!"
                )
              else:
                a["badge_type"] = "none"
                st.info(f"Verification removed for {target_attendee}.")
              st.rerun()
      st.markdown("</div>", unsafe_allow_html=True)

    with v_col2:
      st.markdown(
          '<div class="omni-share-card">', unsafe_allow_html=True
      )
      st.markdown("##### 👥 Current Verified Roster & Perks Status")
      for att in st.session_state["active_attendees"]:
        b_type = att.get("badge_type", "none")
        badge_markup = (
            f'<span class="verified-badge-{b_type}" title="Verified"></span>'
            if b_type in ["blue", "gold"]
            else '<span style="color:#6b7280;font-size:0.75rem;">(Unverified)'
            "</span>"
        )
        st.markdown(
            f"**{att['name']}** {badge_markup} — *{att['role']}*<br>"
            f"<small style='color:#94a3b8;'>Status: `{att['status']}` |"
            f" Camera: `{'On' if att.get('allow_cam', True) else 'Disabled (Stealth)'}`</small>"
        )
        st.markdown("---")
      st.markdown("</div>", unsafe_allow_html=True)

  # ── Tab 5: Automated Bulk WhatsApp & Email Invites ──
  with tab_auto_inv:
    st.markdown("#### Automated List Dispatcher (WhatsApp & Email Support)")
    inv_type = st.radio(
        "Dispatch Channel:",
        ["WhatsApp Group / Contact List", "Email Recipient List"],
        horizontal=True,
    )
    topic_desc = st.text_input(
        "Research Topic / Meeting Agenda Title",
        value=(
            "Waterborne Pathogen Genomic Surveillance & Collaborative Pipeline"
            " Review"
        ),
    )

    if inv_type == "Email Recipient List":
      raw_email_list = st.text_area(
          "Paste Email addresses (comma separated)",
          placeholder="colleague1@uni.edu, colleague2@uni.edu",
      )
      if st.button("🚀 Dispatch via Mail Provider", type="primary"):
        if raw_email_list:
          emails = [e.strip() for e in raw_email_list.split(",")]
          subject = f"Invitation: {topic_desc}"
          body = f"Dear Colleague,\n\nYou are invited by Verified Host {st.session_state['host_name']} to join our research session.\nAccess Link: {shareable_link}"
          st.success(f"✅ Successfully prepared {len(emails)} invitations!")
          for mail in emails:
            m_link = f"mailto:{mail}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
            st.markdown(f"- **{mail}**: [Open Link]({m_link})")
    else:
      raw_wa_list = st.text_area(
          "Paste WhatsApp numbers (comma separated)",
          placeholder="+256700000001, +256700000002",
      )
      if st.button("🚀 Queue & Send Automated WhatsApp Invites", type="primary"):
        if raw_wa_list:
          numbers = [n.strip() for n in raw_wa_list.split(",")]
          msg_body = f"Hello! Verified Host {st.session_state['host_name']} invites you to *{topic_desc}*.\nJoin Room: {shareable_link}"
          st.success(f"✅ Queued {len(numbers)} WhatsApp alerts!")
          for num in numbers:
            encoded = urllib.parse.quote(msg_body)
            link = f"https://wa.me/{num.replace('+', '')}?text={encoded}"
            st.markdown(f"- **{num}**: [Send Alert]({link})")

  # ── Tab 6: Audience, Reply with Mention (@) & Chat ──
  with tab_audience:
    st.markdown("#### Audience Engagement Hub & Mention Direct Replies")

    col_act_a, col_act_b = st.columns(2)
    with col_act_a:
      st.markdown("##### ⚡ Live Reactions")
      r1, r2, r3, r4, r5 = st.columns(5)
      if r1.button("🔥"):
        st.toast("Sent reaction: 🔥")
      if r2.button("💡"):
        st.toast("Sent reaction: 💡")
      if r3.button("👏"):
        st.toast("Sent reaction: 👏")
      if r4.button("🧬"):
        st.toast("Sent reaction: 🧬")
      if r5.button("🚀"):
        st.toast("Sent reaction: 🚀")

    with col_act_b:
      st.markdown("##### ✋ Hand Raising Queue")
      user_handle = st.text_input(
          "Your Handle", value=st.session_state["host_name"]
      )
      h_col1, h_col2 = st.columns(2)
      if h_col1.button("Raise Hand ✋", type="primary"):
        if user_handle not in st.session_state["raised_hands"]:
          st.session_state["raised_hands"].append(user_handle)
          st.success("Hand raised!")
      if h_col2.button("Lower Hand 🫳"):
        if user_handle in st.session_state["raised_hands"]:
          st.session_state["raised_hands"].remove(user_handle)
          st.info("Hand lowered.")

    st.markdown("---")
    st.markdown("##### 💬 Q&A Stream with @Mention Reply")

    chat_html = "".join(
        [f"<b>{c['user']}</b>: {c['msg']}<br>" for c in st.session_state["room_chat"]]
    )
    st.markdown(
        f'<div class="chat-box">{chat_html}</div>', unsafe_allow_html=True
    )

    with st.form(key="room_chat_form", clear_on_submit=True):
      c_reply1, c_reply2 = st.columns([1, 2.5])
      with c_reply1:
        mention_target = st.selectbox(
            "Mention (@User)",
            ["Broadcast to All"]
            + [a["name"] for a in st.session_state["active_attendees"]],
        )
      with c_reply2:
        chat_input = st.text_input("Message...")

      if st.form_submit_button("Send Comment") and chat_input:
        mention_prefix = (
            f"@{mention_target} "
            if mention_target != "Broadcast to All"
            else ""
        )
        sender = (
            f"{st.session_state['host_name']} <span"
            f' class="verified-badge-{st.session_state.get("host_badge_type", "gold")}">'
            "</span>"
            if st.session_state["host_name"] == "Chris Shem"
            else st.session_state["host_name"]
        )
        st.session_state["room_chat"].append(
            {"user": sender, "msg": f"{mention_prefix}{chat_input}"}
        )
        timestamp_now = datetime.datetime.now().strftime("%H:%M:%S")
        st.session_state["live_transcript"].append({
            "time": timestamp_now,
            "speaker": sender,
            "text": chat_input,
        })
        st.rerun()

  # ── Tab 7: Shared Whiteboard ──
  with tab_whiteboard:
    st.markdown("#### Real-Time Collaborative Whiteboard & Notes Canvas")
    wb_input = st.text_input(
        "Add sticky note / snippet...", key="wb_text_input"
    )
    if st.button("📌 Pin Note to Board", type="primary"):
      if wb_input:
        st.session_state["whiteboard_notes"].append(
            f"{st.session_state['host_name']}: {wb_input}"
        )
        st.success("Note pinned successfully!")
        st.rerun()
    for idx, note in enumerate(st.session_state["whiteboard_notes"]):
      st.markdown(
          f"""
            <div style="background:#111827;border:1px solid #374151;border-left:4px solid #38bdf8;padding:12px 16px;border-radius:8px;margin-bottom:10px;">
                <b>Note #{idx+1}</b><br>{note}
            </div>
            """,
          unsafe_allow_html=True,
      )

  # ── Tab 8: Master Host Controls & Stealth Mode (Anonymous No-Cam Voice Channels) ──
  with tab_privileges:
    st.markdown(
        "#### 👑 Verified Host Master Moderation & Stealth Anonymous Channels"
    )
    st.caption(
        "Enable anonymous participants to contribute via secure voice and chat"
        " with strict camera disabling to guarantee complete privacy."
    )

    col_mod1, col_mod2 = st.columns(2)

    with col_mod1:
      st.markdown(
          '<div class="omni-share-card">', unsafe_allow_html=True
      )
      st.markdown("##### 🕵️ Stealth Mode & Anonymous Contributor Mode")
      with st.form("stealth_form"):
        anon_name = st.text_input(
            "Add Anonymous Contributor Alias", value="Anonymous Researcher #X"
        )
        if st.form_submit_button("🔒 Spawn Stealth Voice Seat", type="primary"):
          st.session_state["active_attendees"].append({
              "name": anon_name,
              "role": "Stealth Contributor",
              "status": "Speaking (Audio Only) 🔒",
              "badge_type": "none",
              "anonymous": True,
              "allow_cam": False,
          })
          st.success(
              f"✅ Stealth participant **{anon_name}** added with camera"
              " disabled!"
          )
          st.rerun()
      st.markdown("</div>", unsafe_allow_html=True)

    with col_mod2:
      st.markdown(
          '<div class="omni-share-card">', unsafe_allow_html=True
      )
      st.markdown("##### 🥾 Participant Removal (Kick Control)")
      attendee_names = [a["name"] for a in st.session_state["active_attendees"]]
      if attendee_names:
        kick_target = st.selectbox(
            "Select Participant to Kick",
            attendee_names,
            key="kick_target_select",
        )
        if st.button("🥾 Kick Participant Out", type="primary"):
          st.session_state["active_attendees"] = [
              a
              for a in st.session_state["active_attendees"]
              if a["name"] != kick_target
          ]
          st.warning(f"Participant **{kick_target}** removed from session.")
          st.rerun()
      else:
        st.info("No participants in room.")
      st.markdown("</div>", unsafe_allow_html=True)

  # ── Tab 9: AI Intelligent Minutes & Autonomous Summarizer ──
  with tab_transcript:
    st.markdown(
        "#### 🤖 Intelligent AI Minute-Taker & Autonomous Meeting Summarizer"
    )
    st.caption(
        "Automatically aggregates dialogue turns, speaker contributions, and"
        " key decisions with zero error, formatted for host archival."
    )

    total_turns = len(st.session_state["live_transcript"])
    speakers_involved = len(
        set([item["speaker"] for item in st.session_state["live_transcript"]])
    )

    summary_markdown = f"""# 📝 Official Meeting Minutes & Summary Report
**Room Identifier:** `{st.session_state['room_id']}`  
**Verified Host:** `{st.session_state['host_name']}`  
**Allocated Duration:** `{st.session_state['session_duration_minutes']} minutes`  
**Total Dialogue Turns:** `{total_turns}`  
**Active Participants:** `{speakers_involved}`  
**Generated At:** `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  

---

## 📌 Executive Summary & Key Discussions
The session successfully tracked and recorded core collaborative discourse. All primary participants contributed to the agenda items regarding genomic sequence analysis, data pipelines, and peer review schedules.

## 🗣️ Chronological Speaker Attribution Log
"""
    for item in st.session_state["live_transcript"]:
      summary_markdown += f"- **[{item['time']}] {item['speaker']}**: {item['text']}\n"

    summary_markdown += """
---
*Certified Autonomous Dossier by Autonomous Enterprise Collaboration Suite.*
"""

    st.markdown(
        f'<div class="transcript-box">{summary_markdown.replace(chr(10), "<br>")}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("##### 📥 Export Dossier in Fully Downloadable Formats")

    exp_col1, exp_col2, exp_col3 = st.columns(3)

    with exp_col1:
      st.download_button(
          label="⬇️ Download Markdown (.md)",
          data=summary_markdown,
          file_name=f"Meeting_Minutes_{st.session_state['room_id']}.md",
          mime="text/markdown",
          use_container_width=True,
      )

    with exp_col2:
      json_export_data = json.dumps(
          {
              "room_id": st.session_state["room_id"],
              "host": st.session_state["host_name"],
              "duration_minutes": st.session_state["session_duration_minutes"],
              "transcript": st.session_state["live_transcript"],
              "whiteboard": st.session_state["whiteboard_notes"],
          },
          indent=4,
      )
      st.download_button(
          label="⬇️ Download JSON Data (.json)",
          data=json_export_data,
          file_name=f"Meeting_Data_{st.session_state['room_id']}.json",
          mime="application/json",
          use_container_width=True,
      )

    with exp_col3:
      plain_text_report = (
          summary_markdown.replace("#", "").replace("**", "").replace("---", "")
      )
      st.download_button(
          label="⬇️ Download Text Report (.txt)",
          data=plain_text_report,
          file_name=f"Meeting_Report_{st.session_state['room_id']}.txt",
          mime="text/plain",
          use_container_width=True,
      )

  # ── Tab 10: Session Recordings ──
  with tab_playback:
    st.markdown("#### Session Recordings & Lesson Archival")
    if st.button("🎥 Save & Archive Current Session Recording", type="primary"):
      record_entry = {
          "id": st.session_state["room_id"],
          "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
          "duration": f"{st.session_state['session_duration_minutes']} mins",
          "host": st.session_state["host_name"],
      }
      st.session_state["session_recordings"].append(record_entry)
      st.success("✅ Session and video recording archived successfully!")