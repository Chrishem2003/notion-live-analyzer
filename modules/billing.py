"""Subscription plans, entitlement checks, discount codes and Stripe glue.

The plan matrix below is the single source of truth: the pricing page, the
feature gates and the admin console all read it, so a tier change is one edit.

Stripe is optional. Without ``STRIPE_SECRET_KEY`` the checkout helpers report
that billing is unconfigured instead of failing, which keeps the app usable for
self-hosted and trial users. Webhook signatures are verified with stdlib
``hmac`` — the Stripe SDK is not a dependency.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from modules.accounts import (
    AccountError,
    SQLiteAccountStore,
    Tier,
    User,
    billing_period,
    set_tier,
    utcnow,
)

UNLIMITED = -1


@dataclass(frozen=True)
class Plan:
    tier: Tier
    name: str
    price_usd: float
    tagline: str
    quotas: Dict[str, int]
    features: Tuple[str, ...]
    highlights: Tuple[str, ...]

    def quota(self, feature: str) -> int:
        """Monthly allowance for a metered feature (UNLIMITED for no cap)."""
        return self.quotas.get(feature, 0)


# ─── Metered features ─────────────────────────────────────────────────
AUDIT_CHECK = "audit_check"
DEEP_ANALYSIS = "deep_analysis"
EMAIL_REPORT = "email_report"

# ─── Boolean capabilities ─────────────────────────────────────────────
ADVANCED_FILTERING = "advanced_filtering"
MULTI_PAPER_SYNTHESIS = "multi_paper_synthesis"
NOTION_TEMPLATE = "notion_template"
PROFESSOR_SUITE = "professor_suite"
WEBHOOKS = "webhooks"
FULL_INTEGRATIONS = "full_integrations"
EXPORT_PDF = "export_pdf"
EXPORT_WORD = "export_word"
EXPORT_BIBTEX = "export_bibtex"
EXPORT_LATEX = "export_latex"
AUTOMATED_EMAIL_REPORTS = "automated_email_reports"

FEATURE_LABELS = {
    AUDIT_CHECK: "Audit & similarity checks",
    DEEP_ANALYSIS: "Deep literature analysis",
    EMAIL_REPORT: "Emailed audit reports",
    ADVANCED_FILTERING: "Advanced literature filtering",
    MULTI_PAPER_SYNTHESIS: "Multi-paper synthesis",
    NOTION_TEMPLATE: "Notion workspace template",
    PROFESSOR_SUITE: "Password-protected professor suite",
    WEBHOOKS: "Webhook automations",
    FULL_INTEGRATIONS: "Zapier, Zotero & Notion sync",
    EXPORT_PDF: "PDF export",
    EXPORT_WORD: "Word export",
    EXPORT_BIBTEX: "BibTeX export",
    EXPORT_LATEX: "LaTeX / Overleaf export",
    AUTOMATED_EMAIL_REPORTS: "Automated email reports",
}

PLANS: Dict[Tier, Plan] = {
    Tier.FREE: Plan(
        tier=Tier.FREE,
        name="Free",
        price_usd=0.0,
        tagline="Basic literature search and exports",
        quotas={AUDIT_CHECK: 3, DEEP_ANALYSIS: 5, EMAIL_REPORT: 0},
        features=(EXPORT_PDF,),
        highlights=(
            "Basic literature queries",
            "3 audit checks per month",
            "PDF & text export",
        ),
    ),
    Tier.STANDARD: Plan(
        tier=Tier.STANDARD,
        name="Standard",
        price_usd=9.0,
        tagline="Advanced filtering, deeper summaries, 15-day free trial",
        quotas={AUDIT_CHECK: 15, DEEP_ANALYSIS: 100, EMAIL_REPORT: 10},
        features=(ADVANCED_FILTERING, WEBHOOKS, EXPORT_PDF, EXPORT_WORD, EXPORT_BIBTEX),
        highlights=(
            "Advanced filtering + deep summaries",
            "15 audit checks per month",
            "PDF, Word & BibTeX export",
            "Limited webhook automations",
        ),
    ),
    Tier.PREMIUM: Plan(
        tier=Tier.PREMIUM,
        name="Premium",
        price_usd=29.0,
        tagline="Unlimited analysis, professor suite and the Notion template",
        quotas={AUDIT_CHECK: UNLIMITED, DEEP_ANALYSIS: UNLIMITED, EMAIL_REPORT: UNLIMITED},
        features=(
            ADVANCED_FILTERING,
            MULTI_PAPER_SYNTHESIS,
            NOTION_TEMPLATE,
            PROFESSOR_SUITE,
            WEBHOOKS,
            FULL_INTEGRATIONS,
            EXPORT_PDF,
            EXPORT_WORD,
            EXPORT_BIBTEX,
            EXPORT_LATEX,
            AUTOMATED_EMAIL_REPORTS,
        ),
        highlights=(
            "Unlimited deep analysis & multi-paper synthesis",
            "One-time Notion template duplication",
            "Professor-verified, password-protected review suite",
            "Zapier, Zotero & Notion sync",
            "Automated email reports + every export format",
        ),
    ),
}


def plan_for(tier: Tier) -> Plan:
    return PLANS[tier]


def plan_for_user(user: User, now: Optional[datetime] = None) -> Plan:
    return PLANS[user.effective_tier(now)]


# ═══════════════════════════════════════════════════════════════════════
# Entitlements
# ═══════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class Entitlement:
    allowed: bool
    reason: str = ""
    used: int = 0
    limit: int = 0
    required_tier: Optional[Tier] = None

    def __bool__(self) -> bool:
        return self.allowed

    @property
    def remaining(self) -> int:
        if self.limit == UNLIMITED:
            return UNLIMITED
        return max(0, self.limit - self.used)


def minimum_tier_for(feature: str) -> Tier:
    """Cheapest tier that includes a boolean feature or a non-zero quota."""
    for tier in (Tier.FREE, Tier.STANDARD, Tier.PREMIUM):
        plan = PLANS[tier]
        if feature in plan.features or plan.quota(feature) != 0:
            return tier
    return Tier.PREMIUM


def check_access(
    user: Optional[User],
    feature: str,
    store: Optional[SQLiteAccountStore] = None,
    now: Optional[datetime] = None,
) -> Entitlement:
    """Can this user use ``feature`` right now?

    Boolean features resolve from the plan's feature set; metered features also
    consult the store for this calendar month's usage.
    """
    now = now or utcnow()
    required = minimum_tier_for(feature)

    if user is None:
        return Entitlement(False, "Sign in to use this feature.", required_tier=required)
    if user.is_suspended:
        return Entitlement(False, "This account is suspended.", required_tier=required)

    plan = plan_for_user(user, now)
    limit = plan.quota(feature)

    if feature in plan.features and limit == 0:
        return Entitlement(True, limit=UNLIMITED)

    if limit == 0:
        return Entitlement(
            False,
            f"{FEATURE_LABELS.get(feature, feature)} requires the "
            f"{PLANS[required].name} plan.",
            required_tier=required,
        )
    if limit == UNLIMITED:
        return Entitlement(True, limit=UNLIMITED)

    used = store.usage_count(user.id, feature, now) if store else 0
    if used >= limit:
        return Entitlement(
            False,
            f"You've used all {limit} {FEATURE_LABELS.get(feature, feature).lower()} "
            f"for {billing_period(now)}. Upgrade for more.",
            used=used,
            limit=limit,
            required_tier=Tier.PREMIUM if plan.tier is Tier.STANDARD else Tier.STANDARD,
        )
    return Entitlement(True, used=used, limit=limit)


def consume(
    store: SQLiteAccountStore,
    user: User,
    feature: str,
    now: Optional[datetime] = None,
) -> Entitlement:
    """Check then record one use. Raises :class:`AccountError` when blocked."""
    entitlement = check_access(user, feature, store, now)
    if not entitlement.allowed:
        raise AccountError(entitlement.reason)
    if entitlement.limit != UNLIMITED:
        store.record_usage(user.id, feature, now)
    return entitlement


def usage_summary(
    store: SQLiteAccountStore, user: User, now: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Per-metered-feature usage for the account page and admin console."""
    now = now or utcnow()
    plan = plan_for_user(user, now)
    rows = []
    for feature in (AUDIT_CHECK, DEEP_ANALYSIS, EMAIL_REPORT):
        limit = plan.quota(feature)
        used = store.usage_count(user.id, feature, now)
        rows.append(
            {
                "feature": FEATURE_LABELS[feature],
                "used": used,
                "limit": "Unlimited" if limit == UNLIMITED else limit,
                "remaining": "Unlimited" if limit == UNLIMITED else max(0, limit - used),
            }
        )
    return rows


# ═══════════════════════════════════════════════════════════════════════
# Discount codes
# ═══════════════════════════════════════════════════════════════════════
def create_discount_code(
    store: SQLiteAccountStore,
    code: str,
    percent_off: int = 0,
    grants_tier: Optional[Tier] = None,
    grants_days: Optional[int] = None,
    max_redemptions: int = 1,
    expires_at: Optional[datetime] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now or utcnow()
    normalized = (code or "").strip().upper()
    if not normalized:
        raise AccountError("Enter a code.")
    if not 0 <= percent_off <= 100:
        raise AccountError("Percent off must be between 0 and 100.")
    if store.get_discount_code(normalized):
        raise AccountError(f"Code {normalized} already exists.")

    payload = {
        "code": normalized,
        "percent_off": int(percent_off),
        "grants_tier": grants_tier.value if grants_tier else None,
        "grants_days": int(grants_days) if grants_days else None,
        "max_redemptions": int(max_redemptions),
        "redemptions": 0,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": now.isoformat(),
    }
    store.create_discount_code(payload)
    return payload


def redeem_discount_code(
    store: SQLiteAccountStore,
    user: User,
    code: str,
    now: Optional[datetime] = None,
) -> Tuple[User, str]:
    """Apply a code to an account. Returns the updated user and a message."""
    now = now or utcnow()
    record = store.get_discount_code(code or "")
    if record is None:
        raise AccountError("That code is not valid.")
    if record.get("expires_at"):
        expiry = datetime.fromisoformat(str(record["expires_at"]).replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=now.tzinfo)
        if expiry <= now:
            raise AccountError("That code has expired.")
    if int(record.get("redemptions", 0)) >= int(record.get("max_redemptions", 1)):
        raise AccountError("That code has already been fully redeemed.")

    store.increment_discount_redemptions(record["code"])

    if record.get("grants_tier"):
        granted = Tier.from_string(record["grants_tier"])
        days = record.get("grants_days") or 30
        user = set_tier(store, user, granted, days=int(days), now=now)
        return user, f"{record['code']} applied — {PLANS[granted].name} for {days} days."
    return user, f"{record['code']} applied — {record.get('percent_off', 0)}% off at checkout."


# ═══════════════════════════════════════════════════════════════════════
# Stripe
# ═══════════════════════════════════════════════════════════════════════
def stripe_configured() -> bool:
    return bool(os.environ.get("STRIPE_SECRET_KEY"))


def price_id_for(tier: Tier) -> Optional[str]:
    return os.environ.get(f"STRIPE_PRICE_{tier.value.upper()}")


def create_checkout_session(
    user: User,
    tier: Tier,
    success_url: str,
    cancel_url: str,
    discount_code: Optional[str] = None,
    session=None,
) -> Dict[str, Any]:
    """Create a Stripe Checkout session and return its ``url``.

    Uses the REST API directly (form-encoded, as Stripe expects) so the SDK is
    not a dependency.
    """
    if not stripe_configured():
        raise AccountError(
            "Billing is not configured. Set STRIPE_SECRET_KEY and the "
            "STRIPE_PRICE_* variables to enable checkout."
        )
    price_id = price_id_for(tier)
    if not price_id:
        raise AccountError(f"No Stripe price configured for the {tier.value} plan.")

    import requests

    payload = {
        "mode": "subscription",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": user.id,
        "customer_email": user.email,
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": 1,
        "metadata[user_id]": user.id,
        "metadata[tier]": tier.value,
    }
    if discount_code:
        payload["discounts[0][promotion_code]"] = discount_code

    http = session or requests
    response = http.post(
        "https://api.stripe.com/v1/checkout/sessions",
        data=payload,
        auth=(os.environ["STRIPE_SECRET_KEY"], ""),
        timeout=20,
    )
    if response.status_code >= 400:
        raise AccountError(f"Stripe checkout failed: {response.text[:200]}")
    return response.json()


def verify_webhook_signature(
    payload: bytes,
    signature_header: str,
    secret: str,
    tolerance_seconds: int = 300,
    now: Optional[float] = None,
) -> bool:
    """Validate a ``Stripe-Signature`` header (scheme v1, HMAC-SHA256)."""
    if not (payload and signature_header and secret):
        return False

    parts = dict(
        item.split("=", 1) for item in signature_header.split(",") if "=" in item
    )
    timestamp = parts.get("t")
    provided = parts.get("v1")
    if not timestamp or not provided:
        return False

    now = time.time() if now is None else now
    try:
        if abs(now - int(timestamp)) > tolerance_seconds:
            return False
    except ValueError:
        return False

    expected = hmac.new(
        secret.encode(),
        f"{timestamp}.".encode() + payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, provided)


def apply_webhook_event(
    store: SQLiteAccountStore, event: Dict[str, Any], now: Optional[datetime] = None
) -> Optional[User]:
    """Move an account between tiers in response to a Stripe event.

    Handles the four events that change entitlement:
    ``checkout.session.completed``, ``customer.subscription.updated``,
    ``customer.subscription.deleted`` and ``invoice.payment_failed``.
    """
    now = now or utcnow()
    event_type = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}
    metadata = obj.get("metadata") or {}

    user_id = metadata.get("user_id") or obj.get("client_reference_id")
    user = store.get_user(user_id) if user_id else None
    if user is None:
        email = obj.get("customer_email") or (obj.get("customer_details") or {}).get("email")
        user = store.get_user_by_email(email) if email else None
    if user is None:
        return None

    if event_type in ("checkout.session.completed", "customer.subscription.updated"):
        tier = Tier.from_string(metadata.get("tier") or Tier.STANDARD.value)
        period_end = obj.get("current_period_end")
        if period_end:
            days = max(1, int((datetime.fromtimestamp(int(period_end), now.tzinfo) - now).days))
        else:
            days = 31
        user = set_tier(store, user, tier, days=days, now=now)
        if obj.get("customer"):
            user.stripe_customer_id = str(obj["customer"])
            store.save_user(user)
        return user

    if event_type in ("customer.subscription.deleted", "invoice.payment_failed"):
        # Keep access until the paid period ends rather than cutting off mid-cycle.
        grace = now + timedelta(days=1) if event_type == "invoice.payment_failed" else now
        user.subscription_ends_at = grace
        return store.save_user(user)

    return None
