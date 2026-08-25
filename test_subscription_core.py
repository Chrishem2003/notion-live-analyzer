"""Unit tests for modules.subscription_core pure-logic functions."""
import pytest
from datetime import datetime, timedelta, timezone

from modules.subscription_core import (
    TRIAL_LENGTH_DAYS,
    Role,
    SubStatus,
    User,
    Subscription,
    start_trial,
    activate_subscription,
    has_access,
    needs_payment,
    days_left_in_trial,
)


class TestStartTrial:
    def test_creates_trial_subscription(self):
        sub = start_trial("user_1")
        assert sub.user_id == "user_1"
        assert sub.status == SubStatus.TRIAL
        assert sub.trial_ends_at > sub.trial_started_at
        assert (sub.trial_ends_at - sub.trial_started_at).days == TRIAL_LENGTH_DAYS


class TestActivateSubscription:
    def test_creates_active_subscription(self):
        sub = activate_subscription("user_1", provider_customer_id="cus_123")
        assert sub.user_id == "user_1"
        assert sub.status == SubStatus.ACTIVE
        assert sub.provider_customer_id == "cus_123"

    def test_preserves_provided_dates(self):
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)
        sub = activate_subscription("u1", trial_started_at=now, current_period_end=period_end)
        assert sub.trial_started_at == now
        assert sub.current_period_end == period_end


class TestHasAccess:
    def test_active_subscription_grants_access(self):
        sub = activate_subscription("u1")
        assert has_access(sub) is True

    def test_trial_not_expired_grants_access(self):
        sub = start_trial("u1")
        assert has_access(sub) is True

    def test_expired_trial_denies_access(self):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        sub = Subscription(
            user_id="u1",
            status=SubStatus.TRIAL,
            trial_started_at=past - timedelta(days=TRIAL_LENGTH_DAYS),
            trial_ends_at=past,
        )
        assert has_access(sub) is False

    def test_expired_status_denies(self):
        sub = Subscription(
            user_id="u1", status=SubStatus.EXPIRED,
            trial_started_at=datetime.now(timezone.utc) - timedelta(days=20),
            trial_ends_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        assert has_access(sub) is False

    def test_canceled_status_denies(self):
        sub = Subscription(
            user_id="u1", status=SubStatus.CANCELED,
            trial_started_at=datetime.now(timezone.utc),
            trial_ends_at=datetime.now(timezone.utc) + timedelta(days=10),
        )
        # Canceled means no access even if trial hasn't technically ended
        assert has_access(sub) is False

    def test_none_subscription_denies(self):
        assert has_access(None) is False


class TestNeedsPayment:
    def test_needs_payment_when_no_access(self):
        assert needs_payment(None) is True

    def test_no_payment_needed_when_active(self):
        sub = activate_subscription("u1")
        assert needs_payment(sub) is False

    def test_no_payment_needed_during_trial(self):
        sub = start_trial("u1")
        assert needs_payment(sub) is False


class TestDaysLeftInTrial:
    def test_active_trial_returns_positive(self):
        sub = start_trial("u1")
        assert days_left_in_trial(sub) >= 5  # at least 5 days remain in 15-day trial

    def test_expired_trial_returns_zero(self):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        sub = Subscription(
            user_id="u1", status=SubStatus.TRIAL,
            trial_started_at=past - timedelta(days=TRIAL_LENGTH_DAYS),
            trial_ends_at=past,
        )
        assert days_left_in_trial(sub) == 0

    def test_active_subscription_returns_zero(self):
        sub = activate_subscription("u1")
        assert days_left_in_trial(sub) == 0

    def test_none_subscription_returns_zero(self):
        assert days_left_in_trial(None) == 0


class TestEnumValues:
    def test_roles(self):
        assert Role.USER.value == "user"
        assert Role.ADMIN.value == "admin"

    def test_statuses(self):
        assert SubStatus.TRIAL.value == "trial"
        assert SubStatus.ACTIVE.value == "active"
        assert SubStatus.EXPIRED.value == "expired"
        assert SubStatus.CANCELED.value == "canceled"
