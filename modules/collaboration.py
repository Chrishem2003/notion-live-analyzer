import security_guard

"""
Research Command Center  Unified Collaboration Hub.
Combines video conferencing, real-time collaboration, chat, 
task management, and AI-powered research assistant into one platform.
"""
import os
import time
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field

import streamlit as st
import pandas as pd
import requests

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CORE ENUMS & DATA STRUCTURES
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class RoomType(Enum):
    VIDEO_CALL = "video"
    CHAT_ROOM = "chat"
    WHITEBOARD = "whiteboard"
    RESEARCH_PANEL = "panel"
    WEBINAR = "webinar"

class MemberRole(Enum):
    HOST = "host"
    MODERATOR = "moderator"
    SPEAKER = "speaker"
    ATTENDEE = "attendee"
    VIEWER = "viewer"

class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    CODE = "code"
    SYSTEM = "system"
    POLL = "poll"

@dataclass
class TeamMember:
    id: str
    name: str
    email: str
    avatar: str = ""
    role: MemberRole = MemberRole.ATTENDEE
    status: str = "offline"  # online, away, busy
    joined_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ChatMessage:
    id: str
    room_id: str
    sender_id: str
    sender_name: str
    content: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reactions: Dict[str, List[str]] = field(default_factory=dict)
    reply_to: str = None

@dataclass
class ResearchRoom:
    id: str
    name: str
    room_type: RoomType
    host_id: str
    description: str = ""
    members: List[TeamMember] = field(default_factory=list)
    max_participants: int = 100
    is_recording: bool = False
    is_locked: bool = False
    password: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    settings: Dict = field(default_factory=dict)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# SESSION STATE INITIALIZATION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def init_collaboration_state():
    """Initialize collaboration module state."""
    defaults = {
        # Current user
        "collab_user_id": str(uuid.uuid4())[:8],
        "collab_user_name": "",
        "collab_user_email": "",
        
        # Rooms
        "active_room": None,
        "room_messages": {},
        "active_participants": [],
        
        # Video/Audio
        "video_enabled": False,
        "audio_enabled": True,
        "screen_sharing": False,
        "virtual_bg": None,
        
        # Chat
        "chat_panel_open": True,
        "unread_messages": 0,
        
        # Tasks
        "room_tasks": {},
        
        # Whiteboard
        "whiteboard_data": "",
        
        # Presence
        "user_status": "online",
        "last_seen": datetime.utcnow().isoformat(),
    }
    
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ROOM MANAGEMENT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class RoomManager:
    """Manages research collaboration rooms."""
    
    def __init__(self):
        self._rooms: Dict[str, ResearchRoom] = {}
        self._load_demo_rooms()
    
    def _load_demo_rooms(self):
        """Load demo rooms for showcase."""
        demo_rooms = [
            ResearchRoom(
                id="room_lab_meeting",
                name="ðŸ”¬ Lab Meeting",
                room_type=RoomType.VIDEO_CALL,
                host_id="user1",
                description="Weekly lab meeting and paper review",
                max_participants=15,
            ),
            ResearchRoom(
                id="room_data_team", 
                name=" Data Team Sync",
                room_type=RoomType.RESEARCH_PANEL,
                host_id="user2",
                description="Data analysis and visualization discussions",
                max_participants=10,
            ),
            ResearchRoom(
                id="room_genetics",
                name="ðŸ§¬ Genetics Journal Club",
                room_type=RoomType.CHAT_ROOM,
                host_id="user3",
                description="Discussion of latest genetics research papers",
                max_participants=50,
            ),
            ResearchRoom(
                id="room_whiteboard",
                name="ðŸŽ¨ Research Whiteboard",
                room_type=RoomType.WHITEBOARD,
                host_id="user1",
                description="Collaborative brainstorming and mind mapping",
                max_participants=20,
            ),
            ResearchRoom(
                id="room_webinar",
                name="ðŸŽ“ Guest Lecture Series",
                room_type=RoomType.WEBINAR,
                host_id="user1",
                description="Live webinars with guest speakers",
                max_participants=500,
            ),
        ]
        for room in demo_rooms:
            self._rooms[room.id] = room
    
    def create_room(
        self,
        name: str,
        room_type: RoomType,
        host_id: str,
        description: str = "",
        password: str = "",
    ) -> ResearchRoom:
        """Create a new collaboration room."""
        room = ResearchRoom(
            id=f"room_{uuid.uuid4().hex[:12]}",
            name=name,
            room_type=room_type,
            host_id=host_id,
            description=description,
            password=password,
        )
        self._rooms[room.id] = room
        return room
    
    def get_room(self, room_id: str) -> Optional[ResearchRoom]:
        """Get room by ID."""
        return self._rooms.get(room_id)
    
    def list_rooms(self, room_type: RoomType = None) -> List[ResearchRoom]:
        """List all rooms, optionally filtered by type."""
        rooms = list(self._rooms.values())
        if room_type:
            rooms = [r for r in rooms if r.room_type == room_type]
        return sorted(rooms, key=lambda r: r.created_at, reverse=True)
    
    def add_member(self, room_id: str, member: TeamMember) -> bool:
        """Add member to room."""
        room = self.get_room(room_id)
        if not room:
            return False
        if len(room.members) >= room.max_participants:
            return False
        if any(m.id == member.id for m in room.members):
            return True  # Already in room
        room.members.append(member)
        return True
    
    def remove_member(self, room_id: str, member_id: str) -> bool:
        """Remove member from room."""
        room = self.get_room(room_id)
        if not room:
            return False
        room.members = [m for m in room.members if m.id != member_id]
        return True

@st.cache_resource
def get_room_manager() -> RoomManager:
    """Get cached room manager."""
    return RoomManager()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CHAT & MESSAGING SYSTEM
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class ChatSystem:
    """Real-time messaging system for rooms."""
    
    def __init__(self):
        # In production, use Supabase Realtime or WebSocket
        self._messages: Dict[str, List[ChatMessage]] = {}
        self._typing_users: Dict[str, List[str]] = {}
    
    def send_message(
        self,
        room_id: str,
        sender_id: str,
        sender_name: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        reply_to: str = None,
    ) -> ChatMessage:
        """Send a message to a room."""
        msg = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            room_id=room_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            message_type=message_type,
            reply_to=reply_to,
        )
        
        if room_id not in self._messages:
            self._messages[room_id] = []
        self._messages[room_id].append(msg)
        
        return msg
    
    def get_messages(self, room_id: str, limit: int = 100) -> List[ChatMessage]:
        """Get messages for a room."""
        messages = self._messages.get(room_id, [])
        return messages[-limit:]
    
    def add_reaction(self, message_id: str, room_id: str, emoji: str, user_id: str):
        """Add reaction to message."""
        messages = self._messages.get(room_id, [])
        for msg in messages:
            if msg.id == message_id:
                if emoji not in msg.reactions:
                    msg.reactions[emoji] = []
                if user_id not in msg.reactions[emoji]:
                    msg.reactions[emoji].append(user_id)
                break
    
    def create_poll(self, room_id: str, question: str, options: List[str], 
                   sender_id: str, sender_name: str) -> ChatMessage:
        """Create a poll message."""
        poll_data = {
            "question": question,
            "options": {opt: [] for opt in options},
            "total_votes": 0,
        }
        return self.send_message(
            room_id, sender_id, sender_name,
            json.dumps(poll_data),
            message_type=MessageType.POLL,
        )
    
    def vote_poll(self, message_id: str, room_id: str, option: str, user_id: str):
        """Vote on a poll."""
        messages = self._messages.get(room_id, [])
        for msg in messages:
            if msg.id == message_id and msg.message_type == MessageType.POLL:
                try:
                    poll = json.loads(msg.content)
                    if option in poll["options"] and user_id not in poll["options"][option]:
                        poll["options"][option].append(user_id)
                        poll["total_votes"] = 1
                        msg.content = json.dumps(poll)
                except:
                    pass
                break

@st.cache_resource
def get_chat_system() -> ChatSystem:
    """Get cached chat system."""
    return ChatSystem()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# TASK MANAGEMENT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@dataclass
class Task:
    id: str
    room_id: str
    title: str
    description: str = ""
    assignee_id: str = ""
    assignee_name: str = ""
    due_date: datetime = None
    priority: str = "medium"  # low, medium, high, urgent
    status: str = "todo"  # todo, in_progress, review, done
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

class TaskManager:
    """Task management for research teams."""
    
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
    
    def create_task(
        self,
        room_id: str,
        title: str,
        description: str = "",
        assignee_id: str = "",
        assignee_name: str = "",
        due_date: datetime = None,
        priority: str = "medium",
    ) -> Task:
        """Create a new task."""
        task = Task(
            id=f"task_{uuid.uuid4().hex[:10]}",
            room_id=room_id,
            title=title,
            description=description,
            assignee_id=assignee_id,
            assignee_name=assignee_name,
            due_date=due_date,
            priority=priority,
        )
        self._tasks[task.id] = task
        return task
    
    def get_room_tasks(self, room_id: str) -> List[Task]:
        """Get all tasks for a room."""
        return [t for t in self._tasks.values() if t.room_id == room_id]
    
    def update_task_status(self, task_id: str, status: str) -> bool:
        """Update task status."""
        if task_id in self._tasks:
            self._tasks[task_id].status = status
            return True
        return False
    
    def get_task_stats(self, room_id: str) -> Dict[str, int]:
        """Get task statistics for a room."""
        tasks = self.get_room_tasks(room_id)
        stats = {"todo": 0, "in_progress": 0, "review": 0, "done": 0}
        for task in tasks:
            if task.status in stats:
                stats[task.status] = 1
        return stats

@st.cache_resource
def get_task_manager() -> TaskManager:
    """Get cached task manager."""
    return TaskManager()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# AI RESEARCH ASSISTANT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class ResearchAssistant:
    """AI-powered research assistant for collaboration rooms."""
    
    def __init__(self):
        self._conversation_history: Dict[str, List[Dict]] = {}
    
    def ask(
        self,
        question: str,
        room_id: str,
        context: str = "",
        use_websearch: bool = True,
        use_literature: bool = True,
    ) -> Dict[str, Any]:
        """Ask the research assistant a question."""
        # In production, integrate with OpenAI/LLM
        # For now, return a structured response
        response = {
            "answer": f"Research insight for: {question[:50]}...",
            "sources": [
                {"title": "Related Paper 1", "url": "#", "relevance": 0.95},
                {"title": "Related Paper 2", "url": "#", "relevance": 0.87},
            ],
            "follow_up": [
                "What methodology was used?",
                "Who are the key authors?",
                "What are the limitations?",
            ],
            "cited_by": 42,
            "similar_topics": ["machine learning", "data analysis"],
        }
        
        # Store in history
        if room_id not in self._conversation_history:
            self._conversation_history[room_id] = []
        
        self._conversation_history[room_id].append({
            "question": question,
            "answer": response["answer"],
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        return response
    
    def summarize_papers(self, paper_links: List[str]) -> Dict[str, Any]:
        """Summarize multiple research papers."""
        return {
            "summary": "Combined summary of papers...",
            "key_findings": [
                "Finding 1",
                "Finding 2", 
                "Finding 3",
            ],
            "methodologies": ["Quantitative", "Qualitative", "Mixed"],
            "gaps_identified": ["Gap 1", "Gap 2"],
        }
    
    def suggest_experts(self, topic: str, count: int = 5) -> List[Dict]:
        """Suggest experts for collaboration."""
        return [
            {"name": f"Prof. {i1}", "affiliation": "University", "expertise": topic, "h_index": 45-i*3}
            for i in range(count)
        ]
    
    def generate_research_brief(self, topic: str) -> Dict[str, Any]:
        """Generate a research brief on a topic."""
        return {
            "executive_summary": f"Brief on {topic}...",
            "key_questions": ["Question 1", "Question 2"],
            "recommended_papers": 15,
            "estimated_reading_time": "4 hours",
            "related_topics": ["topic A", "topic B"],
        }

@st.cache_resource
def get_research_assistant() -> ResearchAssistant:
    """Get cached research assistant."""
    return ResearchAssistant()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# AUTOMATION ENGINE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@dataclass
class Automation:
    id: str
    name: str
    trigger: str  # event that triggers automation
    action: str  # action to perform
    conditions: Dict = field(default_factory=dict)
    enabled: bool = True

class AutomationEngine:
    """Workflow automation for research teams."""
    
    def __init__(self):
        self._automations: Dict[str, Automation] = {}
        self._load_default_automations()
    
    def _load_default_automations(self):
        """Load default automation workflows."""
        defaults = [
            Automation(
                id="auto_1",
                name="New Member Welcome",
                trigger="member_joined",
                action="send_welcome_message",
                conditions={"delay_seconds": 5},
            ),
            Automation(
                id="auto_2",
                name="Meeting Reminder",
                trigger="schedule_near",
                action="send_reminder",
                conditions={"minutes_before": 15},
            ),
            Automation(
                id="auto_3",
                name="Task Assignment Alert",
                trigger="task_assigned",
                action="notify_assignee",
                conditions={},
            ),
            Automation(
                id="auto_4",
                name="Research Paper Alert",
                trigger="new_paper_relevant",
                action="share_to_room",
                conditions={"keywords": ["AI", "research"]},
            ),
            Automation(
                id="auto_5",
                name="Weekly Summary",
                trigger="weekly_schedule",
                action="generate_summary",
                conditions={"day": "friday"},
            ),
        ]
        for auto in defaults:
            self._automations[auto.id] = auto
    
    def create_automation(
        self,
        name: str,
        trigger: str,
        action: str,
        conditions: Dict = None,
    ) -> Automation:
        """Create a new automation."""
        auto = Automation(
            id=f"auto_{uuid.uuid4().hex[:8]}",
            name=name,
            trigger=trigger,
            action=action,
            conditions=conditions or {},
        )
        self._automations[auto.id] = auto
        return auto
    
    def list_automations(self) -> List[Automation]:
        """List all automations."""
        return list(self._automations.values())
    
    def toggle_automation(self, auto_id: str, enabled: bool):
        """Enable/disable automation."""
        if auto_id in self._automations:
            self._automations[auto_id].enabled = enabled
    
    def execute(self, trigger: str, context: Dict):
        """Execute automations for a trigger."""
        for auto in self._automations.values():
            if auto.enabled and auto.trigger == trigger:
                # In production, execute actual actions
                pass

@st.cache_resource
def get_automation_engine() -> AutomationEngine:
    """Get cached automation engine."""
    return AutomationEngine()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LIVE TRANSLATION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TranslationService:
    """Real-time translation for international teams."""
    
    SUPPORTED_LANGUAGES = {
        "en": "English",
        "es": "Spanish", 
        "fr": "French",
        "de": "German",
        "zh": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "pt": "Portuguese",
        "ar": "Arabic",
        "ru": "Russian",
    }
    
    def translate(self, text: str, target_lang: str, source_lang: str = "auto") -> Dict:
        """Translate text between languages."""
        # In production, use Google Translate API or DeepL
        return {
            "translated_text": f"[{target_lang}] {text}",
            "source_lang": source_lang,
            "target_lang": target_lang,
            "confidence": 0.95,
        }
    
    def detect_language(self, text: str) -> str:
        """Detect language of text."""
        return "en"

@st.cache_resource
def get_translation_service() -> TranslationService:
    """Get cached translation service."""
    return TranslationService()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# FILE SHARING & VERSION CONTROL
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@dataclass
class SharedFile:
    id: str
    room_id: str
    name: str
    size: int
    mime_type: str
    uploader_id: str
    uploader_name: str
    version: int = 1
    versions: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

class FileManager:
    """File sharing with version control."""
    
    def __init__(self):
        self._files: Dict[str, SharedFile] = {}
    
    def upload_file(
        self,
        room_id: str,
        name: str,
        size: int,
        mime_type: str,
        uploader_id: str,
        uploader_name: str,
    ) -> SharedFile:
        """Upload a file to the room."""
        file = SharedFile(
            id=f"file_{uuid.uuid4().hex[:10]}",
            room_id=room_id,
            name=name,
            size=size,
            mime_type=mime_type,
            uploader_id=uploader_id,
            uploader_name=uploader_name,
        )
        self._files[file.id] = file
        return file
    
    def get_room_files(self, room_id: str) -> List[SharedFile]:
        """Get all files in a room."""
        return [f for f in self._files.values() if f.room_id == room_id]
    
    def upload_new_version(self, file_id: str, uploader_id: str) -> bool:
        """Upload new version of existing file."""
        if file_id not in self._files:
            return False
        
        file = self._files[file_id]
        file.version = 1
        file.versions.append({
            "version": file.version,
            "uploaded_by": uploader_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        return True

@st.cache_resource
def get_file_manager() -> FileManager:
    """Get cached file manager."""
    return FileManager()
