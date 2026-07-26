"""Tests for modules.session_auth — session handling and visitor gating."""
import pytest

from modules import session_auth
from modules.accounts import AccountError, SQLiteAccountStore, Tier, register, set_tier
from modules.billing import AUDIT_CHECK, EXPORT_PDF, NOTION_TEMPLATE, UNLIMITED


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """Point the session layer at a throwaway store."""
    account_store = SQLiteAccountStore(tmp_path / "accounts.db")
    monkeypatch.setattr(session_auth, "store", lambda: account_store)
    return account_store


@pytest.fixture(autouse=True)
def session(bare_session_state, monkeypatch):
    monkeypatch.setattr(session_auth, "st", _StreamlitStub(bare_session_state))
    return bare_session_state


class _StreamlitStub:
    """Minimal stand-in exposing the Streamlit surface session_auth touches."""

    def __init__(self, state):
        self.session_state = state


class TestSessionLifecycle:
    def test_no_user_by_default(self, store):
        assert session_auth.current_user() is None

    def test_sign_in_then_read_back(self, store):
        user = register(store, "chris@example.com", "password123")
        session_auth.sign_in(user)
        assert session_auth.current_user().id == user.id

    def test_refresh_picks_up_tier_changes(self, store):
        user = register(store, "chris@example.com", "password123", with_trial=False)
        session_auth.sign_in(user)
        set_tier(store, user, Tier.PREMIUM)
        assert session_auth.current_user().tier is Tier.FREE
        assert session_auth.current_user(refresh=True).tier is Tier.PREMIUM

    def test_sign_out_clears_the_session(self, store):
        session_auth.sign_in(register(store, "chris@example.com", "password123"))
        session_auth.sign_out()
        assert session_auth.current_user() is None

    def test_deleted_account_signs_the_visitor_out(self, store, session):
        user = register(store, "chris@example.com", "password123")
        session_auth.sign_in(user)
        store.delete_user(user.id)
        session.pop("_account_user_obj")
        assert session_auth.current_user() is None
        assert session_auth.SESSION_USER_KEY not in session

    def test_is_admin_reflects_the_account(self, store, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", "boss@example.com")
        session_auth.sign_in(register(store, "chris@example.com", "password123"))
        assert session_auth.is_admin() is False
        session_auth.sign_in(register(store, "boss@example.com", "password123"))
        assert session_auth.is_admin() is True


class TestAnonymousGating:
    def test_free_features_are_open(self, store):
        assert session_auth.entitlement(EXPORT_PDF).allowed

    def test_premium_features_prompt_a_sign_in(self, store):
        result = session_auth.entitlement(NOTION_TEMPLATE)
        assert not result.allowed
        assert "Sign in" in result.reason

    def test_metered_features_use_the_free_quota(self, store):
        assert session_auth.entitlement(AUDIT_CHECK).limit == 3

    def test_usage_is_counted_in_the_session(self, store, session):
        session_auth.consume(AUDIT_CHECK)
        assert session[session_auth.ANON_USAGE_KEY] == {AUDIT_CHECK: 1}
        assert session_auth.entitlement(AUDIT_CHECK).remaining == 2

    def test_exhausted_quota_blocks_further_use(self, store):
        for _ in range(3):
            session_auth.consume(AUDIT_CHECK)
        result = session_auth.entitlement(AUDIT_CHECK)
        assert not result.allowed
        assert "Sign in" in result.reason
        with pytest.raises(AccountError):
            session_auth.consume(AUDIT_CHECK)


class TestSignedInGating:
    def test_usage_is_recorded_against_the_account(self, store):
        user = register(store, "chris@example.com", "password123", with_trial=False)
        session_auth.sign_in(user)
        session_auth.consume(AUDIT_CHECK)
        assert store.usage_count(user.id, AUDIT_CHECK) == 1

    def test_anonymous_usage_does_not_follow_the_account(self, store, session):
        session_auth.consume(AUDIT_CHECK)
        user = register(store, "chris@example.com", "password123", with_trial=False)
        session_auth.sign_in(user)
        assert session_auth.entitlement(AUDIT_CHECK).used == 0

    def test_premium_features_unlock(self, store):
        user = register(store, "chris@example.com", "password123", with_trial=False)
        session_auth.sign_in(set_tier(store, user, Tier.PREMIUM))
        assert session_auth.entitlement(NOTION_TEMPLATE).allowed

    def test_unlimited_plans_are_not_metered(self, store):
        user = register(store, "chris@example.com", "password123", with_trial=False)
        session_auth.sign_in(set_tier(store, user, Tier.PREMIUM))
        assert session_auth.consume(AUDIT_CHECK).limit == UNLIMITED
        assert store.usage_count(user.id, AUDIT_CHECK) == 0

    def test_quota_exhaustion_raises(self, store):
        user = register(store, "chris@example.com", "password123", with_trial=False)
        session_auth.sign_in(user)
        for _ in range(3):
            session_auth.consume(AUDIT_CHECK)
        with pytest.raises(AccountError):
            session_auth.consume(AUDIT_CHECK)
