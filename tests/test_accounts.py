"""Tests for modules.accounts — hashing, tiers, store CRUD, quotas, claims."""
from datetime import timedelta

import pytest

from modules import accounts
from modules.accounts import (
    AccountError,
    SQLiteAccountStore,
    Tier,
    User,
    authenticate,
    billing_period,
    extend_trial,
    hash_password,
    normalize_email,
    register,
    set_tier,
    suspend,
    utcnow,
    verify_password,
)


@pytest.fixture()
def store(tmp_path):
    return SQLiteAccountStore(tmp_path / "accounts.db")


# ═══════════════════════════════════════════════════════════════════════
class TestPasswordHashing:
    def test_hash_is_not_the_password(self):
        encoded = hash_password("correct horse battery")
        assert "correct horse battery" not in encoded
        assert encoded.startswith("pbkdf2_sha256$")

    def test_same_password_hashes_differently(self):
        assert hash_password("hunter22") != hash_password("hunter22")

    def test_verify_accepts_the_right_password(self):
        assert verify_password("hunter22", hash_password("hunter22"))

    def test_verify_rejects_the_wrong_password(self):
        assert not verify_password("hunter23", hash_password("hunter22"))

    def test_verify_rejects_malformed_hashes(self):
        assert not verify_password("x", "not-a-hash")
        assert not verify_password("x", "")
        assert not verify_password("x", None)

    def test_verify_rejects_unknown_algorithm(self):
        encoded = hash_password("hunter22").replace("pbkdf2_sha256", "md5")
        assert not verify_password("hunter22", encoded)

    def test_empty_password_is_rejected(self):
        with pytest.raises(ValueError):
            hash_password("")


class TestTier:
    def test_from_string_is_forgiving(self):
        assert Tier.from_string("PREMIUM") is Tier.PREMIUM
        assert Tier.from_string(" standard ") is Tier.STANDARD

    def test_unknown_values_fall_back_to_free(self):
        assert Tier.from_string("platinum") is Tier.FREE
        assert Tier.from_string(None) is Tier.FREE

    def test_covers_is_ordered(self):
        assert Tier.PREMIUM.covers(Tier.STANDARD)
        assert Tier.STANDARD.covers(Tier.STANDARD)
        assert not Tier.FREE.covers(Tier.STANDARD)


class TestEffectiveTier:
    def test_free_user_stays_free(self):
        assert User(id="1", email="a@b.c").effective_tier() is Tier.FREE

    def test_active_trial_grants_standard(self):
        user = User(id="1", email="a@b.c", trial_ends_at=utcnow() + timedelta(days=3))
        assert user.effective_tier() is Tier.STANDARD
        assert user.trial_days_left() == 3

    def test_expired_trial_reverts_to_free(self):
        user = User(id="1", email="a@b.c", trial_ends_at=utcnow() - timedelta(days=1))
        assert user.effective_tier() is Tier.FREE
        assert user.trial_days_left() == 0

    def test_trial_never_downgrades_a_paying_user(self):
        user = User(
            id="1",
            email="a@b.c",
            tier=Tier.PREMIUM,
            trial_ends_at=utcnow() + timedelta(days=3),
            subscription_ends_at=utcnow() + timedelta(days=20),
        )
        assert user.effective_tier() is Tier.PREMIUM

    def test_lapsed_subscription_reverts_to_free(self):
        user = User(
            id="1",
            email="a@b.c",
            tier=Tier.PREMIUM,
            subscription_ends_at=utcnow() - timedelta(days=1),
        )
        assert user.effective_tier() is Tier.FREE

    def test_paid_tier_without_end_date_persists(self):
        user = User(id="1", email="a@b.c", tier=Tier.PREMIUM)
        assert user.effective_tier() is Tier.PREMIUM

    def test_suspension_removes_all_entitlements(self):
        user = User(
            id="1",
            email="a@b.c",
            tier=Tier.PREMIUM,
            trial_ends_at=utcnow() + timedelta(days=5),
            is_suspended=True,
        )
        assert user.effective_tier() is Tier.FREE


class TestSQLiteStore:
    def test_round_trips_a_user(self, store):
        created = store.create_user("Chris@Example.COM", "password123")
        fetched = store.get_user(created.id)
        assert fetched.email == "chris@example.com"
        assert verify_password("password123", fetched.password_hash)

    def test_lookup_by_email_is_case_insensitive(self, store):
        store.create_user("chris@example.com", "password123")
        assert store.get_user_by_email("CHRIS@example.com") is not None

    def test_duplicate_email_is_rejected(self, store):
        store.create_user("chris@example.com", "password123")
        with pytest.raises(AccountError):
            store.create_user("chris@example.com", "otherpassword")

    def test_missing_user_is_none(self, store):
        assert store.get_user("nope") is None
        assert store.get_user_by_email("nobody@example.com") is None

    def test_save_persists_every_field(self, store):
        user = store.create_user("chris@example.com", "password123")
        user.tier = Tier.PREMIUM
        user.country = "UG"
        user.student_verified = True
        user.notion_template_claimed = True
        store.save_user(user)

        reloaded = store.get_user(user.id)
        assert reloaded.tier is Tier.PREMIUM
        assert reloaded.country == "UG"
        assert reloaded.student_verified is True
        assert reloaded.notion_template_claimed is True

    def test_list_users_returns_everyone(self, store):
        store.create_user("a@example.com", "password123")
        store.create_user("b@example.com", "password123")
        assert len(store.list_users()) == 2

    def test_delete_removes_the_user(self, store):
        user = store.create_user("a@example.com", "password123")
        assert store.delete_user(user.id) is True
        assert store.get_user(user.id) is None
        assert store.delete_user(user.id) is False

    def test_timestamps_survive_the_round_trip(self, store):
        user = store.create_user("a@example.com", "password123")
        trial = utcnow() + timedelta(days=15)
        user.trial_ends_at = trial
        store.save_user(user)
        assert abs((store.get_user(user.id).trial_ends_at - trial).total_seconds()) < 1


class TestUsageMetering:
    def test_counts_start_at_zero(self, store):
        assert store.usage_count("u1", "audit_check") == 0

    def test_recording_increments_the_count(self, store):
        store.record_usage("u1", "audit_check")
        store.record_usage("u1", "audit_check")
        assert store.usage_count("u1", "audit_check") == 2

    def test_features_are_counted_separately(self, store):
        store.record_usage("u1", "audit_check")
        assert store.usage_count("u1", "deep_analysis") == 0

    def test_users_are_counted_separately(self, store):
        store.record_usage("u1", "audit_check")
        assert store.usage_count("u2", "audit_check") == 0

    def test_quota_resets_next_month(self, store):
        now = utcnow()
        store.record_usage("u1", "audit_check", now)
        next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        assert store.usage_count("u1", "audit_check", next_month) == 0

    def test_billing_period_is_the_calendar_month(self):
        assert billing_period(utcnow()) == utcnow().strftime("%Y-%m")


class TestTemplateClaims:
    def test_token_redeems_once(self, store):
        token = store.issue_template_token("u1")
        assert store.redeem_template_token(token) == "u1"
        assert store.redeem_template_token(token) is None

    def test_unknown_token_is_rejected(self, store):
        assert store.redeem_template_token("made-up") is None

    def test_expired_token_is_rejected(self, store):
        token = store.issue_template_token("u1", ttl_hours=1)
        assert store.redeem_template_token(token, utcnow() + timedelta(hours=2)) is None

    def test_tokens_are_unique(self, store):
        assert store.issue_template_token("u1") != store.issue_template_token("u1")


class TestDiscountCodeStorage:
    def _code(self, code="LAUNCH50"):
        return {
            "code": code,
            "percent_off": 50,
            "grants_tier": None,
            "grants_days": None,
            "max_redemptions": 2,
            "redemptions": 0,
            "expires_at": None,
            "created_at": utcnow().isoformat(),
        }

    def test_create_and_read(self, store):
        store.create_discount_code(self._code())
        assert store.get_discount_code("launch50")["percent_off"] == 50

    def test_increment_redemptions(self, store):
        store.create_discount_code(self._code())
        store.increment_discount_redemptions("LAUNCH50")
        assert store.get_discount_code("LAUNCH50")["redemptions"] == 1

    def test_delete(self, store):
        store.create_discount_code(self._code())
        assert store.delete_discount_code("LAUNCH50") is True
        assert store.get_discount_code("LAUNCH50") is None

    def test_list(self, store):
        store.create_discount_code(self._code("A1"))
        store.create_discount_code(self._code("B2"))
        assert {row["code"] for row in store.list_discount_codes()} == {"A1", "B2"}


class TestRegistration:
    def test_register_starts_a_trial(self, store, monkeypatch):
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        user = register(store, "chris@example.com", "password123")
        assert user.trial_active()
        assert user.trial_days_left() == accounts.TRIAL_DAYS
        assert user.is_admin is False

    def test_trial_can_be_skipped(self, store):
        user = register(store, "chris@example.com", "password123", with_trial=False)
        assert user.trial_ends_at is None

    def test_short_passwords_are_rejected(self, store):
        with pytest.raises(AccountError):
            register(store, "chris@example.com", "short")

    def test_invalid_email_is_rejected(self, store):
        with pytest.raises(AccountError):
            register(store, "not-an-email", "password123")

    def test_admin_emails_are_promoted(self, store, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", "boss@example.com, chris@example.com")
        assert register(store, "Chris@example.com", "password123").is_admin is True

    def test_non_admin_emails_are_not_promoted(self, store, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", "boss@example.com")
        assert register(store, "chris@example.com", "password123").is_admin is False


class TestAuthentication:
    def test_valid_credentials_return_the_user(self, store):
        register(store, "chris@example.com", "password123")
        assert authenticate(store, "chris@example.com", "password123").email == "chris@example.com"

    def test_wrong_password_is_rejected(self, store):
        register(store, "chris@example.com", "password123")
        with pytest.raises(AccountError):
            authenticate(store, "chris@example.com", "wrong-password")

    def test_unknown_email_is_rejected(self, store):
        with pytest.raises(AccountError):
            authenticate(store, "nobody@example.com", "password123")

    def test_unknown_email_and_wrong_password_report_the_same_error(self, store):
        register(store, "chris@example.com", "password123")
        with pytest.raises(AccountError) as unknown:
            authenticate(store, "nobody@example.com", "password123")
        with pytest.raises(AccountError) as wrong:
            authenticate(store, "chris@example.com", "nope-nope-nope")
        assert str(unknown.value) == str(wrong.value)

    def test_suspended_accounts_cannot_sign_in(self, store):
        user = register(store, "chris@example.com", "password123")
        suspend(store, user)
        with pytest.raises(AccountError, match="suspended"):
            authenticate(store, "chris@example.com", "password123")


class TestTierManagement:
    def test_set_tier_without_days_has_no_expiry(self, store):
        user = register(store, "chris@example.com", "password123")
        updated = set_tier(store, user, Tier.PREMIUM)
        assert updated.tier is Tier.PREMIUM
        assert updated.subscription_ends_at is None

    def test_set_tier_with_days_sets_an_end_date(self, store):
        user = register(store, "chris@example.com", "password123")
        updated = set_tier(store, user, Tier.PREMIUM, days=30)
        assert updated.subscription_active()
        assert 29 <= (updated.subscription_ends_at - utcnow()).days <= 30

    def test_extend_trial_adds_to_an_active_trial(self, store):
        user = register(store, "chris@example.com", "password123")
        original = user.trial_ends_at
        extended = extend_trial(store, user, 10)
        assert (extended.trial_ends_at - original).days == 10

    def test_extend_trial_restarts_a_lapsed_trial_from_today(self, store):
        user = register(store, "chris@example.com", "password123")
        user.trial_ends_at = utcnow() - timedelta(days=30)
        store.save_user(user)
        extended = extend_trial(store, user, 10)
        assert extended.trial_active()
        assert extended.trial_days_left() == 10

    def test_suspend_and_reinstate(self, store):
        user = register(store, "chris@example.com", "password123")
        assert suspend(store, user).is_suspended is True
        assert suspend(store, user, False).is_suspended is False


class TestHelpers:
    def test_normalize_email(self):
        assert normalize_email("  Chris@Example.COM ") == "chris@example.com"
        assert normalize_email(None) == ""

    def test_get_store_defaults_to_sqlite(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
        monkeypatch.setenv("ACCOUNTS_DB_PATH", str(tmp_path / "a.db"))
        assert accounts.get_store().backend == "sqlite"

    def test_storage_is_durable_only_with_supabase(self, monkeypatch):
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        assert accounts.storage_is_durable() is False
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
        assert accounts.storage_is_durable() is True
