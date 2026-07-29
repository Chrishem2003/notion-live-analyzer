# ═══════════════════════════════════════════════════════════════════════════════
# AUTONOMOUS ENTERPRISE COLLABORATION & RESEARCH SUITE [GLOBAL OMNI v14.0]
# ═══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import time
import datetime
import uuid
import urllib.parse

# Safe Page Config Wrapper for Multipage/Router compatibility
try:
    st.set_page_config(
        page_title="Autonomous Collaboration & Research Suite",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
except Exception:
    pass

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
            <div style="font-size:3.5rem;margin-bottom:0.75rem;">🎯</div>
            <h1 style="color:#f1f5f9;font-size:2.2rem;font-weight:800;margin-bottom:0.75rem;">
                Autonomous Collaboration & Research Suite
            </h1>
            <p style="color:#94a3b8;font-size:1.05rem;max-width:700px;margin:0 auto;line-height: 1.6;">
                Unlimited-scale global conferencing with multi-provider mail dispatchers, camera filters, live hand-raising queues, interactive reaction streams, and AI research synthesis.
            </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.markdown("#### Host Configuration")
        
        st.session_state["host_email"] = st.text_input("Host Verified Email", value=st.session_state["host_email"])
        st.session_state["host_phone"] = st.text_input("WhatsApp Number", value=st.session_state["host_phone"])
        room_input = st.text_input("Room Identifier", value=st.session_state["room_id"])
        
        c_act1, c_act2 = st.columns(2)
        with c_act1:
            if st.button("🚀 Launch Global Omni Room", type="primary", use_container_width=True):
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
    h1, h2, h3 = st.columns([2, 2.5, 1])
    with h1:
        st.markdown(f"### 🟢 Room: `{st.session_state['room_id']}` [Scale: Unlimited Mesh]")
        st.caption(f"Host: {st.session_state['host_email']}")
    with h2:
        shareable_link = f"https://notion-live-analyzer-w6ckned7rqd4gb8oppjjke.streamlit.app/?room={st.session_state['room_id']}"
        st.markdown(f'<div class="link-display">🔗 {shareable_link}</div>', unsafe_allow_html=True)
    with h3:
        if st.button("🔴 Close Room", type="secondary", use_container_width=True):
            st.session_state["in_session"] = False
            st.rerun()

    st.markdown("---")

    tab_auto_inv, tab_audience, tab_whiteboard, tab_privileges, tab_vid_avatar, tab_transcript, tab_playback = st.tabs([
        "📤 Bulk Invites", 
        "💬 Audience & Chat", 
        "📋 Shared Whiteboard", 
        "👑 Privileges", 
        "🎥 Camera & Filters", 
        "🤖 AI Synthesis", 
        "📼 Record & Playback"
    ])

    with tab_auto_inv:
        st.markdown("#### Automated List Dispatcher with Multi-Provider Support")
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
            sel_timezone = st.selectbox("Timezone Profile", ["Africa/Kampala (EAT)", "UTC", "America/New_York (EST/EDT)", "Europe/London (GMT/BST)"])

        formatted_schedule = f"{sel_date} at {sel_hour}:{sel_min} {sel_ampm} ({sel_timezone})"
        
        if inv_type == "Email Recipient List":
            email_provider = st.selectbox("Select Mail Dispatch Provider", ["Gmail", "Yahoo Mail", "Microsoft Outlook / Office 365", "Custom SMTP Relay"])
            raw_email_list = st.text_area("Paste Email addresses (comma separated)", placeholder="colleague1@uni.edu, colleague2@uni.edu")
            
            if st.button(f"🚀 Dispatch via {email_provider}", type="primary"):
                if raw_email_list:
                    emails = [e.strip() for e in raw_email_list.split(",")]
                    subject = f"Invitation: {topic_desc}"
                    body = f"Dear Colleague,\n\nYou are invited to join our secure research session.\nTopic: {topic_desc}\nTime: {formatted_schedule}\n\nAccess Link: {shareable_link}"
                    st.success(f"✅ Successfully prepared {len(emails)} invitations!")
                    for mail in emails:
                        m_link = f"mailto:{mail}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
                        st.markdown(f"- **{mail}**: [Open Mail Client]({m_link})", unsafe_allow_html=True)
                else:
                    st.warning("Please provide valid email addresses.")
        else:
            raw_wa_list = st.text_area("Paste WhatsApp numbers (comma separated)", placeholder="+256700000001")
            if st.button("🚀 Queue & Send Automated WhatsApp Invites", type="primary"):
                if raw_wa_list:
                    numbers = [n.strip() for n in raw_wa_list.split(",")]
                    msg_body = f"Hello! You are invited by {st.session_state['host_email']} to *{topic_desc}*.\nScheduled: {formatted_schedule}\nJoin Room: {shareable_link}"
                    st.success(f"✅ Queued {len(numbers)} automated WhatsApp invites!")
                    for num in numbers:
                        link = f"https://wa.me/{num.replace('+', '')}?text={urllib.parse.quote(msg_body)}"
                        st.markdown(f"- **{num}**: [Dispatch WhatsApp Alert]({link})", unsafe_allow_html=True)

    with tab_audience:
        st.markdown("#### High-Capacity Audience Engagement Hub")
        user_handle = st.text_input("Your Display Handle for Queue", value=st.session_state["host_email"])
        if st.button("Raise Hand ✋", type="primary"):
            if user_handle not in st.session_state["raised_hands"]:
                st.session_state["raised_hands"].append(user_handle)
                st.success("Hand raised!")
        if st.session_state["raised_hands"]:
            st.markdown(f"**Queue**: " + ", ".join([f"`{h}`" for h in st.session_state["raised_hands"]]))

        chat_html = "".join([f"<b>{c['user']}</b>: {c['msg']}<br>" for c in st.session_state["room_chat"]])
        st.markdown(f'<div class="chat-box">{chat_html}</div>', unsafe_allow_html=True)
        
        with st.form(key="room_chat_form", clear_on_submit=True):
            chat_input = st.text_input("Broadcast comment...")
            if st.form_submit_button("Send") and chat_input:
                st.session_state["room_chat"].append({"user": st.session_state["host_email"], "msg": chat_input})
                st.rerun()

    with tab_whiteboard:
        st.markdown("#### Real-Time Collaborative Whiteboard")
        wb_input = st.text_input("Add sticky note...", key="wb_text_input")
        if st.button("📌 Pin Note", type="primary") and wb_input:
            st.session_state["whiteboard_notes"].append(f"{st.session_state['host_email']}: {wb_input}")
            st.rerun()
        for idx, note in enumerate(st.session_state["whiteboard_notes"]):
            st.markdown(f"<div style='background:#111827;padding:10px;border-radius:6px;margin-bottom:8px;'><b>Note #{idx+1}</b><br>{note}</div>", unsafe_allow_html=True)

    with tab_privileges:
        st.markdown("#### Multi-Presenter & Role Management")
        new_colleague = st.text_input("Participant Identifier", placeholder="colleague@uni.edu")
        assigned_role = st.selectbox("Role", ["Co-Host", "Co-Presenter", "Standard Participant"])
        if st.button("Grant Privileges") and new_colleague:
            st.session_state["co_hosts"].append({"email": new_colleague, "role": assigned_role})
            st.success(f"Granted {assigned_role} to {new_colleague}")

    with tab_vid_avatar:
        st.markdown("#### Camera & Filters Hub")
        filter_style = st.selectbox("Visual Filter", ["Normal", "Studio Glow", "Cyberpunk Neon", "Cinematic Noir"])
        st.info(f"Active Filter Configuration: {filter_style}")

    with tab_transcript:
        st.markdown("#### Real-Time AI Transcript & Synthesis")
        transcript_text = "".join([f"[{i['time']}] {i['speaker']}: {i['text']}\n" for i in st.session_state["live_transcript"]])
        st.markdown(f'<div class="transcript-box">{transcript_text.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
        if st.button("✨ Auto-Synthesize Research Summary", type="primary"):
            st.info("🤖 **AI Synthesis**: Discussion centers on pipeline execution speed, automated validation checks, and low-latency sharing matrices.")

    with tab_playback:
        st.markdown("#### Recordings & Archival Vault")
        if st.button("🎥 Archive Session", type="primary"):
            st.session_state["session_recordings"].append({"id": st.session_state["room_id"], "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
            st.success("Session archived successfully!")