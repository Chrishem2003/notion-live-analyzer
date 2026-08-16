"""
workspace.py  multi-workspace / agency mode.

Lets one account manage several Notion workspaces (e.g. a consultant's
clients) and see aggregated health across them. This feature is what turns
the app from a personal tool into something worth a monthly subscription.

This is pure-logic (no Streamlit UI imports at module level). The storage
layer is injected via function arguments so it works with any DB backend
(SQLite, Supabase, etc.).
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional


class WorkspaceRole(str, Enum):
    OWNER = "owner"       # can connect/disconnect workspaces, manage members
    MEMBER = "member"     # can view + act on audits
    VIEWER = "viewer"     # read-only, e.g. a client checking their own report


@dataclass
class Workspace:
    id: str
    owner_user_id: str              # the subscriber who connected it
    name: str                       # display name, e.g. "Acme Co — Notion"
    notion_workspace_id: str        # Notion's own workspace identifier
    notion_token_ref: str           # reference/key into your secrets store —
                                     # NEVER store the raw Notion API token in
                                     # the row itself; keep it in a secrets
                                     # manager or encrypted column
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


@dataclass
class WorkspaceMembership:
    workspace_id: str
    user_id: str
    role: WorkspaceRole


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

def user_can_access_workspace(
    user_id: str, workspace_id: str,
    get_membership_fn: Callable[[str, str], Optional[WorkspaceMembership]],
) -> bool:
    """Check if a user has *any* membership role in a workspace."""
    membership = get_membership_fn(user_id, workspace_id)
    return membership is not None


def user_workspace_role(
    user_id: str, workspace_id: str,
    get_membership_fn: Callable[[str, str], Optional[WorkspaceMembership]],
) -> Optional[WorkspaceRole]:
    """Return the user's role in a workspace, or None."""
    membership = get_membership_fn(user_id, workspace_id)
    return membership.role if membership else None


# ---------------------------------------------------------------------------
# Subscription gating — agency mode is a paid tier feature
# ---------------------------------------------------------------------------

MAX_WORKSPACES_BY_TIER = {
    "trial": 1,
    "free": 1,
    "standard": 1,
    "premium": 5,
    "agency": 25,  # tune to your pricing
}


def can_connect_another_workspace(
    user_id: str,
    plan_tier: str,
    count_workspaces_fn: Callable[[str], int],
) -> bool:
    """Returns True if the user can add a workspace under their current plan."""
    limit = MAX_WORKSPACES_BY_TIER.get(plan_tier, 1)
    current_count = count_workspaces_fn(user_id)
    return current_count < limit


# ---------------------------------------------------------------------------
# Connecting a new workspace
# ---------------------------------------------------------------------------

def connect_workspace(
    owner_user_id: str,
    name: str,
    notion_workspace_id: str,
    notion_token_ref: str,
    plan_tier: str,
    count_workspaces_fn: Callable[[str], int],
    create_workspace_fn: Callable[..., Workspace],
    create_membership_fn: Callable[..., WorkspaceMembership],
) -> Workspace:
    """Connect a new workspace for a user. Raises PermissionError if at limit."""
    if not can_connect_another_workspace(owner_user_id, plan_tier, count_workspaces_fn):
        limit = MAX_WORKSPACES_BY_TIER.get(plan_tier, 1)
        raise PermissionError(
            f"Plan '{plan_tier}' allows at most {limit} "
            "connected workspace(s). Upgrade to Agency to add more."
        )

    workspace = create_workspace_fn(
        owner_user_id=owner_user_id,
        name=name,
        notion_workspace_id=notion_workspace_id,
        notion_token_ref=notion_token_ref,
    )
    create_membership_fn(
        workspace_id=workspace.id,
        user_id=owner_user_id,
        role=WorkspaceRole.OWNER,
    )
    return workspace


# ---------------------------------------------------------------------------
# Aggregated health across all of a user's workspaces
# ---------------------------------------------------------------------------

@dataclass
class WorkspaceHealthSummary:
    workspace_id: str
    workspace_name: str
    health_score: float           # 0-100, from your audit engine
    open_findings: int
    last_audited_at: Optional[datetime]


def aggregate_health_across_workspaces(
    user_id: str,
    list_workspaces_for_user_fn: Callable[[str], list[Workspace]],
    get_latest_health_fn: Callable[[Workspace], Optional[WorkspaceHealthSummary]],
) -> list[WorkspaceHealthSummary]:
    """Powers the agency-mode dashboard: one screen, all clients, worst-first.

    Workspaces that need attention surface first.
    """
    workspaces = list_workspaces_for_user_fn(user_id)
    summaries: list[WorkspaceHealthSummary] = []
    for ws in workspaces:
        health = get_latest_health_fn(ws)
        if health is not None:
            summaries.append(health)
    # Worst health first — that's what an agency user wants to see on login.
    summaries.sort(key=lambda s: s.health_score)
    return summaries


# ---------------------------------------------------------------------------
# Streamlit-style "active workspace" switcher (lazily imports streamlit)
# ---------------------------------------------------------------------------

def render_workspace_switcher(
    user_id: str,
    list_workspaces_for_user_fn: Callable[[str], list[Workspace]],
) -> str:
    """Call near the top of every page, below auth/trial checks.

    Sets ``st.session_state['active_workspace_id']`` and returns the id so
    every other page knows which client's data to show. If there are no
    workspaces, renders an info message and stops.
    """
    import streamlit as st  # lazy import

    workspaces = list_workspaces_for_user_fn(user_id)
    if not workspaces:
        st.info("Connect a Notion workspace to get started.")
        st.stop()
        return ""

    options = {ws.name: ws.id for ws in workspaces}
    choice = st.selectbox("Workspace", options.keys())
    st.session_state["active_workspace_id"] = options[choice]
    return options[choice]
