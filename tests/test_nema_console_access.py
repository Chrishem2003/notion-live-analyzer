from nema_agora.access import has_authenticated_portal_session


def test_rejects_missing_or_locked_portal_session():
    assert has_authenticated_portal_session({}) is False
    assert has_authenticated_portal_session({"portal_unlocked": False, "user_identity": {"email": "user@example.com"}}) is False
    assert has_authenticated_portal_session({"portal_unlocked": 1, "user_identity": {"email": "user@example.com"}}) is False


def test_rejects_missing_or_invalid_identity():
    assert has_authenticated_portal_session({"portal_unlocked": True}) is False
    assert has_authenticated_portal_session({"portal_unlocked": True, "user_identity": None}) is False
    assert has_authenticated_portal_session({"portal_unlocked": True, "user_identity": {"email": " "}}) is False
    assert has_authenticated_portal_session({"portal_unlocked": True, "user_identity": {"email": 123}}) is False


def test_accepts_portal_identity_established_by_main_auth_flow():
    assert has_authenticated_portal_session({
        "portal_unlocked": True,
        "user_identity": {"email": "operator@example.com", "role": "admin"},
    }) is True
