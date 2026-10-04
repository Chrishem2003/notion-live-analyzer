import pytest

from nema_agora.access import (
    PERMISSIONS,
    ROLE_PERMISSIONS,
    can_read_observation,
    has_permission,
    require_permission,
)


def test_roles_have_only_known_permissions():
    assert set().union(*ROLE_PERMISSIONS.values()) <= PERMISSIONS


@pytest.mark.parametrize(
    ("role", "permission", "expected"),
    [
        ("submitter", "observation:create", True),
        ("submitter", "observation:read_own", True),
        ("submitter", "observation:read_all", False),
        ("reviewer", "observation:review", True),
        ("reviewer", "case:export", False),
        ("reviewer", "intelligence:use", True),
        ("coordinator", "case:export", True),
        ("coordinator", "user:manage", False),
        ("coordinator", "intelligence:use", True),
        ("coordinator", "intelligence:feedback", True),
        ("admin", "user:manage", True),
        ("unknown", "observation:create", False),
        (None, "observation:create", False),
        ("admin", "system:root", False),
    ],
)
def test_permission_matrix(role, permission, expected):
    assert has_permission(role, permission) is expected


def test_role_name_is_case_and_whitespace_normalised():
    assert has_permission("  REVIEWER ", "observation:review")


def test_require_permission_raises_for_denied_action():
    with pytest.raises(PermissionError):
        require_permission("submitter", "observation:review")


def test_require_permission_returns_none_when_allowed():
    assert require_permission("reviewer", "observation:review") is None


def test_submitter_can_read_only_owned_observation():
    assert can_read_observation("submitter", "user-1", "user-1")
    assert not can_read_observation("submitter", "user-1", "user-2")
    assert not can_read_observation("submitter", "", "")
    assert not can_read_observation("submitter", None, "user-1")


def test_reviewer_can_read_all_observations():
    assert can_read_observation("reviewer", "reviewer-1", "user-2")


def test_unknown_role_cannot_read_observations():
    assert not can_read_observation("mystery", "user-1", "user-1")


def test_submitter_cannot_use_intelligence():
    assert not has_permission("submitter", "intelligence:use")


def test_admin_can_use_intelligence():
    assert has_permission("admin", "intelligence:use")
    assert has_permission("admin", "intelligence:feedback")


def test_shadow_permission_is_reviewer_coordinator_admin_only():
    assert not has_permission("submitter", "intelligence:shadow")
    assert has_permission("reviewer", "intelligence:shadow")
    assert has_permission("coordinator", "intelligence:shadow")
    assert has_permission("admin", "intelligence:shadow")
