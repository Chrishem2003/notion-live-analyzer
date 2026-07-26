"""Tests for modules.notion_template — one duplication link per Premium account."""
import pytest

from modules.accounts import AccountError, SQLiteAccountStore, Tier, register, set_tier
from modules.notion_template import claim, redeem, reset_claim, template_configured, template_url

TEMPLATE = "https://www.notion.so/chrishem/research-suite-abc123"


@pytest.fixture()
def store(tmp_path):
    return SQLiteAccountStore(tmp_path / "accounts.db")


@pytest.fixture()
def premium(store):
    user = register(store, "premium@example.com", "password123", with_trial=False)
    return set_tier(store, user, Tier.PREMIUM)


@pytest.fixture(autouse=True)
def configured_template(monkeypatch):
    monkeypatch.setenv("NOTION_TEMPLATE_URL", TEMPLATE)


class TestConfiguration:
    def test_reads_the_url_from_the_environment(self):
        assert template_url() == TEMPLATE
        assert template_configured() is True

    def test_unset_url_is_reported(self, monkeypatch):
        monkeypatch.delenv("NOTION_TEMPLATE_URL", raising=False)
        assert template_url() is None
        assert template_configured() is False


class TestClaim:
    def test_premium_user_gets_a_tokenised_link(self, store, premium):
        granted = claim(store, premium)
        assert granted.url.startswith(TEMPLATE)
        assert f"claim={granted.token}" in granted.url

    def test_query_separator_is_chosen_correctly(self, store, premium, monkeypatch):
        monkeypatch.setenv("NOTION_TEMPLATE_URL", f"{TEMPLATE}?v=1")
        assert "?v=1&claim=" in claim(store, premium).url

    def test_claiming_marks_the_account(self, store, premium):
        claim(store, premium)
        assert store.get_user(premium.id).notion_template_claimed is True

    def test_second_claim_is_refused(self, store, premium):
        claim(store, premium)
        with pytest.raises(AccountError, match="already claimed"):
            claim(store, store.get_user(premium.id))

    def test_free_users_cannot_claim(self, store):
        user = register(store, "free@example.com", "password123", with_trial=False)
        with pytest.raises(AccountError, match="Premium"):
            claim(store, user)

    def test_trial_users_cannot_claim(self, store):
        user = register(store, "trial@example.com", "password123")
        with pytest.raises(AccountError):
            claim(store, user)

    def test_unconfigured_template_fails_clearly(self, store, premium, monkeypatch):
        monkeypatch.delenv("NOTION_TEMPLATE_URL", raising=False)
        with pytest.raises(AccountError, match="NOTION_TEMPLATE_URL"):
            claim(store, premium)

    def test_a_failed_claim_does_not_burn_the_entitlement(self, store, premium, monkeypatch):
        monkeypatch.delenv("NOTION_TEMPLATE_URL", raising=False)
        with pytest.raises(AccountError):
            claim(store, premium)
        assert store.get_user(premium.id).notion_template_claimed is False


class TestRedeem:
    def test_token_resolves_to_its_owner(self, store, premium):
        granted = claim(store, premium)
        assert redeem(store, granted.token).id == premium.id

    def test_token_works_only_once(self, store, premium):
        granted = claim(store, premium)
        redeem(store, granted.token)
        assert redeem(store, granted.token) is None

    def test_unknown_token_is_rejected(self, store):
        assert redeem(store, "not-a-token") is None


class TestReset:
    def test_admin_can_allow_a_second_claim(self, store, premium):
        claim(store, premium)
        reset_claim(store, store.get_user(premium.id))
        assert claim(store, store.get_user(premium.id)).token
