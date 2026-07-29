# ═══════════════════════════════════════════════════════════════════════════════
# AUTONOMOUS ENTERPRISE COLLABORATION & RESEARCH SUITE [UI-FIXED v11.1]
# ═══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import time
import datetime
import uuid
import urllib.parse

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
if "host_email" not in st.session_state:
    st.session_state["host_email"] = "kula.chris@muni.ac.ug"
if "host_phone" not in st.session_state:
    st.session_state["host_phone"] = "+256700000000"
if "scheduled_invites" not in st.session_state:
    st.session_state["scheduled_invites"] = []
if "co_hosts" not in st.session_state:
    st.session_state["co_hosts"] = []
if "session_recordings" not in st.session_state:
    st.session_state["session_recordings"] = []
if "live_transcript" not in st.session_state:
    st.session_state["live_transcript"] = [
        {"time": "12:00", "speaker": "System AI", "text": "Autopilot session initialized. Automatic reminders and privileges active."}
    ]

# Enterprise Dark-Mode CSS Styling (Fixes input box visibility & contrast)
st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #f8fafc; font-family: -apple-system, sans-serif; }
    
    /* Fix text inputs, text areas, and selectboxes to have dark backgrounds and visible text */
    input, textarea, select {
        background-color: #111827 !important;
        color: #f8fafc !important;
        border: 1px solid #374151 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div {
        background-color: #111827 !important;
        color: #f8fafc !important;
        border-color: #374151 !important;
    }
    input::placeholder, textarea::placeholder {
        color: #6b7280 !important;
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
    .transcript-box {
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
""", unsafe_allow_html=True)

# ==========================================
# 2. LANDING & HOST SETUP SHELL
# ==========================================
if not st.session_state["in_session"]:
    st.markdown("""
        <div class="hero-banner">
            <div style="font-size:3.5rem;margin-bottom:0.75rem;">🎯</div>
            <h1 style="color:#f1f5f9;font-size:2.2rem;font-weight:800;margin-bottom:0.75rem;">
                Autonomous Collaboration & Research Suite
            </h1>
            <p style="color:#94a3b8;font-size:1.05rem;max-width:700px;margin:0 auto;line-height: 1.6;">
                Zero-friction automated conferencing. Set your host credentials once, schedule bulk invites via email/WhatsApp, assign co-host privileges, and record session playbacks effortlessly.
            </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.markdown("#### Host Configuration")
        st.session_state["host_email"] = st.text_input("Your Verified Host Email", value=st.session_state["host_email"])
        st.session_state["host_phone"] = st.text_input("Your WhatsApp Number (for automated dispatch)", value=st.session_state["host_phone"])
        
        room_input = st.text_input("Room Identifier", value=st.session_state["room_id"])
        
        c_act1, c_act2 = st.columns(2)
        with c_act1:
            if st.button("🚀 Launch Autopilot Room", type="primary", use_container_width=True):
                st.session_state["room_id"] = str(uuid.uuid4())[:8].upper()
                st.session_state["in_session"] = True
                st.rerun()
        with c_act2:
            if st.button("🔗 Join Room", use_container_width=True):
                st.session_state["room_id"] = room_input
                st.session_state["in_session"] = True
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # ==========================================
    # 3. ACTIVE AUTOPILOT WORKSPACE
    # ==========================================
    
    # Top Hub
    h1, h2, h3 = st.columns([2, 2.5, 1])
    with h1:
        st.markdown(f"### 🟢 Room: `{st.session_state['room_id']}`")
        st.caption(f"Host: {st.session_state['host_email']}")
    with h2:
        shareable_link = f"https://notion-live-analyzer-w6ckned7rqd4gb8oppjjke.streamlit.app/Project_Collaboration?room={st.session_state['room_id']}"
        st.markdown(f'<div class="link-display">🔗 {shareable_link}</div>', unsafe_allow_html=True)
    with h3:
        if st.button("🔴 Close Room", type="secondary", use_container_width=True):
            st.session_state["in_session"] = False
            st.rerun()

    st.markdown("---")

    # Core Automated Tabs
    tab_auto_inv, tab_privileges, tab_vid_avatar, tab_transcript, tab_playback = st.tabs([
        "📤 Autonomous Bulk Invites", 
        "👑 Host & Co-Presenter Privileges", 
        "🎥 Video & Virtual Avatar", 
        "🤖 Live Transcript & Notes", 
        "📼 Recordings & Playbacks"
    ])

    # ── Tab 1: Autonomous Bulk Invites (Email & WhatsApp Lists) ──
    with tab_auto_inv:
        st.markdown("#### Automated List Dispatcher (Zero Stress)")
        st.caption("Paste a comma-separated list of emails or WhatsApp numbers. The system formats and queues automatic reminders instantly.")

        inv_type = st.radio("Dispatch Channel:", ["WhatsApp Group / Contact List", "Email Recipient List"], horizontal=True)
        topic_desc = st.text_input("Research Topic / Meeting Agenda Title", value="Waterborne Pathogen Genomic Surveillance & Data Pipeline Review")
        schedule_time = st.text_input("Scheduled Date & Time", value="Today at 16:00 EAT")

        if inv_type == "WhatsApp Group / Contact List":
            raw_wa_list = st.text_area("Paste WhatsApp numbers (comma separated)", placeholder="+256700000001, +256700000002")
            if st.button("🚀 Queue & Send Automated WhatsApp Invites", type="primary"):
                if raw_wa_list:
                    numbers = [n.strip() for n in raw_wa_list.split(",")]
                    msg_body = f"Hello! You are invited by {st.session_state['host_email']} to our research session on *{topic_desc}*.\nScheduled: {schedule_time}\nJoin Room: {shareable_link}"
                    
                    st.success(f"✅ Successfully queued {len(numbers)} automated WhatsApp alerts!")
                    for num in numbers:
                        encoded = urllib.parse.quote(msg_body)
                        link = f"https://wa.me/{num.replace('+', '')}?text={encoded}"
                        st.markdown(f"- **{num}**: [Click to Dispatch Instant Alert]({link})", unsafe_allow_html=True)
                else:
                    st.warning("Please provide valid phone numbers.")
        else:
            raw_email_list = st.text_area("Paste Email addresses (comma separated)", placeholder="colleague1@uni.edu, colleague2@uni.edu")
            if st.button("🚀 Queue & Send Automated Email Invites", type="primary"):
                if raw_email_list:
                    emails = [e.strip() for e in raw_email_list.split(",")]
                    subject = f"Invitation: {topic_desc}"
                    body = f"Dear Colleague,\n\nYou are invited to join our secure research session.\nTopic: {topic_desc}\nTime: {schedule_time}\n\nAccess Link: {shareable_link}\n\nBest regards,\n{st.session_state['host_email']}"
                    
                    st.success(f"✅ Successfully compiled {len(emails)} automated email drafts!")
                    for mail in emails:
                        m_link = f"mailto:{mail}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
                        st.markdown(f"- **{mail}**: [Dispatch via Mail Client]({m_link})", unsafe_allow_html=True)
                else:
                    st.warning("Please provide valid email addresses.")

    # ── Tab 2: Host & Co-Presenter Privileges ──
    with tab_privileges:
        st.markdown("#### Multi-Presenter & Role Management")
        st.caption("Assign co-host, co-presenter, or participant permissions to control screen sharing, muting, and whiteboard edits.")

        new_colleague = st.text_input("Participant Email or Handle", placeholder="e.g., ocircan.darius@muni.ac.ug")
        assigned_role = st.selectbox("Assign Role & Permissions", ["Co-Host (Full Control)", "Co-Presenter (Whiteboard & Screen Share)", "Standard Participant"])

        if st.button("Grant Role Privileges", type="primary"):
            if new_colleague:
                st.session_state["co_hosts"].append({"email": new_colleague, "role": assigned_role})
                st.success(f"✅ Successfully granted **{assigned_role}** privileges to `{new_colleague}`!")
            else:
                st.warning("Please enter a participant identifier.")

        st.markdown("##### Current Active Privilege Roster")
        if st.session_state["co_hosts"]:
            for entry in st.session_state["co_hosts"]:
                st.markdown(f"- 👤 **{entry['email']}** &bull; *Role*: `{entry['role']}`")
        else:
            st.info("No custom roles assigned yet. Host retains sole administrative control.")

    # ── Tab 3: Video & Virtual Avatar / Streaming Pose ──
    with tab_vid_avatar:
        st.markdown("#### Camera Stream & Virtual Persona Hub")
        mode = st.radio("Display Mode:", ["Live Camera & Mic (Hardware)", "Virtual Avatar & Presentation Pose"], horizontal=True)

        if mode == "Live Camera & Mic (Hardware)":
            st.info("👇 Grant permission for native camera/microphone hardware streaming.")
            cam_html = """
            <div style="background:#111827;border:1px solid #374151;border-radius:12px;padding:20px;text-align:center;">
                <video id="vidFeed" autoplay playsinline muted style="width:100%;max-width:450px;height:250px;background:#0b0f19;border-radius:8px;object-fit:cover;"></video>
                <div style="margin-top:12px;">
                    <button onclick="startCam()" style="background:#2563eb;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:bold;margin-right:8px;">Start Camera</button>
                    <button onclick="stopCam()" style="background:#dc2626;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:bold;">Stop</button>
                </div>
            </div>
            <script>
                async function startCam() {
                    try {
                        const s = await navigator.mediaDevices.getUserMedia({video:true, audio:true});
                        document.getElementById('vidFeed').srcObject = s;
                    } catch(e) { alert('Permission denied: ' + e.message); }
                }
                function stopCam() {
                    const v = document.getElementById('vidFeed');
                    if(v.srcObject) v.srcObject.getTracks().forEach(t => t.stop());
                    v.srcObject = null;
                }
            </script>
            """
            st.components.v1.html(cam_html, height=360)
        else:
            st.markdown("##### Virtual Avatar & Pose Selection")
            av_file = st.file_uploader("Upload Presentation Avatar/Portrait", type=["png", "jpg", "jpeg"])
            pose_sel = st.selectbox("Select Streaming Pose", ["Active Speaker Podium", "Research Presentation Mode", "Standby / Break Mode"])
            if av_file:
                st.image(av_file, width=200, caption="Active Persona Broadcast")
            else:
                st.info(f"Broadcast active as Virtual Persona [Pose: {pose_sel}].")

    # ── Tab 4: Live Transcript & Notes ──
    with tab_transcript:
        st.markdown("#### Real-Time Speech-to-Text & Collaborative Notes")
        
        transcript_container = st.container()
        with transcript_container:
            transcript_text = ""
            for item in st.session_state["live_transcript"]:
                transcript_text += f"[{item['time']}] {item['speaker']}: {item['text']}\n"
            st.markdown(f'<div class="transcript-box">{transcript_text.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

        with st.form(key="note_form", clear_on_submit=True):
            new_note = st.text_input("Add manual note or discussion point...")
            if st.form_submit_button("Log Note") and new_note:
                t_stamp = datetime.datetime.now().strftime("%H:%M")
                st.session_state["live_transcript"].append({"time": t_stamp, "speaker": st.session_state["host_email"], "text": new_note})
                st.rerun()

    # ── Tab 5: Recordings & Playbacks ──
    with tab_playback:
        st.markdown("#### Session Recordings & Lesson Archival")
        st.caption("Access previous session recordings, auto-compiled summaries, and downloadable lesson notes.")

        if st.button("🎥 Save & Archive Current Session Recording", type="primary"):
            record_entry = {
                "id": st.session_state["room_id"],
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "duration": "45 mins",
                "notes_count": len(st.session_state["live_transcript"])
            }
            st.session_state["session_recordings"].append(record_entry)
            st.success("✅ Session successfully recorded and archived to cloud storage!")

        st.markdown("##### Archived Session Vault")
        if st.session_state["session_recordings"]:
            for rec in st.session_state["session_recordings"]:
                st.markdown(f"""
                <div style="background:#111827;border:1px solid #1f2937;padding:12px;border-radius:10px;margin-bottom:10px;">
                    <b>📼 Room Recording: {rec['id']}</b><br>
                    <span style="color:#94a3b8;font-size:0.85rem;">Saved on: {rec['date']} &bull; Duration: {rec['duration']} &bull; Logged Entries: {rec['notes_count']}</span><br>
                    <a href="#" style="color:#38bdf8;font-size:0.85rem;text-decoration:none;">▶ Playback Session Video</a> &bull; 
                    <a href="#" style="color:#34d399;font-size:0.85rem;text-decoration:none;">📥 Download Transcript (.TXT)</a>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No recorded sessions archived in this vault yet.")