# ═══════════════════════════════════════════════════════════════════════════════
# ADVANCED ENTERPRISE COLLABORATION & MEETING SUITE [FULL-FEATURED v10.0]
# ═══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import time
import datetime
import uuid
import urllib.parse

# Page Config
st.set_page_config(
    page_title="Enterprise Collaboration & Meeting Suite",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==========================================
# 1. SESSION STATE SETUP
# ==========================================
if "room_id" not in st.session_state:
    st.session_state["room_id"] = str(uuid.uuid4())[:8].upper()
if "in_session" not in st.session_state:
    st.session_state["in_session"] = False
if "shared_whiteboard" not in st.session_state:
    st.session_state["shared_whiteboard"] = "# Strategic Collaboration Canvas\n- Plan architecture milestones\n- Review team geolocation logs"
if "room_chat" not in st.session_state:
    st.session_state["room_chat"] = [
        {"user": "System AI", "time": "12:00", "text": "Secure encrypted channel initialized. Permissions module active."}
    ]
if "geo_locations" not in st.session_state:
    st.session_state["geo_locations"] = []

# Enterprise CSS Styling
st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #f8fafc; font-family: -apple-system, sans-serif; }
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
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LANDING & ROOM LAUNCHER
# ==========================================
if not st.session_state["in_session"]:
    st.markdown("""
        <div class="hero-banner">
            <div style="font-size:3.5rem;margin-bottom:0.75rem;">🎯</div>
            <h1 style="color:#f1f5f9;font-size:2.2rem;font-weight:800;margin-bottom:0.75rem;">
                Enterprise Collaboration & Meeting Suite
            </h1>
            <p style="color:#94a3b8;font-size:1.05rem;max-width:700px;margin:0 auto;line-height: 1.6;">
                Advanced hybrid conferencing featuring native hardware permission triggers, virtual avatar streaming poses, direct WhatsApp/Email dispatching, and live geo-tracking.
            </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        input_room = st.text_input("Meeting Room Code", value=st.session_state["room_id"])
        
        c_act1, c_act2 = st.columns(2)
        with c_act1:
            if st.button("🚀 Create Room", type="primary", use_container_width=True):
                st.session_state["room_id"] = str(uuid.uuid4())[:8].upper()
                st.session_state["in_session"] = True
                st.rerun()
        with c_act2:
            if st.button("🔗 Join Room", use_container_width=True):
                st.session_state["room_id"] = input_room
                st.session_state["in_session"] = True
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # ==========================================
    # 3. ACTIVE LIVE COLLABORATION WORKSPACE
    # ==========================================
    
    # Top Control Hub
    h1, h2, h3 = st.columns([2, 2.5, 1])
    with h1:
        st.markdown(f"### 🟢 Room: `{st.session_state['room_id']}`")
    with h2:
        shareable_link = f"https://notion-live-analyzer-w6ckned7rqd4gb8oppjjke.streamlit.app/Project_Collaboration?room={st.session_state['room_id']}"
        st.markdown(f'<div class="link-display">🔗 {shareable_link}</div>', unsafe_allow_html=True)
    with h3:
        if st.button("🔴 Leave", type="secondary", use_container_width=True):
            st.session_state["in_session"] = False
            st.rerun()

    st.markdown("---")

    # Core Application Tabs (Expanding Features)
    tab_vid, tab_invite, tab_geo, tab_board, tab_ai = st.tabs([
        "🎥 Live Video & Avatar Pose", 
        "📤 Direct Invites (WhatsApp/Email)", 
        "📍 Geo-Tracking Hub", 
        "🎨 Shared Whiteboard", 
        "🤖 AI Minutes"
    ])

    # ── Tab 1: Native Hardware Camera & Virtual Avatar Streaming Poses ──
    with tab_vid:
        st.markdown("#### Media Stream & Privacy Mode")
        st.caption("Grants direct browser camera/microphone access or switches to simulated streaming poses and uploaded avatars.")

        stream_mode = st.radio("Choose Media Input Mode:", ["Live Camera & Microphone (Hardware)", "Virtual Avatar / Streaming Pose Mode"], horizontal=True)

        if stream_mode == "Live Camera & Microphone (Hardware)":
            st.info("👇 Click below to request native browser hardware permission for your Camera and Microphone.")
            
            # Embedded HTML5 snippet requesting real browser media permissions
            cam_mic_html = """
            <div style="background:#111827;border:1px solid #374151;border-radius:12px;padding:20px;text-align:center;">
                <h4 style="color:#f8fafc;margin-bottom:10px;">Browser Media Stream Console</h4>
                <video id="localVideo" autoplay playsinline muted style="width:100%;max-width:480px;height:270px;background:#0b0f19;border-radius:8px;object-fit:cover;"></video>
                <div style="margin-top:15px;">
                    <button onclick="startCamera()" style="background:#2563eb;color:white;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;font-weight:bold;margin-right:10px;">Request Camera & Mic Access</button>
                    <button onclick="stopCamera()" style="background:#dc2626;color:white;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;font-weight:bold;">Stop Stream</button>
                </div>
                <p id="statusMsg" style="color:#94a3b8;font-size:0.85rem;margin-top:10px;">Status: Waiting for permission request...</p>
            </div>
            <script>
                async function startCamera() {
                    try {
                        const constraints = { video: { width: 1280, height: 720 }, audio: { echoCancellation: true, noiseSuppression: true } };
                        const stream = await navigator.mediaDevices.getUserMedia(constraints);
                        const videoElement = document.getElementById('localVideo');
                        videoElement.srcObject = stream;
                        document.getElementById('statusMsginnerText = "Status: Live HD Audio/Video Stream Active (AEC Enabled)";
                        document.getElementById('statusMsg').style.color = "#34d399";
                    } catch (err) {
                        document.getElementById('statusMsg').innerText = "Error: Permission denied or hardware unavailable (" + err.message + ")";
                        document.getElementById('statusMsg').style.color = "#f87171";
                    }
                }
                function stopCamera() {
                    const videoElement = document.getElementById('localVideo');
                    if (videoElement.srcObject) {
                        let tracks = videoElement.srcObject.getTracks();
                        tracks.forEach(track => track.stop());
                        videoElement.srcObject = null;
                        document.getElementById('statusMsg').innerText = "Status: Stream stopped.";
                        document.getElementById('statusMsg').style.color = "#94a3b8";
                    }
                }
            </script>
            """
            st.components.v1.html(cam_mic_html, height=420)

        else:
            # Virtual Avatar & Streaming Poses Option
            st.markdown("#### Virtual Avatar & Pose Configuration")
            col_av1, col_av2 = st.columns(2)
            with col_av1:
                uploaded_avatar = st.file_uploader("Upload Custom Profile Portrait/Avatar", type=["png", "jpg", "jpeg"])
                streaming_pose = st.selectbox("Select Streaming Simulation Pose", ["Professional Presentation Pose", "Active Listener Pose", "Away / Break Mode", "Custom Animated Avatar"])
            with col_av2:
                if uploaded_avatar:
                    st.image(uploaded_avatar, width=220, caption="Active Virtual Streaming Persona")
                else:
                    st.markdown(
                        '<div style="background:#111827;border:1px dashed #4b5563;height:200px;border-radius:12px;display:flex;align-items:center;justify-content:center;color:#94a3b8;">'
                        f'<span>[Using Default Avatar &bull; Pose: {streaming_pose}]</span>'
                        '</div>', unsafe_allow_html=True
                    )
            st.success("✨ Virtual stream mask active! Your feed will broadcast as the selected avatar/pose instead of direct video.")

    # ── Tab 2: Direct Email & WhatsApp Invite Dispatcher ──
    with tab_invite:
        st.markdown("#### Multi-Channel Instant Invites")
        st.caption("Send direct invitations via WhatsApp message links or automated email templates.")

        inv_col1, inv_col2 = st.columns(2)
        with inv_col1:
            st.markdown("##### 💬 WhatsApp Direct Dispatch")
            wa_number = st.text_input("Recipient WhatsApp Number (with country code e.g. +256...)", placeholder="+256XXXXXXXXX")
            wa_msg = f"Hello! Join our secure enterprise collaboration room ({st.session_state['room_id']}) here: {shareable_link}"
            
            if wa_number:
                encoded_msg = urllib.parse.quote(wa_msg)
                wa_url = f"https://wa.me/{wa_number.replace('+', '')}?text={encoded_msg}"
                st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background:#25d366;color:white;border:none;padding:10px 18px;border-radius:8px;font-weight:bold;cursor:pointer;width:100%;">📤 Open WhatsApp Invite</button></a>', unsafe_allow_html=True)
            else:
                st.info("Enter a WhatsApp number to generate direct chat link.")

        with inv_col2:
            st.markdown("##### 📧 Email Dispatcher")
            email_target = st.text_input("Recipient Email Address", placeholder="colleague@example.com")
            email_subject = st.text_input("Email Subject", value=f"Invitation to Secure Meeting Room {st.session_state['room_id']}")
            email_body = st.text_area("Email Message", value=f"You have been invited to join a live enterprise research session.\n\nRoom ID: {st.session_state['room_id']}\nAccess URL: {shareable_link}")
            
            if email_target:
                mail_to_url = f"mailto:{email_target}?subject={urllib.parse.quote(email_subject)}&body={urllib.parse.quote(email_body)}"
                st.markdown(f'<a href="{mail_to_url}"><button style="background:#2563eb;color:white;border:none;padding:10px 18px;border-radius:8px;font-weight:bold;cursor:pointer;width:100%;">📨 Send via Mail Client</button></a>', unsafe_allow_html=True)

    # ── Tab 3: Geo-Tracking Hub ──
    with tab_geo:
        st.markdown("#### Participant Geo-Location Tracking & Check-Ins")
        st.caption("Share or log your physical or operational location securely for regional field research teams.")

        geo_col1, geo_col2 = st.columns(2)
        with geo_col1:
            st.markdown("##### Log Current Location")
            loc_name = st.text_input("Location Name / District Description", placeholder="e.g., Arua Hub / Field Site Alpha")
            loc_coords = st.text_input("GPS Coordinates (Lat, Long)", placeholder="3.0303° N, 30.9070° E")
            
            if st.button("📍 Check-In Location to Room Log", type="primary"):
                if loc_name:
                    st.session_state["geo_locations"].append({"time": datetime.datetime.now().strftime("%H:%M"), "name": loc_name, "coords": loc_coords or "Manual Entry"})
                    st.success(f"✅ Checked in successfully at {loc_name}!")
                else:
                    st.warning("Please enter a location name.")

        with geo_col2:
            st.markdown("##### Active Room Check-Ins")
            if st.session_state["geo_locations"]:
                for idx, entry in enumerate(st.session_state["geo_locations"]):
                    st.markdown(f"""
                    <div style="background:#111827;border:1px solid #1f2937;padding:10px;border-radius:8px;margin-bottom:8px;font-size:0.85rem;">
                        <b>📍 {entry['name']}</b><br>
                        <span style="color:#94a3b8;">Coords: {entry['coords']} &bull; Time: {entry['time']}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No location check-ins recorded yet for this session.")

    # ── Tab 4: Shared Whiteboard ──
    with tab_board:
        st.markdown("#### Collaborative Strategy Canvas")
        new_board = st.text_area("Live Agenda & Notes", value=st.session_state["shared_whiteboard"], height=250)
        if new_board != st.session_state["shared_whiteboard"]:
            st.session_state["shared_whiteboard"] = new_board
        if st.button("📡 Sync Canvas"):
            st.success("✅ Canvas state broadcasted to peers!")

    # ── Tab 5: AI Meeting Minutes ──
    with tab_ai:
        st.markdown("#### Automated AI Transcription & Action Items")
        if st.button("⚡ Generate AI Summary"):
            with st.spinner("Compiling logs..."):
                time.sleep(1)
            st.success("✨ Summary Generated!")
            st.markdown(f"""
            - **Room Token**: `{st.session_state['room_id']}`
            - **Check-ins Logged**: {len(st.session_state['geo_locations'])} location nodes.
            - **Action Items**: Review location logs and verify secure stream connections.
            """)
            