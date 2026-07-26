"""Tests for modules.billing — plan matrix, gating, quotas, codes, Stripe."""
import hashlib
import hmac
import json
import time
from datetime import timedelta

import pytest

from modules.accounts import AccountError, SQLiteAccountStore, Tier, register, set_tier, utcnow
from modules.billing import (
    ADVANCED_FILTERING,
    AUDIT_CHECK,
    EMAIL_REPORT,
    EXPORT_PDF,
    MULTI_PAPER_SYNTHESIS,
    NOTION_TEMPLATE,
    PLANS,
    UNLIMITED,
    apply_webhook_event,
    check_access,
    consume,
    create_checkout_session,
    create_discount_code,
    minimum_tier_for,
    plan_for_user,
    price_id_for,
    redeem_discount_code,
    stripe_configured,
    usage_summary,
    verify_webhook_signature,
)


@pytest.fixture()
def store(tmp_path):
    return SQLiteAccountStore(tmp_path / "accounts.db")


@pytest.fixture()
def free_user(store):
    return register(store, "free@example.com", "password123", with_trial=False)


# ═══════════════════════════════════════════════════════════════════════
class TestPlanMatrix:
    def test_every_tier_has_a_plan(self):
        assert set(PLANS) == set(Tier)

    def test_prices_increase_with_tier(self):
        assert PLANS[Tier.FREE].price_usd < PLANS[Tier.STANDARD].price_usd
        assert PLANS[Tier.STANDARD].price_usd < PLANS[Tier.PREMIUM].price_usd

    def test_audit_quota_increases_with_tier(self):
        assert PLANS[Tier.FREE].quota(AUDIT_CHECK) == 3
        assert PLANS[Tier.STANDARD].quota(AUDIT_CHECK) == 15
        assert PLANS[Tier.PREMIUM].quota(AUDIT_CHECK) == UNLIMITED

    def test_premium_features_are_premium_only(self):
        for feature in (NOTION_TEMPLATE, MULTI_PAPER_SYNTHESIS):
            assert feature in PLANS[Tier.PREMIUM].features
            assert feature not in PLANS[Tier.STANDARD].features
            assert feature not in PLANS[Tier.FREE].features

    def test_unknown_feature_has_no_quota(self):
        assert PLANS[Tier.PREMIUM].quota("teleportation") == 0

    def test_minimum_tier_for_boolean_features(self):
        assert minimum_tier_for(EXPORT_PDF) is Tier.FREE
        assert minimum_tier_for(ADVANCED_FILTERING) is Tier.STANDARD
        assert minimum_tier_for(NOTION_TEMPLATE) is Tier.PREMIUM

    def test_minimum_tier_for_metered_features(self):
        assert minimum_tier_for(AUDIT_CHECK) is Tier.FREE
        assert minimum_tier_for(EMAIL_REPORT) is Tier.STANDARD

    def test_plan_for_user_follows_the_effective_tier(self, store, free_user):
        assert plan_for_user(free_user).tier is Tier.FREE
        upgraded = set_tier(store, free_user, Tier.PREMIUM)
        assert plan_for_user(upgraded).tier is Tier.PREMIUM


class TestAccessChecks:
    def test_anonymous_visitors_are_asked_to_sign_in(self, store):
        result = check_access(None, AUDIT_CHECK, store)
        assert not result
        assert "Sign in" in result.reason

    def test_free_feature_is_allowed(self, store, free_user):
        assert check_access(free_user, EXPORT_PDF, store)

    def test_premium_feature_is_blocked_on_free(self, store, free_user):
        result = check_access(free_user, NOTION_TEMPLATE, store)
        assert not result
        assert result.required_tier is Tier.PREMIUM
        assert "Premium" in result.reason

    def test_premium_feature_is_allowed_on_premium(self, store, free_user):
        premium = set_tier(store, free_user, Tier.PREMIUM)
        assert check_access(premium, NOTION_TEMPLATE, store)

    def test_trial_unlocks_standard_features(self, store):
        user = register(store, "trial@example.com", "password123")
        assert check_access(user, ADVANCED_FILTERING, store)

    def test_expired_trial_relocks_standard_features(self, store):
        user = register(store, "trial@example.com", "password123")
        user.trial_ends_at = utcnow() - timedelta(days=1)
        store.save_user(user)
        assert not check_access(user, ADVANCED_FILTERING, store)

    def test_suspended_accounts_are_blocked(self, store, free_user):
        free_user.is_suspended = True
        store.save_user(free_user)
        assert not check_access(free_user, EXPORT_PDF, store)

    def test_quota_is_reported(self, store, free_user):
        result = check_access(free_user, AUDIT_CHECK, store)
        assert (result.limit, result.used, result.remaining) == (3, 0, 3)

    def test_unlimited_quota_reports_unlimited_remaining(self, store, free_user):
        premium = set_tier(store, free_user, Tier.PREMIUM)
        assert check_access(premium, AUDIT_CHECK, store).remaining == UNLIMITED

    def test_quota_exhaustion_blocks_access(self, store, free_user):
        for _ in range(3):
            store.record_usage(free_user.id, AUDIT_CHECK)
        result = check_access(free_user, AUDIT_CHECK, store)
        assert not result
        assert "used all 3" in result.reason

    def test_quota_resets_next_month(self, store, free_user):
        for _ in range(3):
            store.record_usage(free_user.id, AUDIT_CHECK)
        next_month = (utcnow().replace(day=1) + timedelta(days=32)).replace(day=1)
        assert check_access(free_user, AUDIT_CHECK, store, next_month)


class TestConsume:
    def test_consume_records_usage(self, store, free_user):
        consume(store, free_user, AUDIT_CHECK)
        assert store.usage_count(free_user.id, AUDIT_CHECK) == 1

    def test_consume_raises_once_the_quota_is_gone(self, store, free_user):
        for _ in range(3):
            consume(store, free_user, AUDIT_CHECK)
        with pytest.raises(AccountError):
            consume(store, free_user, AUDIT_CHECK)

    def test_unlimited_features_are_not_metered(self, store, free_user):
        premium = set_tier(store, free_user, Tier.PREMIUM)
        consume(store, premium, AUDIT_CHECK)
        assert store.usage_count(premium.id, AUDIT_CHECK) == 0

    def test_blocked_features_are_not_recorded(self, store, free_user):
        with pytest.raises(AccountError):
            consume(store, free_user, EMAIL_REPORT)
        assert store.usage_count(free_user.id, EMAIL_REPORT) == 0

    def test_usage_summary_covers_metered_features(self, store, free_user):
        consume(store, free_user, AUDIT_CHECK)
        rows = usage_summary(store, free_user)
        audit_row = next(row for row in rows if "Audit" in row["feature"])
        assert (audit_row["used"], audit_row["limit"], audit_row["remaining"]) == (1, 3, 2)

    def test_usage_summary_marks_unlimited_plans(self, store, free_user):
        premium = set_tier(store, free_user, Tier.PREMIUM)
        assert all(row["limit"] == "Unlimited" for row in usage_summary(store, premium))


class TestDiscountCodes:
    def test_create_normalizes_the_code(self, store):
        assert create_discount_code(store, " launch50 ", percent_off=50)["code"] == "LAUNCH50"

    def test_duplicate_codes_are_rejected(self, store):
        create_discount_code(store, "LAUNCH50", percent_off=50)
        with pytest.raises(AccountError):
            create_discount_code(store, "launch50", percent_off=10)

    def test_empty_code_is_rejected(self, store):
        with pytest.raises(AccountError):
            create_discount_code(store, "  ")

    def test_out_of_range_percentage_is_rejected(self, store):
        with pytest.raises(AccountError):
            create_discount_code(store, "BAD", percent_off=150)

    def test_redeeming_a_granting_code_upgrades_the_user(self, store, free_user):
        create_discount_code(
            store, "STUDENT", grants_tier=Tier.PREMIUM, grants_days=60, max_redemptions=5
        )
        user, message = redeem_discount_code(store, free_user, "student")
        assert user.tier is Tier.PREMIUM
        assert user.subscription_active()
        assert "Premium" in message

    def test_redeeming_a_percentage_code_leaves_the_tier_alone(self, store, free_user):
        create_discount_code(store, "HALF", percent_off=50)
        user, message = redeem_discount_code(store, free_user, "HALF")
        assert user.tier is Tier.FREE
        assert "50% off" in message

    def test_unknown_code_is_rejected(self, store, free_user):
        with pytest.raises(AccountError, match="not valid"):
            redeem_discount_code(store, free_user, "MADEUP")

    def test_exhausted_code_is_rejected(self, store, free_user):
        create_discount_code(store, "ONCE", percent_off=10, max_redemptions=1)
        redeem_discount_code(store, free_user, "ONCE")
        with pytest.raises(AccountError, match="fully redeemed"):
            redeem_discount_code(store, free_user, "ONCE")

    def test_multi_use_code_allows_several_redemptions(self, store, free_user):
        create_discount_code(store, "MANY", percent_off=10, max_redemptions=3)
        for _ in range(3):
            redeem_discount_code(store, free_user, "MANY")
        with pytest.raises(AccountError):
            redeem_discount_code(store, free_user, "MANY")

    def test_expired_code_is_rejected(self, store, free_user):
        create_discount_code(
            store, "OLD", percent_off=10, expires_at=utcnow() - timedelta(days=1)
        )
        with pytest.raises(AccountError, match="expired"):
            redeem_discount_code(store, free_user, "OLD")


class TestStripeConfiguration:
    def test_not_configured_without_a_key(self, monkeypatch):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        assert stripe_configured() is False

    def test_configured_with_a_key(self, monkeypatch):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
        assert stripe_configured() is True

    def test_price_ids_come_from_the_environment(self, monkeypatch):
        monkeypatch.setenv("STRIPE_PRICE_PREMIUM", "price_123")
        assert price_id_for(Tier.PREMIUM) == "price_123"
        monkeypatch.delenv("STRIPE_PRICE_STANDARD", raising=False)
        assert price_id_for(Tier.STANDARD) is None

    def test_checkout_fails_clearly_when_unconfigured(self, monkeypatch, free_user):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        with pytest.raises(AccountError, match="not configured"):
            create_checkout_session(free_user, Tier.PREMIUM, "https://x/ok", "https://x/no")

    def test_checkout_fails_without_a_price_id(self, monkeypatch, free_user):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
        monkeypatch.delenv("STRIPE_PRICE_PREMIUM", raising=False)
        with pytest.raises(AccountError, match="No Stripe price"):
            create_checkout_session(free_user, Tier.PREMIUM, "https://x/ok", "https://x/no")

    def test_checkout_posts_the_expected_payload(self, monkeypatch, free_user):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
        monkeypatch.setenv("STRIPE_PRICE_PREMIUM", "price_123")
        captured = {}

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {"url": "https://checkout.stripe.com/session"}

        class FakeSession:
            @staticmethod
            def post(url, data=None, auth=None, timeout=None):
                captured.update(url=url, data=data, auth=auth)
                return FakeResponse()

        result = create_checkout_session(
            free_user, Tier.PREMIUM, "https://x/ok", "https://x/no", session=FakeSession()
        )
        assert result["url"].startswith("https://checkout.stripe.com")
        assert captured["data"]["line_items[0][price]"] == "price_123"
        assert captured["data"]["client_reference_id"] == free_user.id
        assert captured["data"]["metadata[tier]"] == "premium"
        assert captured["auth"] == ("sk_test_x", "")

    def test_checkout_surfaces_stripe_errors(self, monkeypatch, free_user):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
        monkeypatch.setenv("STRIPE_PRICE_PREMIUM", "price_123")

        class FakeResponse:
            status_code = 402
            text = "card declined"

        class FakeSession:
            @staticmethod
            def post(*args, **kwargs):
                return FakeResponse()

        with pytest.raises(AccountError, match="card declined"):
            create_checkout_session(
                free_user, Tier.PREMIUM, "https://x/ok", "https://x/no", session=FakeSession()
            )


class TestWebhookSignature:
    SECRET = "whsec_test"

    def _sign(self, payload: bytes, timestamp: int, secret: str = SECRET) -> str:
        digest = hmac.new(
            secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
        ).hexdigest()
        return f"t={timestamp},v1={digest}"

    def test_valid_signature_passes(self):
        payload = b'{"id":"evt_1"}'
        now = int(time.time())
        assert verify_webhook_signature(payload, self._sign(payload, now), self.SECRET)

    def test_tampered_payload_fails(self):
        now = int(time.time())
        header = self._sign(b'{"id":"evt_1"}', now)
        assert not verify_webhook_signature(b'{"id":"evt_2"}', header, self.SECRET)

    def test_wrong_secret_fails(self):
        payload = b'{"id":"evt_1"}'
        now = int(time.time())
        assert not verify_webhook_signature(payload, self._sign(payload, now), "whsec_other")

    def test_stale_timestamp_fails(self):
        payload = b'{"id":"evt_1"}'
        old = int(time.time()) - 3600
        assert not verify_webhook_signature(payload, self._sign(payload, old), self.SECRET)

    def test_malformed_headers_fail(self):
        payload = b"{}"
        assert not verify_webhook_signature(payload, "garbage", self.SECRET)
        assert not verify_webhook_signature(payload, "t=abc,v1=def", self.SECRET)
        assert not verify_webhook_signature(payload, "", self.SECRET)

    def test_missing_inputs_fail(self):
        assert not verify_webhook_signature(b"", "t=1,v1=x", self.SECRET)
        assert not verify_webhook_signature(b"{}", "t=1,v1=x", "")


class TestWebhookEvents:
    def _event(self, event_type, **obj):
        return {"type": event_type, "data": {"object": obj}}

    def test_checkout_completed_upgrades_the_user(self, store, free_user):
        event = self._event(
            "checkout.session.completed",
            client_reference_id=free_user.id,
            metadata={"user_id": free_user.id, "tier": "premium"},
            customer="cus_123",
        )
        user = apply_webhook_event(store, event)
        assert user.tier is Tier.PREMIUM
        assert user.subscription_active()
        assert store.get_user(free_user.id).stripe_customer_id == "cus_123"

    def test_user_can_be_matched_by_email(self, store, free_user):
        event = self._event(
            "checkout.session.completed",
            customer_email=free_user.email,
            metadata={"tier": "standard"},
        )
        assert apply_webhook_event(store, event).tier is Tier.STANDARD

    def test_unknown_user_is_ignored(self, store):
        event = self._event("checkout.session.completed", metadata={"user_id": "nope"})
        assert apply_webhook_event(store, event) is None

    def test_unhandled_event_types_are_ignored(self, store, free_user):
        event = self._event("customer.created", metadata={"user_id": free_user.id})
        assert apply_webhook_event(store, event) is None

    def test_subscription_deleted_ends_access(self, store, free_user):
        premium = set_tier(store, free_user, Tier.PREMIUM, days=30)
        event = self._event(
            "customer.subscription.deleted", metadata={"user_id": premium.id}
        )
        user = apply_webhook_event(store, event)
        assert not user.subscription_active()
        assert user.effective_tier() is Tier.FREE

    def test_payment_failure_leaves_a_grace_day(self, store, free_user):
        premium = set_tier(store, free_user, Tier.PREMIUM, days=30)
        event = self._event("invoice.payment_failed", metadata={"user_id": premium.id})
        user = apply_webhook_event(store, event)
        assert user.subscription_active()
        assert (user.subscription_ends_at - utcnow()).days == 0

    def test_period_end_sets_the_renewal_date(self, store, free_user):
        period_end = int((utcnow() + timedelta(days=45)).timestamp())
        event = self._event(
            "customer.subscription.updated",
            metadata={"user_id": free_user.id, "tier": "standard"},
            current_period_end=period_end,
        )
        user = apply_webhook_event(store, event)
        assert 43 <= (user.subscription_ends_at - utcnow()).days <= 45

    def test_event_payload_round_trips_from_json(self, store, free_user):
        raw = json.dumps(
            self._event(
                "checkout.session.completed",
                metadata={"user_id": free_user.id, "tier": "premium"},
            )
        )
        assert apply_webhook_event(store, json.loads(raw)).tier is Tier.PREMIUM
