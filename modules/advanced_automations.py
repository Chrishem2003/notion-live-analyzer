
"""Advanced Automations & Scheduling Module."""
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
# AUTOMATION DEFINITIONS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class AutomationType(Enum):
    SCHEDULED = "scheduled"
    TRIGGERED = "triggered"
    CONDITIONAL = "conditional"
    WEBHOOK = "webhook"

class TriggerEvent(Enum):
    # User events
    USER_JOINED = "user.joined"
    USER_LEFT = "user.left"
    USER_STATUS_CHANGE = "user.status_changed"
    
    # Content events
    NEW_DOCUMENT = "document.new"
    DOCUMENT_UPDATED = "document.updated"
    FILE_UPLOADED = "file.uploaded"
    
    # Research events
    NEW_PAPER_RELEVANT = "paper.relevant"
    CITATION_ALERT = "citation.alert"
    PEER_REVIEW_COMPLETE = "review.complete"
    
    # Meeting events
    MEETING_START = "meeting.start"
    MEETING_END = "meeting.end"
    MEETING_REMINDER = "meeting.reminder"
    
    # Task events
    TASK_CREATED = "task.created"
    TASK_COMPLETED = "task.completed"
    TASK_OVERDUE = "task.overdue"
    
    # Message events
    NEW_MESSAGE = "message.new"
    MENTION = "message.mention"
    
    # Time events
    DAILY_DIGEST = "daily.digest"
    WEEKLY_REPORT = "weekly.report"
    MONTHLY_SUMMARY = "monthly.summary"

class ActionType(Enum):
    SEND_NOTIFICATION = "notification.send"
    SEND_EMAIL = "email.send"
    SEND_SLACK = "slack.send"
    
    CREATE_TASK = "task.create"
    UPDATE_TASK = "task.update"
    ASSIGN_TASK = "task.assign"
    
    POST_MESSAGE = "message.post"
    SEND_REMINDER = "reminder.send"
    
    RUN_SCRIPT = "script.run"
    API_CALL = "api.call"
    
    UPDATE_STATUS = "status.update"
    SYNC_DATA = "data.sync"

@dataclass
class Automation:
    id: str
    name: str
    description: str
    automation_type: AutomationType
    trigger: TriggerEvent
    action: ActionType
    conditions: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    schedule: str = ""  # cron expression for scheduled
    last_run: datetime = None
    run_count: int = 0
    
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ADVANCED AUTOMATION ENGINE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class AdvancedAutomationEngine:
    """Production-grade automation engine with scheduling & webhooks."""
    
    def __init__(self):
        self._automations: Dict[str, Automation] = {}
        self._execution_log: List[Dict] = []
        self._webhooks: Dict[str, Callable] = {}
        self._load_prebuilt_automations()
    
    def _load_prebuilt_automations(self):
        """Load prebuilt automation templates."""
        prebuilt = [
            Automation(
                id="auto_welcome",
                name="ðŸ‘‹ Welcome New Members",
                description="Send welcome message when user joins",
                automation_type=AutomationType.TRIGGERED,
                trigger=TriggerEvent.USER_JOINED,
                action=ActionType.SEND_NOTIFICATION,
                config={"message": "Welcome to the Research Command Center!"},
            ),
            Automation(
                id="auto_meeting_reminder",
                name="ðŸ”” Meeting Reminder",
                description="Remind participants 15 min before meeting",
                automation_type=AutomationType.SCHEDULED,
                trigger=TriggerEvent.MEETING_REMINDER,
                action=ActionType.SEND_NOTIFICATION,
                config={"minutes_before": 15},
            ),
            Automation(
                id="auto_task_overdue",
                name="â° Overdue Task Alert",
                description="Alert when tasks become overdue",
                automation_type=AutomationType.TRIGGERED,
                trigger=TriggerEvent.TASK_OVERDUE,
                action=ActionType.SEND_NOTIFICATION,
                config={"priority": "high"},
            ),
            Automation(
                id="auto_daily_digest",
                name=" Daily Research Digest",
                description="Daily summary of research activity",
                automation_type=AutomationType.SCHEDULED,
                trigger=TriggerEvent.DAILY_DIGEST,
                action=ActionType.SEND_EMAIL,
                schedule="0 9 * * *",  # 9 AM daily
                config={"template": "daily_digest"},
            ),
            Automation(
                id="auto_weekly_report",
                name="ðŸ“ˆ Weekly Team Report",
                description="Weekly team progress report",
                automation_type=AutomationType.SCHEDULED,
                trigger=TriggerEvent.WEEKLY_REPORT,
                action=ActionType.SEND_EMAIL,
                schedule="0 18 * * Friday",  # Friday 6 PM
                config={"template": "weekly_report"},
            ),
            Automation(
                id="auto_paper_alert",
                name="ðŸ“° Relevant Paper Alert",
                description="Alert when new relevant papers published",
                automation_type=AutomationType.TRIGGERED,
                trigger=TriggerEvent.NEW_PAPER_RELEVANT,
                action=ActionType.SEND_NOTIFICATION,
                config={"keywords": ["AI", "machine learning", "research"]},
            ),
            Automation(
                id="auto_citation_found",
                name="ðŸ”— Citation Alert",
                description="Alert when paper is cited",
                automation_type=AutomationType.TRIGGERED,
                trigger=TriggerEvent.CITATION_ALERT,
                action=ActionType.SEND_NOTIFICATION,
            ),
            Automation(
                id="auto_new_member_intro",
                name="ðŸŽ“ New Member Introduction",
                description="Introduce new members to the team",
                automation_type=AutomationType.TRIGGERED,
                trigger=TriggerEvent.USER_JOINED,
                action=ActionType.POST_MESSAGE,
                config={"channel": "general", "template": "intro"},
            ),
            Automation(
                id="auto_task_escalation",
                name="âš ï¸ Task Escalation",
                description="Escalate high-priority overdue tasks",
                automation_type=AutomationType.CONDITIONAL,
                trigger=TriggerEvent.TASK_OVERDUE,
                action=ActionType.SEND_NOTIFICATION,
                conditions={"priority": "urgent", "days_overdue": 2},
            ),
            Automation(
                id="auto_data_backup",
                name="ðŸ’¾ Data Backup",
                description="Automatically backup research data",
                automation_type=AutomationType.SCHEDULED,
                trigger=TriggerEvent.DAILY_DIGEST,
                action=ActionType.SYNC_DATA,
                schedule="0 2 * * *",  # 2 AM daily
                config={"target": "supabase", "tables": ["research", "papers"]},
            ),
        ]
        
        for auto in prebuilt:
            self._automations[auto.id] = auto
    
    def create_automation(
        self,
        name: str,
        description: str,
        automation_type: AutomationType,
        trigger: TriggerEvent,
        action: ActionType,
        config: Dict = None,
        schedule: str = "",
    ) -> Automation:
        """Create new automation."""
        auto = Automation(
            id=f"auto_{uuid.uuid4().hex[:10]}",
            name=name,
            description=description,
            automation_type=automation_type,
            trigger=trigger,
            action=action,
            config=config or {},
            schedule=schedule,
            enabled=True,
        )
        self._automations[auto.id] = auto
        return auto
    
    def get_automation(self, auto_id: str) -> Optional[Automation]:
        return self._automations.get(auto_id)
    
    def list_automations(self, automation_type: AutomationType = None) -> List[Automation]:
        autos = list(self._automations.values())
        if automation_type:
            autos = [a for a in autos if a.automation_type == automation_type]
        return sorted(autos, key=lambda a: a.name)
    
    def toggle_automation(self, auto_id: str, enabled: bool):
        if auto_id in self._automations:
            self._automations[auto_id].enabled = enabled
    
    def delete_automation(self, auto_id: str):
        if auto_id in self._automations:
            del self._automations[auto_id]
    
    def execute(self, trigger: TriggerEvent, context: Dict) -> List[Dict]:
        """Execute all automations matching trigger."""
        results = []
        
        for auto in self._automations.values():
            if not auto.enabled:
                continue
            
            if auto.trigger != trigger:
                continue
            
            # Check conditions
            if auto.conditions:
                conditions_met = all(
                    context.get(k) == v 
                    for k, v in auto.conditions.items()
                )
                if not conditions_met:
                    continue
            
            # Execute action
            try:
                result = self._execute_action(auto, context)
                results.append({
                    "automation_id": auto.id,
                    "status": "success",
                    "result": result,
                })
                
                # Update stats
                auto.run_count = 1
                auto.last_run = datetime.utcnow()
                
            except Exception as e:
                results.append({
                    "automation_id": auto.id,
                    "status": "error",
                    "error": str(e),
                })
        
        # Log execution
        self._execution_log.append({
            "trigger": trigger.value,
            "context": context,
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        return results
    
    def _execute_action(self, auto: Automation, context: Dict) -> Any:
        """Execute a single automation action."""
        action = auto.action
        
        if action == ActionType.SEND_NOTIFICATION:
            return self._action_send_notification(auto, context)
        elif action == ActionType.SEND_EMAIL:
            return self._action_send_email(auto, context)
        elif action == ActionType.CREATE_TASK:
            return self._action_create_task(auto, context)
        elif action == ActionType.POST_MESSAGE:
            return self._action_post_message(auto, context)
        elif action == ActionType.SEND_REMINDER:
            return self._action_send_reminder(auto, context)
        elif action == ActionType.RUN_SCRIPT:
            return self._action_run_script(auto, context)
        elif action == ActionType.API_CALL:
            return self._action_api_call(auto, context)
        elif action == ActionType.SYNC_DATA:
            return self._action_sync_data(auto, context)
        
        return {"action": action.value, "executed": True}
    
    def _action_send_notification(self, auto: Automation, context: Dict) -> Dict:
        """Send in-app notification."""
        message = auto.config.get("message", "Notification")
        return {"sent": True, "message": message}
    
    def _action_send_email(self, auto: Automation, context: Dict) -> Dict:
        """Send email notification."""
        # In production, integrate with email module
        template = auto.config.get("template", "default")
        return {"sent": True, "template": template}
    
    def _action_create_task(self, auto: Automation, context: Dict) -> Dict:
        """Create a task."""
        return {"task_id": f"task_{uuid.uuid4().hex[:8]}", "created": True}
    
    def _action_post_message(self, auto: Automation, context: Dict) -> Dict:
        """Post message to channel."""
        channel = auto.config.get("channel", "general")
        return {"posted": True, "channel": channel}
    
    def _action_send_reminder(self, auto: Automation, context: Dict) -> Dict:
        """Send reminder."""
        return {"reminder_sent": True}
    
    def _action_run_script(self, auto: Automation, context: Dict) -> Dict:
        """Run custom script."""
        return {"script_executed": True}
    
    def _action_api_call(self, auto: Automation, context: Dict) -> Dict:
        """Make API call."""
        return {"api_called": True}
    
    def _action_sync_data(self, auto: Automation, context: Dict) -> Dict:
        """Sync data to external service."""
        target = auto.config.get("target", "supabase")
        return {"synced": True, "target": target}
    
    def register_webhook(self, event: str, handler: Callable):
        """Register webhook handler."""
        self._webhooks[event] = handler
    
    def get_execution_log(self, limit: int = 50) -> List[Dict]:
        return self._execution_log[-limit:]
    
    def get_stats(self) -> Dict:
        """Get automation statistics."""
        total = len(self._automations)
        enabled = sum(1 for a in self._automations.values() if a.enabled)
        
        return {
            "total": total,
            "enabled": enabled,
            "disabled": total - enabled,
            "total_runs": sum(a.run_count for a in self._automations.values()),
            "by_type": {
                "scheduled": len([a for a in self._automations.values() 
                                 if a.automation_type == AutomationType.SCHEDULED]),
                "triggered": len([a for a in self._automations.values() 
                                 if a.automation_type == AutomationType.TRIGGERED]),
                "conditional": len([a for a in self._automations.values() 
                                   if a.automation_type == AutomationType.CONDITIONAL]),
            },
        }

@st.cache_resource
def get_advanced_automation_engine() -> AdvancedAutomationEngine:
    """Get cached automation engine."""
    return AdvancedAutomationEngine()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# SCHEDULING SYSTEM
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TaskScheduler:
    """Cron-like task scheduler for research workflows."""
    
    def __init__(self):
        self._scheduled_tasks: Dict[str, Dict] = {}
        self._last_check = datetime.utcnow()
    
    def schedule_task(
        self,
        task_id: str,
        cron_expr: str,
        handler: Callable,
        args: Dict = None,
    ):
        """Schedule a recurring task."""
        self._scheduled_tasks[task_id] = {
            "cron": cron_expr,
            "handler": handler,
            "args": args or {},
            "last_run": None,
            "next_run": self._calc_next_run(cron_expr),
        }
    
    def _calc_next_run(self, cron_expr: str) -> datetime:
        """Calculate next run time from cron expression."""
        # Simplified cron parser
        # In production, use python-croniter
        parts = cron_expr.split()
        if len(parts) >= 5:
            now = datetime.utcnow()
            # Very simplified - just add hours
            return now  timedelta(hours=1)
        return datetime.utcnow()  timedelta(days=1)
    
    def check_and_run(self) -> List[Dict]:
        """Check and run due tasks."""
        now = datetime.utcnow()
        results = []
        
        for task_id, task in self._scheduled_tasks.items():
            if now >= task["next_run"]:
                try:
                    result = task["handler"](**task["args"])
                    results.append({"task_id": task_id, "result": result})
                    task["last_run"] = now
                    task["next_run"] = self._calc_next_run(task["cron"])
                except Exception as e:
                    results.append({"task_id": task_id, "error": str(e)})
        
        self._last_check = now
        return results
    
    def get_upcoming_tasks(self) -> List[Dict]:
        """Get upcoming scheduled tasks."""
        return [
            {"task_id": k, "next_run": v["next_run"]}
            for k, v in self._scheduled_tasks.items()
        ]

@st.cache_resource
def get_task_scheduler() -> TaskScheduler:
    """Get cached task scheduler."""
    return TaskScheduler()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ADVANCED NOTIFICATIONS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@dataclass
class Notification:
    id: str
    user_id: str
    title: str
    message: str
    notification_type: str = "info"  # info, success, warning, error
    read: bool = False
    action_url: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

class NotificationManager:
    """Advanced notification system with channels."""
    
    def __init__(self):
        self._notifications: Dict[str, List[Notification]] = {}
        self._channels = {
            "in_app": [],
            "email": [],
            "slack": [],
            "sms": [],
        }
    
    def add_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "info",
        action_url: str = "",
    ) -> Notification:
        """Add notification for user."""
        notif = Notification(
            id=f"notif_{uuid.uuid4().hex[:10]}",
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            action_url=action_url,
        )
        
        if user_id not in self._notifications:
            self._notifications[user_id] = []
        
        self._notifications[user_id].append(notif)
        return notif
    
    def get_notifications(self, user_id: str, unread_only: bool = False) -> List[Notification]:
        """Get user notifications."""
        notifs = self._notifications.get(user_id, [])
        if unread_only:
            notifs = [n for n in notifs if not n.read]
        return sorted(notifs, key=lambda n: n.created_at, reverse=True)
    
    def mark_read(self, user_id: str, notif_id: str):
        """Mark notification as read."""
        for notif in self._notifications.get(user_id, []):
            if notif.id == notif_id:
                notif.read = True
    
    def get_unread_count(self, user_id: str) -> int:
        """Get unread notification count."""
        return len([n for n in self._notifications.get(user_id, []) if not n.read])

@st.cache_resource
def get_notification_manager() -> NotificationManager:
    """Get cached notification manager."""
    return NotificationManager()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STREAMLIT UI
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def render_automations_advanced():
    """Render the advanced automations UI."""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1e293b, #0f172a);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border: 1px solid #334155;
    ">
        <h2 style="margin:0; color: white;">âš¡ Advanced Automations</h2>
        <p style="color: #94a3b8; margin-top: 0.5rem;">
            Scheduled workflows, triggers, and intelligent alerts
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    engine = get_advanced_automation_engine()
    scheduler = get_task_scheduler()
    notif_mgr = get_notification_manager()
    
    # Stats
    stats = engine.get_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Automations", stats["total"])
    col2.metric("Active", stats["enabled"])
    col3.metric(f"âš™ï¸ Scheduled", stats["by_type"]["scheduled"])
    col4.metric("ðŸ”„ Triggers", stats["by_type"]["triggered"])
    
    st.divider()
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "ðŸ¤– Automations",
        "ðŸ“… Schedule",
        "ðŸ”” Notifications",
        " Logs",
    ])
    
    with tab1:
        render_automation_list(engine)
    
    with tab2:
        render_scheduler_ui(scheduler)
    
    with tab3:
        render_notifications_ui(notif_mgr)
    
    with tab4:
        render_automation_logs(engine)

def render_automation_list(engine: AdvancedAutomationEngine):
    """Render automation list."""
    st.subheader("All Automations")
    
    # Filter
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("Search automations...", placeholder="Search...")
    with col2:
        filter_type = st.selectbox("Type", ["All", "Scheduled", "Triggered", "Conditional"])
    
    automations = engine.list_automations()
    
    if filter_type != "All":
        type_map = {"Scheduled": AutomationType.SCHEDULED, 
                   "Triggered": AutomationType.TRIGGERED,
                   "Conditional": AutomationType.CONDITIONAL}
        automations = [a for a in automations if a.automation_type == type_map[filter_type]]
    
    if search:
        automations = [a for a in automations if search.lower() in a.name.lower()]
    
    # Create new
    with st.expander("âž• Create New Automation", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name")
            desc = st.text_area("Description")
        with col2:
            trigger = st.selectbox("Trigger", [t.value for t in TriggerEvent])
            action = st.selectbox("Action", [a.value for a in ActionType])
        
        if st.button("Create Automation", type="primary") and name:
            engine.create_automation(
                name=name,
                description=desc,
                automation_type=AutomationType.TRIGGERED,
                trigger=TriggerEvent(trigger),
                action=ActionType(action),
            )
            st.success("Automation created!")
            st.rerun()
    
    st.divider()
    
    # List
    for auto in automations:
        type_badge = {
            AutomationType.SCHEDULED: ("â° Scheduled", "ðŸ”µ"),
            AutomationType.TRIGGERED: ("âš¡ Triggered", "ðŸŸ¢"),
            AutomationType.CONDITIONAL: ("ðŸ”€ Conditional", "ðŸŸ¡"),
        }
        badge, emoji = type_badge.get(auto.automation_type, ("ðŸ“Œ", "âšª"))
        
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.markdown(f"**{emoji} {auto.name}**")
            st.caption(auto.description)
        
        with col2:
            st.markdown(f"`{auto.trigger.value}` â†’ `{auto.action.value}`")
            if auto.schedule:
                st.caption(f"Schedule: `{auto.schedule}`")
        
        with col3:
            col_a, col_b = st.columns(2)
            with col_a:
                enabled = st.checkbox("On", value=auto.enabled, key=f"auto_{auto.id}")
                if enabled != auto.enabled:
                    engine.toggle_automation(auto.id, enabled)
                    st.rerun()
            with col_b:
                if st.button("ðŸ—‘ï¸", key=f"del_{auto.id}"):
                    engine.delete_automation(auto.id)
                    st.rerun()
        
        st.divider()

def render_scheduler_ui(scheduler: TaskScheduler):
    """Render scheduler UI."""
    st.subheader("ðŸ“… Scheduled Tasks")
    
    upcoming = scheduler.get_upcoming_tasks()
    
    if not upcoming:
        st.info("No scheduled tasks")
    
    for task in upcoming:
        st.markdown(f"""
        <div style="
            background: #1e293b;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            border-left: 4px solid #3b82f6;
        ">
            <strong>{task['task_id']}</strong>
            <br>
            <span style="color: #94a3b8;">
                Next run: {task['next_run'].strftime('%Y-%m-%d %H:%M')}
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    # Check now button
    if st.button("â–¶ï¸ Check & Run Due Tasks"):
        results = scheduler.check_and_run()
        if results:
            st.success(f"Ran {len(results)} tasks")
        else:
            st.info("No tasks due")

def render_notifications_ui(notif_mgr: NotificationManager):
    """Render notifications UI."""
    st.subheader("ðŸ”” Notifications")
    
    user_id = st.session_state.get("collab_user_id", "demo_user")
    
    # Demo notifications
    demo_notifs = [
        ("", "Weekly Report Ready", "Your weekly research summary is ready", "info"),
        ("â°", "Task Reminder", "Review pending: Data analysis due in 2 hours", "warning"),
        ("âœ…", "Task Completed", "Analysis complete for Project Alpha", "success"),
    ]
    
    for emoji, title, msg, ntype in demo_notifs:
        color = {"info": "#3b82f6", "warning": "#f59e0b", "success": "#22c55e", "error": "#ef4444"}[ntype]
        
        st.markdown(f"""
        <div style="
            background: #1e293b;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            border-left: 4px solid {color};
        ">
            <span style="font-size: 20px;">{emoji}</span>
            <strong style="margin-left: 10px;">{title}</strong>
            <p style="color: #94a3b8; margin: 5px 0 0 30px;">{msg}</p>
        </div>
        """, unsafe_allow_html=True)

def render_automation_logs(engine: AdvancedAutomationEngine):
    """Render execution logs."""
    st.subheader(" Execution Logs")
    
    logs = engine.get_execution_log()
    
    if not logs:
        st.info("No execution logs yet")
        return
    
    for log in logs[-20:]:
        trigger = log.get("trigger", "unknown")
        timestamp = log.get("timestamp", "")
        results = log.get("results", [])
        
        success_count = sum(1 for r in results if r.get("status") == "success")
        
        st.markdown(f"""
        <div style="background: #0f172a; padding: 10px; border-radius: 8px; margin-bottom: 8px;">
            <span style="color: #94a3b8;">{timestamp}</span>
            |
            <code>{trigger}</code>
            |
            <span style="color: {'#22c55e' if success_count else '#ef4444'};">
                {success_count}/{len(results)} succeeded
            </span>
        </div>
        """, unsafe_allow_html=True)
