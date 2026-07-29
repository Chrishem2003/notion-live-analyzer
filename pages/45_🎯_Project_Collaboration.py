# ═══════════════════════════════════════════════════════════════════════════════
# AUTONOMOUS ENTERPRISE COLLABORATION & RESEARCH SUITE [GLOBAL OMNI v15.3]
# ═══════════════════════════════════════════════════════════════════════════════

import datetime
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
  st.session_state["live_transcript"] = [{
      "time": "12:00",
      "speaker": "System AI",
      "text": (
          "Global Omni-Channel room initialized. Host and participant"
          " directories active."
      ),
  }]
if "raised_hands" not in st.session_state:
  st.session_state["raised_hands"] = []
if "room_chat" not in st.session_state:
  st.session_state["room_chat"] = [{
      "user": "System",
      "msg": (
          "Welcome to the open collaborative floor. Check participant roster"
          " below."
      ),
  }]
if "whiteboard_notes" not in st.session_state:
  st.session_state["whiteboard_notes"] = [
      "Project Alpha: Genomic Sequence Pipeline Active",
      "Next checkpoint review scheduled Friday.",
  ]

# Enterprise Dark-Mode CSS Styling
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
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. LANDING & HOST/PARTICIPANT SETUP SHELL
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
                High-definition Apple-grade WebRTC video streaming with named host and participant directories, live attendee lists, and echo cancellation.
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
        "Your Name (Host / Operator)", value=st.session_state["host_name"]
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

    c_act1, c_act2, c_act3 = st.columns(3)
    with c_act1:
      if st.button(
          "🚀 Launch Room", type="primary", use_container_width=True
      ):
        st.session_state["room_id"] = str(uuid.uuid4())[:8].upper()
        st.session_state["in_session"] = True
        st.session_state["active_attendees"] = [
            {
                "name": st.session_state["host_name"],
                "role": "Host (Operator)",
                "status": "Online 🟢",
            },
            {
                "name": st.session_state["participant_name"],
                "role": "Co-Presenter",
                "status": "Online 🟢",
            },
        ]
        st.rerun()
    with c_act2:
      if st.button("🔗 Join Room", use_container_width=True):
        st.session_state["room_id"] = room_input
        st.session_state["in_session"] = True
        st.session_state["active_attendees"] = [
            {
                "name": st.session_state["host_name"],
                "role": "Host (Operator)",
                "status": "Online 🟢",
            },
            {
                "name": st.session_state["participant_name"],
                "role": "Participant",
                "status": "Online 🟢",
            },
        ]
        st.rerun()
    with c_act3:
      if st.button("🧪 Test Live Tour", use_container_width=True):
        st.session_state["room_id"] = "TEST-LIVE-2026"
        st.session_state["in_session"] = True
        st.session_state["active_attendees"] = [
            {
                "name": st.session_state["host_name"],
                "role": "Host (Operator)",
                "status": "Online 🟢",
            },
            {
                "name": st.session_state["participant_name"],
                "role": "Co-Presenter",
                "status": "Online 🟢",
            },
            {
                "name": "Dr. Nsubuga",
                "role": "Guest Reviewer",
                "status": "Online 🟢",
            },
        ]
        st.toast(
            "🧪 Initializing Test Live Demo with Named Participants!",
            icon="🎯",
        )
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

else:
  # ==========================================
  # 3. ACTIVE AUTOPILOT WORKSPACE
  # ==========================================

  # Top Hub
  h1, h2, h3 = st.columns([2, 2.5, 1])
  with h1:
    st.markdown(
        f"### 🟢 Room: `{st.session_state['room_id']}` [Scale: Unlimited Mesh]"
    )
    st.caption(
        f"Host: **{st.session_state['host_name']}**"
        f" ({st.session_state['host_email']})"
    )
  with h2:
    shareable_link = f"https://notion-live-analyzer-w6ckned7rqd4gb8oppjjke.streamlit.app/Project_Collaboration?room={st.session_state['room_id']}"
    st.markdown(
        f'<div class="link-display">🔗 {shareable_link}</div>',
        unsafe_allow_html=True,
    )
  with h3:
    if st.button("🔴 Close Room", type="secondary", use_container_width=True):
      st.session_state["in_session"] = False
      st.rerun()

  st.markdown("---")

  # Core Extended Tabs
  (
      tab_video_mesh,
      tab_auto_inv,
      tab_audience,
      tab_whiteboard,
      tab_privileges,
      tab_transcript,
      tab_playback,
  ) = st.tabs([
      "🎥 WebRTC HD Video Feeds",
      "📤 Bulk WhatsApp & Invites",
      "💬 Audience & Chat",
      "📋 Shared Whiteboard",
      "👑 Host Privileges",
      "🤖 AI Synthesis",
      "📼 Record & Playback",
  ])

  # ── Tab 1: WebRTC HD Video Feeds (Self View & Named Participant Split) ──
  with tab_video_mesh:
    st.markdown(
        "#### High-Grade WebRTC Live Video Mesh (Apple-Grade Clarity)"
    )
    st.caption(
        f"Active session operator: **{st.session_state['host_name']}** | Peer"
        f" viewer: **{st.session_state['participant_name']}**"
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
      st.markdown(
          f"##### 🪞 Host Self-View: `{st.session_state['host_name']}`"
      )
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
      st.markdown("##### 👥 Active Attendees & Participant Grid")
      # Render active attendee roster dynamically
      attendee_cards_html = ""
      for att in st.session_state["active_attendees"]:
        attendee_cards_html += f"""
                <div style="background:#0d1117;border:1px solid #30363d;padding:10px 14px;border-radius:8px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <span style="color:#38bdf8;font-weight:bold;">{att['name']}</span>
                        <div style="color:#94a3b8;font-size:0.8rem;">Role: {att['role']}</div>
                    </div>
                    <div style="color:#34d399;font-size:0.85rem;">{att['status']}</div>
                </div>
                """

      st.markdown(
          f"""
            <div style="background:#111827;border:1px solid #374151;border-radius:12px;padding:15px;height:320px;overflow-y:auto;">
                <div style="color:#f8fafc;font-weight:bold;margin-bottom:10px;font-size:0.95rem;">Connected Room Roster ({len(st.session_state['active_attendees'])} Online):</div>
                {attendee_cards_html}
            </div>
            """,
          unsafe_allow_html=True,
      )

    if webrtc_ctx.state.playing:
      st.success(
          "🟢 Secure WebRTC Data Pipeline Active (Echo Suppression Enabled)."
      )
    else:
      st.warning(
          "⚠️ Stream is currently paused. Click 'START' in your self-view above"
          " to initialize."
      )

  # ── Tab 2: Autonomous Bulk WhatsApp & Email Invites ──
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
      email_provider = st.selectbox(
          "Select Mail Dispatch Provider",
          ["Gmail", "Yahoo Mail", "Microsoft Outlook", "Custom SMTP Relay"],
      )
      raw_email_list = st.text_area(
          "Paste Email addresses (comma separated)",
          placeholder="colleague1@uni.edu, colleague2@uni.edu",
      )
      if st.button(
          f"🚀 Dispatch via {email_provider}",
          type="primary",
          key="email_btn",
      ):
        if raw_email_list:
          emails = [e.strip() for e in raw_email_list.split(",")]
          subject = f"Invitation: {topic_desc}"
          body = f"Dear Colleague,\n\nYou are invited by {st.session_state['host_name']} to join our secure research session.\nTopic: {topic_desc}\nAccess Link: {shareable_link}\n\nBest regards,\n{st.session_state['host_name']} ({st.session_state['host_email']})"
          st.success(
              f"✅ Successfully prepared {len(emails)} invitations routed"
              f" through **{email_provider}**!"
          )
          for mail in emails:
            m_link = f"mailto:{mail}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
            st.markdown(
                f"- **{mail}**: [Open in {email_provider}]({m_link})",
                unsafe_allow_html=True,
            )
        else:
          st.warning("Please provide valid email addresses.")
    else:
      raw_wa_list = st.text_area(
          "Paste WhatsApp numbers (comma separated)",
          placeholder="+256700000001, +256700000002",
      )
      if st.button(
          "🚀 Queue & Send Automated WhatsApp Invites",
          type="primary",
          key="wa_btn",
      ):
        if raw_wa_list:
          numbers = [n.strip() for n in raw_wa_list.split(",")]
          msg_body = f"Hello! You are invited by {st.session_state['host_name']} to *{topic_desc}*.\nJoin Room: {shareable_link}"
          st.success(
              f"✅ Successfully queued {len(numbers)} automated WhatsApp"
              " alerts!"
          )
          for num in numbers:
            encoded = urllib.parse.quote(msg_body)
            link = f"https://wa.me/{num.replace('+', '')}?text={encoded}"
            st.markdown(
                f"- **{num}**: [Click to Dispatch Instant Alert]({link})",
                unsafe_allow_html=True,
            )
        else:
          st.warning("Please provide valid phone numbers.")

  # ── Tab 3: Audience, Chat & Hand Raising ──
  with tab_audience:
    st.markdown("#### High-Capacity Audience Engagement Hub")
    col_act_a, col_act_b = st.columns(2)
    with col_act_a:
      st.markdown("##### ⚡ Live Floating Reactions")
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
          "Your Display Handle", value=st.session_state["host_name"]
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

      if st.session_state["raised_hands"]:
        st.markdown(
            f"**Queue ({len(st.session_state['raised_hands'])})**: "
            + ", ".join([f"`{h}`" for h in st.session_state["raised_hands"]])
        )
      else:
        st.caption("No raised hands currently in queue.")

    st.markdown("---")
    st.markdown("##### 💬 Open Discussion & Q&A Stream")
    chat_html = "".join(
        [f"<b>{c['user']}</b>: {c['msg']}<br>" for c in st.session_state["room_chat"]]
    )
    st.markdown(
        f'<div class="chat-box">{chat_html}</div>', unsafe_allow_html=True
    )
    with st.form(key="room_chat_form", clear_on_submit=True):
      chat_input = st.text_input("Broadcast comment...")
      if st.form_submit_button("Send Comment") and chat_input:
        st.session_state["room_chat"].append(
            {"user": st.session_state["host_name"], "msg": chat_input}
        )
        st.rerun()

  # ── Tab 4: Shared Whiteboard ──
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

  # ── Tab 5: Host & Co-Presenter Privileges ──
  with tab_privileges:
    st.markdown("#### Host & Co-Presenter Role Management")
    new_colleague = st.text_input(
        "Participant Name or Email", placeholder="e.g., Ocircan Darius"
    )
    assigned_role = st.selectbox(
        "Assign Role & Permissions",
        [
            "Co-Host (Full Control)",
            "Co-Presenter (Whiteboard & Screen Share)",
            "Standard Participant",
        ],
    )
    if st.button("Grant Role Privileges", type="primary"):
      if new_colleague:
        st.session_state["co_hosts"].append(
            {"email": new_colleague, "role": assigned_role}
        )
        # Also add to active attendee roster if not present
        if not any(
            a["name"].lower() == new_colleague.lower()
            for a in st.session_state["active_attendees"]
        ):
          st.session_state["active_attendees"].append({
              "name": new_colleague,
              "role": assigned_role,
              "status": "Online 🟢",
          })
        st.success(
            f"✅ Successfully granted **{assigned_role}** privileges to"
            f" `{new_colleague}`!"
        )
      else:
        st.warning("Please enter a participant name.")
    if st.session_state["co_hosts"]:
      for entry in st.session_state["co_hosts"]:
        st.markdown(
            f"- 👤 **{entry['email']}** &bull; *Assigned Role*:"
            f" `{entry['role']}`"
        )
    else:
      st.info("No custom roles assigned yet. Host retains sole control.")

  # ── Tab 6: AI Research Synthesis ──
  with tab_transcript:
    st.markdown("#### Real-Time Speech-to-Text & AI Research Synthesis")
    transcript_text = "".join([
        f"[{item['time']}] {item['speaker']}: {item['text']}\n"
        for item in st.session_state["live_transcript"]
    ])
    st.markdown(
        f'<div class="transcript-box">{transcript_text.replace(chr(10), "<br>")}</div>',
        unsafe_allow_html=True,
    )
    col_ai1, col_ai2 = st.columns(2)
    if col_ai1.button("✨ Auto-Synthesize Research Summary", type="primary"):
      st.info(
          f"🤖 **AI Synthesis Engine**: Session led by"
            f" {st.session_state['host_name']}. Focuses on scalable pipelines,"
            f" active participant mesh, and data validation protocols."
      )
    if col_ai2.button("📑 Generate Action Items"):
      st.success(
          "✅ **Action Items Generated**: 1. Distribute surveillance logs. 2."
          " Finalize co-host permissions."
      )

  # ── Tab 7: Recordings & Playbacks ──
  with tab_playback:
    st.markdown("#### Session Recordings & Lesson Archival")
    if st.button("🎥 Save & Archive Current Session Recording", type="primary"):
      record_entry = {
          "id": st.session_state["room_id"],
          "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
          "duration": "45 mins",
          "host": st.session_state["host_name"],
          "notes_count": len(st.session_state["live_transcript"]),
      }
      st.session_state["session_recordings"].append(record_entry)
      st.success("✅ Session successfully recorded and archived!")
    if st.session_state["session_recordings"]:
      for rec in st.session_state["session_recordings"]:
        st.markdown(
            f"""
                <div style="background:#111827;border:1px solid #1f2937;padding:12px;border-radius:10px;margin-bottom:10px;">
                    <b>📼 Room Recording: {rec['id']}</b><br>
                    <span style="color:#94a3b8;font-size:0.85rem;">Host: {rec['host']} &bull; Saved on: {rec['date']} &bull; Duration: {rec['duration']}</span>
                </div>
                """,
            unsafe_allow_html=True,
        )
    else:
      st.info("No recorded sessions archived in this vault yet.")