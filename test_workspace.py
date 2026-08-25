"""Unit tests for modules.workspace pure-logic functions."""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from modules.workspace import (
    WorkspaceRole,
    Workspace,
    WorkspaceMembership,
    user_can_access_workspace,
    user_workspace_role,
    can_connect_another_workspace,
    connect_workspace,
    aggregate_health_across_workspaces,
    WorkspaceHealthSummary,
)


class TestAccessControl:
    def test_user_can_access_when_member_exists(self):
        getter = MagicMock(return_value=WorkspaceMembership(workspace_id="ws1", user_id="u1", role=WorkspaceRole.VIEWER))
        assert user_can_access_workspace("u1", "ws1", getter) is True
        getter.assert_called_once_with("u1", "ws1")

    def test_user_cannot_access_when_no_membership(self):
        getter = MagicMock(return_value=None)
        assert user_can_access_workspace("u1", "ws1", getter) is False

    def test_user_workspace_role_returns_role(self):
        getter = MagicMock(return_value=WorkspaceMembership(workspace_id="ws1", user_id="u1", role=WorkspaceRole.OWNER))
        assert user_workspace_role("u1", "ws1", getter) == WorkspaceRole.OWNER

    def test_user_workspace_role_returns_none(self):
        getter = MagicMock(return_value=None)
        assert user_workspace_role("u1", "ws1", getter) is None


class TestCanConnect:
    def test_allows_when_under_limit(self):
        counter = MagicMock(return_value=0)
        assert can_connect_another_workspace("u1", "agency", counter) is True

    def test_blocks_when_at_limit(self):
        counter = MagicMock(return_value=25)
        assert can_connect_another_workspace("u1", "agency", counter) is False

    def test_free_tier_blocks_at_one(self):
        counter = MagicMock(return_value=1)
        assert can_connect_another_workspace("u1", "free", counter) is False

    def test_trial_tier_blocks_at_one(self):
        counter = MagicMock(return_value=1)
        assert can_connect_another_workspace("u1", "trial", counter) is False


class TestConnectWorkspace:
    def test_successful_connection(self):
        def count(user_id: str) -> int:
            return 0

        created_workspaces = []

        def create_ws(**kwargs):
            ws = Workspace(
                id="ws_new", owner_user_id=kwargs["owner_user_id"],
                name=kwargs["name"], notion_workspace_id=kwargs["notion_workspace_id"],
                notion_token_ref=kwargs["notion_token_ref"],
            )
            created_workspaces.append(ws)
            return ws

        created_memberships = []

        def create_membership(**kwargs):
            m = WorkspaceMembership(**kwargs)
            created_memberships.append(m)
            return m

        result = connect_workspace("u1", "Acme", "ntn_ws1", "ref_abc", "agency", count, create_ws, create_membership)
        assert result.name == "Acme"
        assert len(created_workspaces) == 1
        assert created_memberships[0].role == WorkspaceRole.OWNER

    def test_raises_permission_error_when_at_limit(self):
        def count(user_id: str) -> int:
            return 1

        with pytest.raises(PermissionError, match="Plan 'free' allows at most 1"):
            connect_workspace("u1", "X", "ntn_x", "r", "free", count, lambda **k: None, lambda **k: None)


class TestAggregateHealth:
    def test_returns_sorted_worst_first(self):
        ws1 = Workspace(id="ws1", owner_user_id="u1", name="Workspace 1", notion_workspace_id="n1", notion_token_ref="r1")
        ws2 = Workspace(id="ws2", owner_user_id="u1", name="Workspace 2", notion_workspace_id="n2", notion_token_ref="r2")

        def list_ws(uid):
            return [ws1, ws2]

        def health(ws):
            if ws.id == "ws1":
                return WorkspaceHealthSummary(workspace_id="ws1", workspace_name="Workspace 1", health_score=30, open_findings=5, last_audited_at=datetime.now(timezone.utc))
            return WorkspaceHealthSummary(workspace_id="ws2", workspace_name="Workspace 2", health_score=90, open_findings=1, last_audited_at=datetime.now(timezone.utc))

        result = aggregate_health_across_workspaces("u1", list_ws, health)
        assert len(result) == 2
        # Worst (30) should come first
        assert result[0].health_score == 30
        assert result[1].health_score == 90

    def test_skips_workspaces_without_health(self):
        ws = Workspace(id="ws1", owner_user_id="u1", name="W1", notion_workspace_id="n1", notion_token_ref="r1")

        def list_ws(uid):
            return [ws]

        def health(ws):
            return None

        assert aggregate_health_across_workspaces("u1", list_ws, health) == []


class TestEnumValues:
    def test_workspace_role_values(self):
        assert WorkspaceRole.OWNER.value == "owner"
        assert WorkspaceRole.MEMBER.value == "member"
        assert WorkspaceRole.VIEWER.value == "viewer"
