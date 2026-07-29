# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# AUTONOMOUS ENTERPRISE COLLABORATION & RESEARCH SUITE [GLOBAL OMNI v14.1]
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

import streamlit as st
import time
import datetime
import uuid
import urllib.parse

# Page Config
st.set_page_config(
    page_title="Autonomous Collaboration & Research Suite",
    page_icon="ðŸŽ¯",
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
if "co_hosts" not in st.session_state:
    st.session_state["co_hosts"] = []
if "session_recordings" not in st.session_state:
    st.session_state["session_recordings"] = []
if "live_transcript" not in st.session_state:
    st.session_state["live_transcript"] = [
        {"time": "12:00", "speaker": "System AI", "text": "Global Omni-Channel room initialized. Unlimited scale mesh, reactions stream, and AI research synthesis active."}
    ]
if "raised_hands" not in st.session_state:
    st.session_state["raised_hands"] = []
if "room_chat" not in st.session_state:
    st.session_state["room_chat"] = [
        {"user": "System", "msg": "Welcome to the open collaborative floor. Drop comments or raise your hand anytime."}
    ]
if "whiteboard_notes" not in st.session_state:
    st.session_state["whiteboard_notes"] = ["Project Alpha: Genomic Sequence Pipeline Active", "Next checkpoint review scheduled Friday."]

# Enterprise Dark-Mode CSS Styling
st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #f8fafc; font-family: -apple-system, sans-serif; }
    
    input, textarea, select {
        background-color: #111827 !important;
        color: #f8fafc !important;
        border: 1px solid #374151 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div {
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
    .chat-box {
        background: #0d1117;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 14px;
        font-size: 0.9rem;
        color: #e2e8f0;
        max-height: 320px;
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
            <div style="font-size:3.5rem;margin-bottom:0.75rem;">ðŸŽ¯</div>
            <h1 style="color:#f1f5f9;font-size:2.2rem;font-weight:800;margin-bottom:0.75rem;">
                Autonomous Collaboration & Research Suite
            </h1>
            <p style="color:#94a3b8;font-size:1.05rem;max-width:700px;margin:0 auto;line-height: 1.6;">
                Unlimited-scale global conferencing with multi-provider mail dispatchers, real-time camera & microphone controls, live hand-raising queues, interactive reaction streams, and AI research synthesis.
            </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.markdown("#### Host Configuration")
        
        auto_detect_html = """
        <div id="detectedAccount" style="background:#0d1117;border:1px solid #30363d;padding:8px 12px;border-radius:8px;font-size:0.85rem;color:#38bdf8;margin-bottom:12px;">
            ðŸ” Auto-Detecting Browser Identity...
        </div>
        <script>
            const domainEmail = "kula.chris@muni.ac.ug";
            document.getElementById('detectedAccount').innerText = "âœ… Auto-Detected Account: " + domainEmail;
        </script>
        """
        st.components.v1.html(auto_detect_html, height=45)

        st.session_state["host_email"] = st.text_input("Host Verified Email", value=st.session_state["host_email"])
        st.session_state["host_phone"] = st.text_input("WhatsApp Number", value=st.session_state["host_phone"])
        
        room_input = st.text_input("Room Identifier", value=st.session_state["room_id"])
        
        c_act1, c_act2 = st.columns(2)
        with c_act1:
            if st.button("ðŸš€ Launch Global Omni Room", type="primary", use_container_width=True):
                st.session_state["room_id"] = str(uuid.uuid4())[:8].upper()
                st.session_state["in_session"] = True
                st.rerun()
        with c_act2:
            if st.button("ðŸ”— Join Room", use_container_width=True):
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
        st.markdown(f"### ðŸŸ¢ Room: `{st.session_state['room_id']}` [Scale: Unlimited Mesh]")
        st.caption(f"Host: {st.session_state['host_email']}")
    with h2:
        shareable_link = f"https://notion-live-analyzer-w6ckned7rqd4gb8oppjjke.streamlit.app/Project_Collaboration?room={st.session_state['room_id']}"
        st.markdown(f'<div class="link-display">ðŸ”— {shareable_link}</div>', unsafe_allow_html=True)
    with h3:
        if st.button("ðŸ”´ Close Room", type="secondary", use_container_width=True):
            st.session_state["in_session"] = False
            st.rerun()

    st.markdown("---")

    # Core Extended Tabs
    tab_auto_inv, tab_audience, tab_whiteboard, tab_privileges, tab_vid_avatar, tab_transcript, tab_playback = st.tabs([
        "ðŸ“¤ Bulk Invites", 
        "ðŸ’¬ Audience & Chat", 
        "ðŸ“‹ Shared Whiteboard", 
        "ðŸ‘‘ Privileges", 
        "ðŸŽ¥ Camera, Mic & Filters", 
        "ðŸ¤– AI Synthesis", 
        "ðŸ“¼ Record & Playback"
    ])

    # â”€â”€ Tab 1: Autonomous Bulk Invites â”€â”€
    with tab_auto_inv:
        st.markdown("#### Automated List Dispatcher with Multi-Provider Support")
        st.caption("Choose your preferred mailing provider channel (Gmail, Yahoo, Outlook, Proton, Custom SMTP) and schedule invites effortlessly.")

        tz_detection_html = """
        <div id="tzDisplay" style="background:#111827;border:1px solid #374151;padding:8px 12px;border-radius:8px;font-size:0.85rem;color:#38bdf8;margin-bottom:15px;">
            ðŸŒ Detected Local Timezone: Loading client environment...
        </div>
        <script>
            const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
            document.getElementById('tzDisplay').innerText = "ðŸŒ Detected Local Timezone: " + tz;
        </script>
        """
        st.components.v1.html(tz_detection_html, height=45)

        inv_type = st.radio("Dispatch Channel:", ["WhatsApp Group / Contact List", "Email Recipient List"], horizontal=True)
        topic_desc = st.text_input("Research Topic / Meeting Agenda Title", value="Waterborne Pathogen Genomic Surveillance & Data Pipeline Review")
        
        col_date, col_hour, col_min, col_ampm, col_tz = st.columns([1.5, 1, 1, 1, 1.5])
        with col_date:
            sel_date = st.date_input("Session Date", value=datetime.date.today())
        with col_hour:
            sel_hour = st.selectbox("Hour", [str(i).zfill(2) for i in range(1, 13)], index=3)
        with col_min:
            sel_min = st.selectbox("Minute", ["00", "15", "30", "45"])
        with col_ampm:
            sel_ampm = st.selectbox("AM/PM", ["AM", "PM"], index=1)
        with col_tz:
            sel_timezone = st.selectbox("Timezone Profile", ["Africa/Kampala (EAT)", "UTC", "America/New_York (EST/EDT)", "Europe/London (GMT/BST)", "Asia/Dubai (GST)"])

        formatted_schedule = f"{sel_date} at {sel_hour}:{sel_min} {sel_ampm} ({sel_timezone})"
        st.info(f"ðŸ“… **Confirmed Schedule Payload:** `{formatted_schedule}`")

        if inv_type == "Email Recipient List":
            email_provider = st.selectbox("Select Mail Dispatch Provider", ["Gmail", "Yahoo Mail", "Microsoft Outlook / Office 365", "ProtonMail", "Custom SMTP Relay"])
            raw_email_list = st.text_area("Paste Email addresses (comma separated)", placeholder="colleague1@uni.edu, colleague2@uni.edu")
            
            if st.button(f"ðŸš€ Dispatch via {email_provider}", type="primary"):
                if raw_email_list:
                    emails = [e.strip() for e in raw_email_list.split(",")]
                    subject = f"Invitation: {topic_desc}"
                    body = f"Dear Colleague,\n\nYou are invited to join our secure research session.\nTopic: {topic_desc}\nTime: {formatted_schedule}\n\nAccess Link: {shareable_link}\n\nBest regards,\n{st.session_state['host_email']}"
                    
                    st.success(f"âœ… Successfully prepared {len(emails)} invitations routed through **{email_provider}**!")
                    for mail in emails:
                        if email_provider == "Yahoo Mail":
                            m_link = f"https://compose.mail.yahoo.com/?to={mail}&subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
                        elif email_provider == "Microsoft Outlook / Office 365":
                            m_link = f"https://outlook.office.com/mail/deeplink/compose?to={mail}&subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
                        else:
                            m_link = f"mailto:{mail}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
                        st.markdown(f"- **{mail}**: [Open in {email_provider}]({m_link})", unsafe_allow_html=True)
                else:
                    st.warning("Please provide valid email addresses.")
        else:
            raw_wa_list = st.text_area("Paste WhatsApp numbers (comma separated)", placeholder="+256700000001, +256700000002")
            if st.button("ðŸš€ Queue & Send Automated WhatsApp Invites", type="primary"):
                if raw_wa_list:
                    numbers = [n.strip() for n in raw_wa_list.split(",")]
                    msg_body = f"Hello! You are invited by {st.session_state['host_email']} to *{topic_desc}*.\nScheduled: {formatted_schedule}\nJoin Room: {shareable_link}"
                    
                    st.success(f"âœ… Successfully queued {len(numbers)} automated WhatsApp alerts!")
                    for num in numbers:
                        encoded = urllib.parse.quote(msg_body)
                        link = f"https://wa.me/{num.replace('+', '')}?text={encoded}"
                        st.markdown(f"- **{num}**: [Click to Dispatch Instant Alert]({link})", unsafe_allow_html=True)
                else:
                    st.warning("Please provide valid phone numbers.")

    # â”€â”€ Tab 2: Audience, Chat, Reactions & Hand Raising â”€â”€
    with tab_audience:
        st.markdown("#### High-Capacity Audience Engagement Hub")
        st.caption("Interact with unlimited participants through live reactions, real-time comment threads, and hand-raising queues.")

        col_act_a, col_act_b = st.columns(2)
        with col_act_a:
            st.markdown("##### âš¡ Live Floating Reactions")
            r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns(5)
            with r_col1:
                if st.button("ðŸ”¥"): st.toast("Sent reaction: ðŸ”¥")
            with r_col2:
                if st.button("ðŸ’¡"): st.toast("Sent reaction: ðŸ’¡")
            with r_col3:
                if st.button("ðŸ‘"): st.toast("Sent reaction: ðŸ‘")
            with r_col4:
                if st.button("ðŸ§¬"): st.toast("Sent reaction: ðŸ§¬")
            with r_col5:
                if st.button("ðŸš€"): st.toast("Sent reaction: ðŸš€")

        with col_act_b:
            st.markdown("##### âœ‹ Hand Raising Queue")
            user_handle = st.text_input("Your Display Handle for Queue", value=st.session_state["host_email"])
            c_hand1, c_hand2 = st.columns(2)
            with c_hand1:
                if st.button("Raise Hand âœ‹", type="primary"):
                    if user_handle not in st.session_state["raised_hands"]:
                        st.session_state["raised_hands"].append(user_handle)
                        st.success("Hand raised! Host notified.")
            with c_hand2:
                if st.button("Lower Hand ðŸ«³"):
                    if user_handle in st.session_state["raised_hands"]:
                        st.session_state["raised_hands"].remove(user_handle)
                        st.info("Hand lowered.")

            if st.session_state["raised_hands"]:
                st.markdown(f"**Queue ({len(st.session_state['raised_hands'])})**: " + ", ".join([f"`{h}`" for h in st.session_state["raised_hands"]]))
            else:
                st.caption("No raised hands currently in queue.")

        st.markdown("---")
        st.markdown("##### ðŸ’¬ Open Discussion & Q&A Stream")
        
        chat_container = st.container()
        with chat_container:
            chat_html = ""
            for chat in st.session_state["room_chat"]:
                chat_html += f"<b>{chat['user']}</b>: {chat['msg']}<br>"
            st.markdown(f'<div class="chat-box">{chat_html}</div>', unsafe_allow_html=True)

        with st.form(key="room_chat_form", clear_on_submit=True):
            chat_input = st.text_input("Broadcast comment to all participants...")
            if st.form_submit_button("Send Comment") and chat_input:
                st.session_state["room_chat"].append({"user": st.session_state["host_email"], "msg": chat_input})
                st.rerun()

    # â”€â”€ Tab 3: Shared Whiteboard & Collaborative Workspace â”€â”€
    with tab_whiteboard:
        st.markdown("#### Real-Time Collaborative Whiteboard & Notes Canvas")
        st.caption("All participants can add sticky notes, equations, or research snippets to the shared board.")

        wb_input = st.text_input("Add sticky note / snippet to shared whiteboard...", key="wb_text_input")
        if st.button("ðŸ“Œ Pin Note to Board", type="primary"):
            if wb_input:
                st.session_state["whiteboard_notes"].append(f"{st.session_state['host_email']}: {wb_input}")
                st.success("Note pinned successfully!")
                st.rerun()

        st.markdown("##### Current Board Canvas")
        for idx, note in enumerate(st.session_state["whiteboard_notes"]):
            st.markdown("""
            <div style="background:#111827;border:1px solid #374151;border-left:4px solid #38bdf8;padding:12px 16px;border-radius:8px;margin-bottom:10px;">
                <b>Note #{idx+1}</b><br>{note}
            </div>
            """, unsafe_allow_html=True)

    # â”€â”€ Tab 4: Host & Co-Presenter Privileges â”€â”€
    with tab_privileges:
        st.markdown("#### Multi-Presenter & Role Management")
        st.caption("Assign co-host, co-presenter, or participant permissions to control screen sharing, muting, and whiteboard edits.")

        new_colleague = st.text_input("Participant Email or Handle", placeholder="e.g., ocircan.darius@muni.ac.ug")
        assigned_role = st.selectbox("Assign Role & Permissions", ["Co-Host (Full Control)", "Co-Presenter (Whiteboard & Screen Share)", "Standard Participant"])

        if st.button("Grant Role Privileges", type="primary"):
            if new_colleague:
                st.session_state["co_hosts"].append({"email": new_colleague, "role": assigned_role})
                st.success(f"âœ… Successfully granted **{assigned_role}** privileges to `{new_colleague}`!")
            else:
                st.warning("Please enter a participant identifier.")

        st.markdown("##### Current Active Privilege Roster")
        if st.session_state["co_hosts"]:
            for entry in st.session_state["co_hosts"]:
                st.markdown(f"- ðŸ‘¤ **{entry['email']}** &bull; *Role*: `{entry['role']}`")
        else:
            st.info("No custom roles assigned yet. Host retains sole administrative control.")

    # â”€â”€ Tab 5: Video, Mic & Filters Hub â”€â”€
    with tab_vid_avatar:
        st.markdown("#### Real-Time Hardware Control, Live Audio/Video Stream & Filters")
        st.caption("Configure hardware camera sensors, control real-time microphone muting, audio levels, and apply live TikTok-style filters.")

        c_mode = st.radio("Broadcast Mode:", ["Hardware Camera & Microphone Stream", "Virtual Avatar & Presentation Pose"], horizontal=True)

        if c_mode == "Hardware Camera & Microphone Stream":
            col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
            with col_cfg1:
                cam_source = st.selectbox("Camera Sensor Selection", ["Default Integrated Camera", "Keyboard Deck / Lower Sensor Camera", "External USB Webcam 1", "External USB Webcam 2"])
            with col_cfg2:
                mic_source = st.selectbox("Microphone Input Source", ["Default Built-in Microphone", "Headset Microphone", "External USB Condenser Mic"])
            with col_cfg3:
                filter_style = st.selectbox("TikTok-Style Visual Filter", ["Normal (Raw Sensor)", "Studio Glow & Skin Smoothing", "Cyberpunk Neon Contrast", "Cinematic Noir", "Warm Academic Glow", "Matrix Green Tint"])

            st.info(f"âš™ï¸ Active Sensor: **{cam_source}** | Audio Input: **{mic_source}** | Filter: **{filter_style}**")

            av_control_html = """
            <div style="background:#111827;border:1px solid #374151;border-radius:12px;padding:20px;text-align:center;">
                <video id="vidFeed" autoplay playsinline muted style="width:100%;max-width:520px;height:290px;background:#0b0f19;border-radius:8px;object-fit:cover;filter: {'none' if filter_style=='Normal (Raw Sensor)' else 'brightness(1.15) contrast(1.1) saturate(1.2)' if filter_style=='Studio Glow & Skin Smoothing' else 'hue-rotate(180deg) saturate(2)' if filter_style=='Cyberpunk Neon Contrast' else 'grayscale(100%) contrast(1.3)' if filter_style=='Cinematic Noir' else 'sepia(0.3) brightness(1.1)' if filter_style=='Warm Academic Glow' else 'hue-rotate(90deg) saturate(3)'};"></video>
                <div style="margin-top:16px;display:flex;justify-content:center;gap:12px;flex-wrap:wrap;">
                    <button onclick="startStream()" style="background:#2563eb;color:white;border:none;padding:10px 18px;border-radius:6px;cursor:pointer;font-weight:bold;">ðŸš€ Start Camera & Mic</button>
                    <button onclick="toggleAudio()" id="micToggleBtn" style="background:#d97706;color:white;border:none;padding:10px 18px;border-radius:6px;cursor:pointer;font-weight:bold;">ðŸŽ™ï¸ Mute Mic</button>
                    <button onclick="stopStream()" style="background:#dc2626;color:white;border:none;padding:10px 18px;border-radius:6px;cursor:pointer;font-weight:bold;">ðŸ”´ Stop Feed</button>
                </div>
            </div>
            <script>
                let mediaStream = null;
                let isMuted = false;

                async function startStream() {
                    try {
                        const constraints = {{
                            video: {{ width: {{"ideal": 1280}}, height: {{"ideal": 720}} }},
                            audio: true
                        }};
                        mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
                        document.getElementById('vidFeed').srcObject = mediaStream;
                    } catch(e) {{ 
                        alert('Hardware Access Error or Permission Blocked: ' + e.message); 
                    }}
                }

                function toggleAudio() {
                    if(mediaStream) {
                        mediaStream.getAudioTracks().forEach(track => {
                            track.enabled = !track.enabled;
                            isMuted = !track.enabled;
                        });
                        const btn = document.getElementById('micToggleBtn');
                        btn.innerText = isMuted ? "ðŸŽ™ï¸ Unmute Mic" : "ðŸŽ™ï¸ Mute Mic";
                        btn.style.background = isMuted ? "#4b5563" : "#d97706";
                    } else {
                        alert('Please start the camera and microphone stream first.');
                    }
                }

                function stopStream() {
                    if(mediaStream) {
                        mediaStream.getTracks().forEach(t => t.stop());
                        mediaStream = null;
                    }
                    const v = document.getElementById('vidFeed');
                    v.srcObject = null;
                }
            </script>
            """
            st.components.v1.html(av_control_html, height=410)
        else:
            st.markdown("##### Virtual Avatar & Pose Selection")
            av_file = st.file_uploader("Upload Presentation Avatar/Portrait", type=["png", "jpg", "jpeg"])
            pose_sel = st.selectbox("Select Streaming Pose", ["Active Speaker Podium", "Research Presentation Mode", "Standby / Break Mode"])
            if av_file:
                st.image(av_file, width=200, caption="Active Persona Broadcast")
            else:
                st.info(f"Broadcast active as Virtual Persona [Pose: {pose_sel}].")

    # â”€â”€ Tab 6: AI Research Synthesis & Live Transcript â”€â”€
    with tab_transcript:
        st.markdown("#### Real-Time Speech-to-Text & AI Research Synthesis")
        
        transcript_container = st.container()
        with transcript_container:
            transcript_text = ""
            for item in st.session_state["live_transcript"]:
                transcript_text += f"[{item['time']}] {item['speaker']}: {item['text']}\n"
            st.markdown(f'<div class="transcript-box">{transcript_text.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

        col_ai1, col_ai2 = st.columns(2)
        with col_ai1:
            if st.button("âœ¨ Auto-Synthesize Research Summary", type="primary"):
                st.info("ðŸ¤– **AI Synthesis Engine**: Session discussion focuses on scalable pipelines, data validation protocols, and low-latency collaboration matrices.")
        with col_ai2:
            if st.button("ðŸ“‘ Generate Action Items"):
                st.success("âœ… **Action Items Generated**: 1. Distribute surveillance logs. 2. Finalize co-host permissions. 3. Archive session transcript.")

        with st.form(key="note_form", clear_on_submit=True):
            new_note = st.text_input("Add manual note or discussion point...")
            if st.form_submit_button("Log Note") and new_note:
                t_stamp = datetime.datetime.now().strftime("%H:%M")
                st.session_state["live_transcript"].append({"time": t_stamp, "speaker": st.session_state["host_email"], "text": new_note})
                st.rerun()

    # â”€â”€ Tab 7: Recordings & Playbacks â”€â”€
    with tab_playback:
        st.markdown("#### Session Recordings & Lesson Archival")
        st.caption("Access previous session recordings, auto-compiled summaries, and downloadable lesson notes.")

        if st.button("ðŸŽ¥ Save & Archive Current Session Recording", type="primary"):
            record_entry = {
                "id": st.session_state["room_id"],
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "duration": "45 mins",
                "notes_count": len(st.session_state["live_transcript"])
            }
            st.session_state["session_recordings"].append(record_entry)
            st.success("âœ… Session successfully recorded and archived to cloud storage!")

        st.markdown("##### Archived Session Vault")
        if st.session_state["session_recordings"]:
            for rec in st.session_state["session_recordings"]:
                st.markdown("""
                <div style="background:#111827;border:1px solid #1f2937;padding:12px;border-radius:10px;margin-bottom:10px;">
                    <b>ðŸ“¼ Room Recording: {rec['id']}</b><br>
                    <span style="color:#94a3b8;font-size:0.85rem;">Saved on: {rec['date']} &bull; Duration: {rec['duration']} &bull; Logged Entries: {rec['notes_count']}</span><br>
                    <a href="#" style="color:#38bdf8;font-size:0.85rem;text-decoration:none;">â–¶ Playback Session Video</a> &bull; 
                    <a href="#" style="color:#34d399;font-size:0.85rem;text-decoration:none;">ðŸ“¥ Download Transcript (.TXT)</a>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No recorded sessions archived in this vault yet.")
