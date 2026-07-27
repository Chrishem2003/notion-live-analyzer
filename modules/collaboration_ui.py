"""Collaboration UI — Streamlit Interface for Research Command Center."""
import time
import json
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd

from modules.collaboration import (
    RoomType, MemberRole, MessageType,
    get_room_manager, get_chat_system, get_task_manager,
    get_research_assistant, get_automation_engine,
    get_translation_service, get_file_manager,
)

# ═══════════════════════════════════════════════════════════════════════
# CSS STYLES FOR COLLABORATION
# ═══════════════════════════════════════════════════════════════════════

COLLAB_CSS = """
<style>
/* Video Grid Layout */
.video-grid {
    display: grid;
    gap: 10px;
    padding: 10px;
}
.video-tile {
    background: #1a1a2e;
    border-radius: 12px;
    aspect-ratio: 16/9;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    border: 2px solid transparent;
    transition: all 0.3s;
}
.video-tile.active {
    border-color: #3b82f6;
    box-shadow: 0 0 20px rgba(59,130,246,0.3);
}
.video-tile.speaking {
    border-color: #22c55e;
    animation: speaking-pulse 1s infinite;
}
@keyframes speaking-pulse {
    0%, 100% { box-shadow: 0 0 10px rgba(34,197,94,0.3); }
    50% { box-shadow: 0 0 25px rgba(34,197,94,0.5); }
}

/* Chat Panel */
.chat-panel {
    background: #0f172a;
    border-radius: 12px;
    height: 500px;
    display: flex;
    flex-direction: column;
}
.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 15px;
}
.chat-input-area {
    padding: 15px;
    border-top: 1px solid #1e293b;
}
.message {
    margin-bottom: 15px;
    animation: fadeIn 0.3s;
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.message-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 12px;
    font-weight: bold;
    margin-right: 10px;
}
.message-author {
    font-weight: 600;
    color: #f1f5f9;
    font-size: 13px;
}
.message-time {
    font-size: 11px;
    color: #64748b;
    margin-left: 10px;
}
.message-content {
    background: #1e293b;
    padding: 10px 14px;
    border-radius: 12px;
    margin-top: 5px;
    color: #e2e8f0;
    font-size: 14px;
}
.message-own {
    text-align: right;
}
.message-own .message-content {
    background: linear-gradient(135deg, #3b82f6, #2563eb);
}

/* Participant List */
.participant-list {
    max-height: 400px;
    overflow-y: auto;
}
.participant-item {
    display: flex;
    align-items: center;
    padding: 10px;
    border-radius: 8px;
    transition: background 0.2s;
}
.participant-item:hover {
    background: rgba(59,130,246,0.1);
}
.participant-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    margin-right: 12px;
}
.participant-info {
    flex: 1;
}
.participant-name {
    font-weight: 600;
    color: #f1f5f9;
    font-size: 14px;
}
.participant-role {
    font-size: 12px;
    color: #64748b;
}
.status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-left: auto;
}
.status-online { background: #22c55e; }
.status-away { background: #f59e0b; }
.status-busy { background: #ef4444; }
.status-offline { background: #64748b; }

/* Task Cards */
.task-card {
    background: #1e293b;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 10px;
    border-left: 4px solid;
    transition: transform 0.2s;
}
.task-card:hover {
    transform: translateX(5px);
}
.task-priority-urgent { border-color: #ef4444; }
.task-priority-high { border-color: #f59e0b; }
.task-priority-medium { border-color: #3b82f6; }
.task-priority-low { border-color: #64748b; }

/* Control Bar */
.control-bar {
    display: flex;
    gap: 10px;
    padding: 15px;
    background: #1e293b;
    border-radius: 12px;
    margin: 10px 0;
}
.control-btn {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    cursor: pointer;
    transition: all 0.2s;
}
.control-btn:hover {
    transform: scale(1.1);
}
.control-btn.active {
    background: #3b82f6;
    color: white;
}
.control-btn.muted {
    background: #ef4444;
    color: white;
}
.control-btn.end-call {
    background: #ef4444;
    width: 80px;
    border-radius: 25px;
    color: white;
}

/* Room Cards */
.room-card {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 15px;
    border: 1px solid #334155;
    transition: all 0.3s;
    cursor: pointer;
}
.room-card:hover {
    border-color: #3b82f6;
    transform: translateY(-3px);
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}
.room-type-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 10px;
}
.room-type-video { background: rgba(59,130,246,0.2); color: #3b82f6; }
.room-type-chat { background: rgba(34,197,94,0.2); color: #22c55e; }
.room-type-whiteboard { background: rgba(168,85,247,0.2); color: #a855f7; }
.room-type-panel { background: rgba(245,158,11,0.2); color: #f59e0b; }
.room-type-webinar { background: rgba(236,72,153,0.2); color: #ec4899; }

/* Whiteboard */
.whiteboard-container {
    background: white;
    border-radius: 12px;
    min-height: 600px;
    position: relative;
}

/* AI Assistant */
.ai-chat {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border-radius: 16px;
    padding: 20px;
    border: 1px solid #334155;
}
.ai-response {
    background: #0f172a;
    border-radius: 12px;
    padding: 15px;
    margin-top: 15px;
    border-left: 4px solid #8b5cf6;
}
.sources-list {
    font-size: 12px;
    color: #94a3b8;
    margin-top: 10px;
}

/* Reaction Picker */
.reaction-picker {
    display: flex;
    gap: 5px;
    margin-top: 5px;
}
.reaction-btn {
    background: transparent;
    border: none;
    font-size: 16px;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    transition: background 0.2s;
}
.reaction-btn:hover {
    background: rgba(255,255,255,0.1);
}
</style>
"""

def render_collaboration_css():
    """Apply collaboration CSS."""
    st.markdown(COLLAB_CSS, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# MAIN RENDER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def render_command_center():
    """Render the main Research Command Center."""
    
    # Initialize state
    init_collaboration_state()
    render_collaboration_css()
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1e293b, #0f172a);
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid #334155;
    ">
        <h1 style="margin:0; color: white;">🎯 Research Command Center</h1>
        <p style="color: #94a3b8; margin-top: 0.5rem;">
            Unified collaboration hub — Video, Chat, Tasks, & AI Assistant
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏠 Lobby",
        "📹 Video Rooms",
        "💬 Chat",
        "✅ Tasks",
        "🤖 AI Assistant",
        "⚡ Automations",
    ])
    
    with tab1:
        render_lobby()
    
    with tab2:
        render_video_rooms()
    
    with tab3:
        render_chat_system()
    
    with tab4:
        render_tasks()
    
    with tab5:
        render_ai_assistant()
    
    with tab6:
        render_automations()

# ═══════════════════════════════════════════════════════════════════════
# LOBBY - Room Selection
# ═══════════════════════════════════════════════════════════════════════

def render_lobby():
    """Render the room lobby."""
    st.subheader("🚀 Join or Create a Room")
    
    # User profile setup
    with st.expander("👤 Your Profile", expanded=not st.session_state.get("collab_user_name")):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state["collab_user_name"] = st.text_input(
                "Your Name",
                value=st.session_state.get("collab_user_name", ""),
                placeholder="Enter your name"
            )
        with col2:
            st.session_state["collab_user_email"] = st.text_input(
                "Email",
                value=st.session_state.get("collab_user_email", ""),
                placeholder="your@email.com"
            )
    
    st.divider()
    
    # Create new room
    col1, col2 = st.columns([2, 1])
    with col1:
        room_name = st.text_input("Create New Room", placeholder="Room name...")
    with col2:
        room_type = st.selectbox("Type", 
            ["Video Call", "Chat Room", "Whiteboard", "Research Panel", "Webinar"])
    
    if st.button("🚀 Create Room", type="primary") and room_name:
        _room_types = {
            "Video Call": RoomType.VIDEO_CALL,
            "Chat Room": RoomType.CHAT_ROOM,
            "Whiteboard": RoomType.WHITEBOARD,
            "Research Panel": RoomType.RESEARCH_PANEL,
            "Webinar": RoomType.WEBINAR,
        }
        manager = get_room_manager()
        room = manager.create_room(
            name=room_name,
            room_type=_room_types[room_type],
            host_id=st.session_state.get("collab_user_id", "user1"),
        )
        st.session_state["active_room"] = room.id
        st.rerun()
    
    st.divider()
    
    # Browse rooms
    st.subheader("📋 Available Rooms")
    
    manager = get_room_manager()
    rooms = manager.list_rooms()
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_type = st.selectbox("Filter by Type", 
            ["All", "Video Call", "Chat Room", "Whiteboard", "Research Panel", "Webinar"])
    with col2:
        filter_status = st.selectbox("Filter by Status", ["All", "Active", "Locked"])
    with col3:
        search = st.text_input("Search", placeholder="Search rooms...")
    
    # Filter rooms
    if filter_type != "All":
        type_map = {
            "Video Call": RoomType.VIDEO_CALL,
            "Chat Room": RoomType.CHAT_ROOM,
            "Whiteboard": RoomType.WHITEBOARD,
            "Research Panel": RoomType.RESEARCH_PANEL,
            "Webinar": RoomType.WEBINAR,
        }
        rooms = [r for r in rooms if r.room_type == type_map[filter_type]]
    
    if search:
        rooms = [r for r in rooms if search.lower() in r.name.lower()]
    
    # Render room cards
    for room in rooms:
        type_badges = {
            RoomType.VIDEO_CALL: ("📹 Video Call", "room-type-video"),
            RoomType.CHAT_ROOM: ("💬 Chat Room", "room-type-chat"),
            RoomType.WHITEBOARD: ("🎨 Whiteboard", "room-type-whiteboard"),
            RoomType.RESEARCH_PANEL: ("📊 Research Panel", "room-type-panel"),
            RoomType.WEBINAR: ("🎓 Webinar", "room-type-webinar"),
        }
        badge_text, badge_class = type_badges.get(room.room_type, ("📌", ""))
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"""
            <div class="room-card">
                <span class="room-type-badge {badge_class}">{badge_text}</span>
                <h3 style="margin: 10px 0; color: white;">{room.name}</h3>
                <p style="color: #94a3b8; font-size: 14px;">{room.description or 'No description'}</p>
                <div style="display: flex; gap: 15px; margin-top: 10px;">
                    <span style="color: #64748b; font-size: 13px;">👥 {len(room.members)} / {room.max_participants}</span>
                    <span style="color: #64748b; font-size: 13px;">🕐 {room.created_at.strftime('%H:%M')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Join", key=f"join_{room.id}"):
                st.session_state["active_room"] = room.id
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# VIDEO ROOMS
# ═══════════════════════════════════════════════════════════════════════

def render_video_rooms():
    """Render video conferencing interface."""
    
    active_room_id = st.session_state.get("active_room")
    
    if not active_room_id:
        st.info("Join a room from the Lobby to start video conferencing")
        return
    
    manager = get_room_manager()
    room = manager.get_room(active_room_id)
    
    if not room:
        st.error("Room not found")
        return
    
    # Header
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.subheader(f"📹 {room.name}")
    with col2:
        if st.button("🔒 Lock Room"):
            room.is_locked = not room.is_locked
            st.rerun()
    with col3:
        if st.button("🚪 Leave"):
            st.session_state["active_room"] = None
            st.rerun()
    
    st.markdown(f"*{room.description or ''}*")
    
    # Video Grid
    st.subheader("👥 Participants")
    
    # Demo participants
    demo_participants = [
        {"name": "Dr. Sarah Chen", "role": "Host", "status": "online", "speaking": True},
        {"name": "Prof. James Wilson", "role": "Speaker", "status": "online", "speaking": False},
        {"name": "Alex Kim", "role": "Attendee", "status": "online", "speaking": False},
        {"name": "Maria Garcia", "role": "Attendee", "status": "away", "speaking": False},
    ]
    
    # Show video grid
    cols = st.columns(4)
    for i, participant in enumerate(demo_participants):
        with cols[i % 4]:
            speaking_class = "speaking" if participant.get("speaking") else ""
            st.markdown(f"""
            <div class="video-tile {speaking_class}">
                <div style="text-align: center;">
                    <div style="font-size: 40px; margin-bottom: 10px;">👤</div>
                    <div style="color: white; font-weight: 600;">{participant['name']}</div>
                    <div style="color: #94a3b8; font-size: 12px;">{participant['role']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Self view
    with st.expander("📷 Your Camera"):
        st.markdown("""
        <div class="video-tile active">
            <div style="text-align: center;">
                <div style="font-size: 40px; margin-bottom: 10px;">👤</div>
                <div style="color: white;">You</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Media controls
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            mic_on = st.button("🎤" if st.session_state.get("audio_enabled") else "🔇")
            st.session_state["audio_enabled"] = not st.session_state.get("audio_enabled", True)
        with col2:
            cam_on = st.button("📹" if st.session_state.get("video_enabled") else "📷")
            st.session_state["video_enabled"] = not st.session_state.get("video_enabled", False)
        with col3:
            st.button("🖥️ Share Screen")
        with col4:
            st.button("💻 Virtual Background")
        with col5:
            st.button("⏺️ Record")
    
    # Side panel options
    col_main, col_side = st.columns([3, 1])
    
    with col_main:
        # Screen share area
        st.subheader("🖥️ Screen Share")
        st.markdown("""
        <div style="
            background: #0f172a;
            border-radius: 12px;
            padding: 60px;
            text-align: center;
            border: 2px dashed #334155;
        ">
            <div style="font-size: 50px; margin-bottom: 15px;">🖥️</div>
            <p style="color: #94a3b8;">Click "Share Screen" to present</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_side:
        # Participants panel
        st.subheader("Participants")
        
        for p in demo_participants:
            status_class = f"status-{p['status']}"
            st.markdown(f"""
            <div class="participant-item">
                <div class="participant-avatar">👤</div>
                <div class="participant-info">
                    <div class="participant-name">{p['name']}</div>
                    <div class="participant-role">{p['role']}</div>
                </div>
                <span class="status-dot {status_class}"></span>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# CHAT SYSTEM
# ═══════════════════════════════════════════════════════════════════════

def render_chat_system():
    """Render chat/messaging interface."""
    
    # Room selection
    manager = get_room_manager()
    rooms = manager.list_rooms()
    
    room_options = {r.id: r.name for r in rooms}
    selected_room = st.selectbox("Select Room", list(room_options.keys()), 
                                  format_func=lambda x: room_options[x])
    
    if not selected_room:
        st.info("Select a room to start chatting")
        return
    
    chat = get_chat_system()
    
    # Send message
    col1, col2 = st.columns([5, 1])
    with col1:
        message = st.text_input("Type a message...", key="chat_input")
    with col2:
        send = st.button("Send ➤")
    
    if send and message:
        user_name = st.session_state.get("collab_user_name") or "You"
        user_id = st.session_state.get("collab_user_id") or "user1"
        
        # Check for commands
        if message.startswith("/poll "):
            poll_q = message[6:]
            chat.create_poll(selected_room, poll_q, ["Yes", "No", "Maybe"], user_id, user_name)
        else:
            chat.send_message(selected_room, user_id, user_name, message)
        
        st.rerun()
    
    st.divider()
    
    # Messages
    st.subheader("💬 Messages")
    
    messages = chat.get_messages(selected_room)
    
    for msg in messages:
        is_own = msg.sender_id == st.session_state.get("collab_user_id")
        own_class = "message-own" if is_own else ""
        
        initial = msg.sender_name[0].upper() if msg.sender_name else "?"
        
        st.markdown(f"""
        <div class="message {own_class}">
            <div style="display: flex; align-items: center;">
                <div class="message-avatar">{initial}</div>
                <div class="message-author">{msg.sender_name}</div>
                <div class="message-time">{msg.timestamp.strftime('%H:%M')}</div>
            </div>
            <div class="message-content">{msg.content}</div>
            <div class="reaction-picker">
                <button class="reaction-btn">👍</button>
                <button class="reaction-btn">❤️</button>
                <button class="reaction-btn">🎉</button>
                <button class="reaction-btn">🤔</button>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# TASK MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

def render_tasks():
    """Render task management interface."""
    
    manager = get_room_manager()
    rooms = manager.list_rooms()
    
    room_options = {r.id: r.name for r in rooms}
    selected_room = st.selectbox("Select Room", list(room_options.keys()),
                                  format_func=lambda x: room_options[x],
                                  key="task_room")
    
    task_mgr = get_task_manager()
    
    # Create task
    with st.expander("➕ Add New Task", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Task Title")
            assignee = st.text_input("Assignee")
        with col2:
            priority = st.selectbox("Priority", ["low", "medium", "high", "urgent"])
            due = st.date_input("Due Date")
        
        if st.button("Create Task", type="primary") and title:
            task_mgr.create_task(
                room_id=selected_room,
                title=title,
                assignee_id=st.session_state.get("collab_user_id", ""),
                assignee_name=assignee,
                priority=priority,
                due_date=datetime.combine(due, datetime.min.time()),
            )
            st.rerun()
    
    st.divider()
    
    # Task stats
    stats = task_mgr.get_task_stats(selected_room)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("To Do", stats.get("todo", 0))
    col2.metric("In Progress", stats.get("in_progress", 0))
    col3.metric("Review", stats.get("review", 0))
    col4.metric("Done", stats.get("done", 0))
    
    st.divider()
    
    # Task list
    tasks = task_mgr.get_room_tasks(selected_room)
    
    # Filter tabs
    tab1, tab2, tab3, tab4 = st.tabs(["All", "To Do", "In Progress", "Done"])
    
    with tab1:
        render_task_list(tasks, task_mgr)
    with tab2:
        render_task_list([t for t in tasks if t.status == "todo"], task_mgr)
    with tab3:
        render_task_list([t for t in tasks if t.status == "in_progress"], task_mgr)
    with tab4:
        render_task_list([t for t in tasks if t.status == "done"], task_mgr)

def render_task_list(tasks, task_mgr):
    """Render a list of tasks."""
    for task in tasks:
        priority_class = f"task-priority-{task.priority}"
        status_emoji = {"todo": "⭕", "in_progress": "🔄", "review": "👀", "done": "✅"}
        
        st.markdown(f"""
        <div class="task-card {priority_class}">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <h4 style="margin: 0; color: white;">{status_emoji.get(task.status, '⬜')} {task.title}</h4>
                    <p style="color: #94a3b8; font-size: 13px; margin: 5px 0;">
                        {task.description or 'No description'}
                    </p>
                    <span style="color: #64748b; font-size: 12px;">
                        👤 {task.assignee_name or 'Unassigned'} | 
                        📅 {task.due_date.strftime('%Y-%m-%d') if task.due_date else 'No due date'}
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if task.status != "todo" and st.button(f"← Todo", key=f"todo_{task.id}"):
                task_mgr.update_task_status(task.id, "todo")
                st.rerun()
        with col2:
            if task.status != "done" and st.button(f"Done ✓", key=f"done_{task.id}"):
                task_mgr.update_task_status(task.id, "done")
                st.rerun()
        with col3:
            if st.button(f"🗑️", key=f"del_{task.id}"):
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# AI RESEARCH ASSISTANT
# ═══════════════════════════════════════════════════════════════════════

def render_ai_assistant():
    """Render AI research assistant."""
    
    st.subheader("🧠 AI Research Assistant")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_area("Ask a research question...", height=100,
                            placeholder="What are the latest advances in CRISPR gene editing?")
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        use_web = st.checkbox("Web Search", value=True)
        use_lit = st.checkbox("Literature", value=True)
    
    if st.button("🔍 Research", type="primary") and query:
        assistant = get_research_assistant()
        
        with st.spinner("Analyzing research..."):
            response = assistant.ask(
                question=query,
                room_id="general",
                use_websearch=use_web,
                use_literature=use_lit,
            )
            
            # Display response
            st.markdown(f"""
            <div class="ai-chat">
                <h4 style="color: white; margin: 0;">💡 Research Insight</h4>
                <p style="color: #94a3b8;">{query}</p>
                <div class="ai-response">
                    <p style="color: #e2e8f0;">{response['answer']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Sources
            if response.get("sources"):
                st.markdown("**📚 Sources:**")
                for source in response["sources"]:
                    st.markdown(f"- [{source['title']}]({source['url']}) ({source['relevance']*100:.0f}%)")
            
            # Follow-up questions
            if response.get("follow_up"):
                st.markdown("**💭 Follow-up questions:**")
                for q in response["follow_up"]:
                    if st.button(f"❓ {q}"):
                        st.rerun()
    
    st.divider()
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Summarize Papers"):
            st.info("Upload papers to summarize...")
    
    with col2:
        if st.button("👥 Find Experts"):
            assistant = get_research_assistant()
            experts = assistant.suggest_experts("machine learning", 5)
            st.write("**Suggested Experts:**")
            for exp in experts:
                st.markdown(f"- **{exp['name']}** ({exp['affiliation']}) - h-index: {exp['h_index']}")
    
    with col3:
        if st.button("📋 Generate Brief"):
            assistant = get_research_assistant()
            brief = assistant.generate_research_brief("AI in healthcare")
            st.json(brief)

# ═══════════════════════════════════════════════════════════════════════
# AUTOMATIONS
# ═══════════════════════════════════════════════════════════════════════

def render_automations():
    """Render automation workflows."""
    
    st.subheader("⚡ Workflow Automations")
    
    engine = get_automation_engine()
    automations = engine.list_automations()
    
    # Create new automation
    with st.expander("➕ Create Automation", expanded=False):
        name = st.text_input("Automation Name")
        trigger = st.selectbox("Trigger", [
            "member_joined",
            "member_left", 
            "message_received",
            "task_assigned",
            "schedule_near",
            "new_paper_relevant",
        ])
        action = st.selectbox("Action", [
            "send_welcome_message",
            "send_reminder",
            "notify_assignee",
            "share_to_room",
            "generate_summary",
        ])
        
        if st.button("Create", type="primary") and name:
            engine.create_automation(name, trigger, action)
            st.rerun()
    
    st.divider()
    
    # List automations
    for auto in automations:
        status = "🟢 Active" if auto.enabled else "🔴 Disabled"
        
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.markdown(f"**{auto.name}**")
            st.caption(f"Trigger: `{auto.trigger}` → Action: `{auto.action}`")
        
        with col2:
            st.markdown(status)
        
        with col3:
            toggle = st.checkbox("Enable", value=auto.enabled, key=f"auto_{auto.id}")
            if toggle != auto.enabled:
                engine.toggle_automation(auto.id, toggle)
                st.rerun()
    
    st.divider()
    
    # Automation templates
    st.subheader("📋 Templates")
    
    template_cols = st.columns(3)
    
    templates = [
        ("🔔 Meeting Reminders", "Send reminders 15 min before meetings"),
        ("👋 Welcome New Members", "Auto-greet new room participants"),
        ("📊 Weekly Summary", "Generate weekly activity reports"),
        ("🎯 Task Follow-up", "Remind about overdue tasks"),
        ("📰 Paper Alerts", "Notify relevant new publications"),
        ("💬 Message Auto-reply", "Respond to common questions"),
    ]
    
    for i, (title, desc) in enumerate(templates):
        with template_cols[i % 3]:
            if st.button(f"**{title}**", key=f"template_{i}"):
                st.info(f"Adding: {title}")

# ═══════════════════════════════════════════════════════════════════════
# TRANSLATION & FILE SHARING
# ═══════════════════════════════════════════════════════════════════════

def render_translation_sidebar():
    """Render translation options in sidebar."""
    st.subheader("🌐 Translation")
    
    trans = get_translation_service()
    
    target_lang = st.selectbox("Translate to", 
                                list(trans.SUPPORTED_LANGUAGES.keys()),
                                format_func=lambda x: trans.SUPPORTED_LANGUAGES[x])
    
    if st.button("Auto-translate"):
        st.info("Translation enabled")

def render_file_sharing_sidebar():
    """Render file sharing in sidebar."""
    st.subheader("📁 Shared Files")
    
    uploaded = st.file_uploader("Upload File", type=None)
    
    if uploaded:
        st.success(f"Uploaded: {uploaded.name}")
    
    # Demo files
    st.markdown("**Recent Files:**")
    demo_files = [
        ("📄 research_notes.pdf", "2.4 MB"),
        ("📊 data_analysis.xlsx", "1.1 MB"),
        ("🖼️ diagram.png", "450 KB"),
    ]
    
    for name, size in demo_files:
        st.markdown(f"{name} - {size}")

# ═══════════════════════════════════════════════════════════════════════
# INIT FUNCTION
# ═══════════════════════════════════════════════════════════════════════

def init_collaboration_ui():
    """Initialize collaboration UI."""
    init_collaboration_state()
    render_collaboration_css()