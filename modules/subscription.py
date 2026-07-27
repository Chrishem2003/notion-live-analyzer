"""Subscription Engine — Stripe Integration & Tier Management."""
import os
import hashlib
import hmac
import time
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from enum import Enum

import logging
import streamlit as st
import requests
import pandas as pd

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# TIER DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════

class Tier(Enum):
    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"

TIER_FEATURES = {
    Tier.FREE: {
        "literature_search": True,
        "limited_tools": True,
        "file_exports": False,
        "automation": False,
        "deep_research": False,
        "email_reports": False,
        "notion_workspace": False,
    },
    Tier.STANDARD: {
        "literature_search": True,
        "limited_tools": True,
        "file_exports": True,
        "automation": True,
        "deep_research": False,
        "email_reports": False,
        "notion_workspace": False,
    },
    Tier.PREMIUM: {
        "literature_search": True,
        "limited_tools": True,
        "file_exports": True,
        "automation": True,
        "deep_research": True,
        "email_reports": True,
        "notion_workspace": True,
    },
}

TIER_LIMITS = {
    Tier.FREE: {"daily_queries": 10, "max_export_rows": 100},
    Tier.STANDARD: {"daily_queries": 100, "max_export_rows": 5000},
    Tier.PREMIUM: {"daily_queries": float('inf'), "max_export_rows": float('inf')},
}

# ═══════════════════════════════════════════════════════════════════════
# STRIPE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

STRIPE_API_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_IDS = {
    Tier.STANDARD: os.environ.get("STRIPE_PRICE_STANDARD", "price_standard"),
    Tier.PREMIUM: os.environ.get("STRIPE_PRICE_PREMIUM", "price_premium"),
}
STRIPE_FREE_TRIAL_DAYS = 15

# ═══════════════════════════════════════════════════════════════════════
# SUPABASE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

def _get_supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

def _get_service_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

# ═══════════════════════════════════════════════════════════════════════
# USER SESSION MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

def init_subscription_state():
    """Initialize subscription-related session state."""
    defaults = {
        "user_id": None,
        "user_email": None,
        "user_tier": Tier.FREE.value,
        "subscription_status": "inactive",
        "subscription_id": None,
        "trial_end_date": None,
        "stripe_customer_id": None,
        "notion_claimed": False,
        "african_verified": False,
        "daily_usage": {},
        "last_usage_date": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def create_user_session(user_id: str, email: str) -> Dict[str, Any]:
    """Create or retrieve user from Supabase and sync to session."""
    if not SUPABASE_URL:
        # Fallback: local-only mode
        st.session_state["user_id"] = user_id or f"user_{int(time.time())}"
        st.session_state["user_email"] = email or "local@demo.com"
        st.session_state["user_tier"] = Tier.FREE.value
        return {"local": True}

    try:
        # Check if user exists
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}",
            headers=_get_supabase_headers(),
        )
        
        if response.status_code == 200 and response.json():
            user = response.json()[0]
        else:
            # Create new user
            user_data = {
                "id": user_id or f"user_{hashlib.sha256(email.encode()).hexdigest()[:16]}",
                "email": email,
                "tier": Tier.FREE.value,
                "created_at": datetime.utcnow().isoformat(),
            }
            create_resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=_get_service_headers(),
                json=user_data,
            )
            user = user_data if create_resp.status_code in (200, 201) else None

        if user:
            st.session_state["user_id"] = user.get("id")
            st.session_state["user_email"] = user.get("email")
            st.session_state["user_tier"] = user.get("tier", Tier.FREE.value)
            st.session_state["subscription_status"] = user.get("subscription_status", "inactive")
            st.session_state["stripe_customer_id"] = user.get("stripe_customer_id")
            st.session_state["notion_claimed"] = user.get("notion_claimed", False)
            st.session_state["african_verified"] = user.get("african_verified", False)
            
            if user.get("trial_end"):
                st.session_state["trial_end_date"] = user.get("trial_end")
            
            return user
    except Exception as e:
        logger.error(f"Supabase user session error: {e}")
    
    return {"local": True}

def update_user_tier(tier: Tier):
    """Update user tier in both session and database."""
    st.session_state["user_tier"] = tier.value
    
    if SUPABASE_URL and st.session_state.get("user_id"):
        try:
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/users?id=eq.{st.session_state['user_id']}",
                headers=_get_service_headers(),
                json={"tier": tier.value},
            )
        except Exception as e:
            logger.error(f"Failed to update tier: {e}")

def get_current_tier() -> Tier:
    """Get current user's subscription tier."""
    try:
        return Tier(st.session_state.get("user_tier", Tier.FREE.value))
    except ValueError:
        return Tier.FREE

def check_feature_access(feature: str) -> bool:
    """Check if current tier has access to a feature."""
    tier = get_current_tier()
    return TIER_FEATURES.get(tier, {}).get(feature, False)

def check_daily_limit() -> Tuple[bool, int]:
    """Check if user has exceeded daily query limit."""
    tier = get_current_tier()
    limits = TIER_LIMITS.get(tier, {})
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Reset daily usage if new day
    if st.session_state.get("last_usage_date") != today:
        st.session_state["daily_usage"] = {}
        st.session_state["last_usage_date"] = today
    
    usage = st.session_state["daily_usage"].get("queries", 0)
    max_queries = limits.get("daily_queries", 10)
    
    if max_queries == float('inf'):
        return True, usage
    
    return usage < max_queries, usage

def increment_usage():
    """Increment daily usage counter."""
    today = datetime.now().strftime("%Y-%m-%d")
    if st.session_state.get("last_usage_date") != today:
        st.session_state["daily_usage"] = {}
        st.session_state["last_usage_date"] = today
    
    current = st.session_state["daily_usage"].get("queries", 0)
    st.session_state["daily_usage"]["queries"] = current + 1

# ═══════════════════════════════════════════════════════════════════════
# STRIPE CHECKOUT
# ═══════════════════════════════════════════════════════════════════════

def create_stripe_checkout_session(tier: Tier, success_url: str, cancel_url: str) -> Optional[str]:
    """Create Stripe checkout session for subscription."""
    if not STRIPE_API_KEY:
        st.warning("Stripe not configured. Using local mode.")
        return None
    
    price_id = STRIPE_PRICE_IDS.get(tier)
    if not price_id:
        return None
    
    try:
        import stripe
        stripe.api_key = STRIPE_API_KEY
        
        customer_id = st.session_state.get("stripe_customer_id")
        
        session_params = {
            "mode": "subscription",
            "payment_method_types": ["card"],
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        
        if customer_id:
            session_params["customer"] = customer_id
        else:
            session_params["customer_email"] = st.session_state.get("user_email")
        
        session = stripe.checkout.Session.create(**session_params)
        return session.url
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        return None

def create_stripe_customer(email: str) -> Optional[str]:
    """Create Stripe customer and return ID."""
    if not STRIPE_API_KEY:
        return None
    
    try:
        import stripe
        stripe.api_key = STRIPE_API_KEY
        customer = stripe.Customer.create(email=email)
        return customer.id
    except Exception as e:
        logger.error(f"Stripe customer creation error: {e}")
        return None

def verify_stripe_webhook(payload: bytes, signature: str) -> bool:
    """Verify Stripe webhook signature."""
    if not STRIPE_WEBHOOK_SECRET:
        return False
    
    try:
        import stripe
        stripe.api_key = STRIPE_API_KEY
        stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
        return True
    except Exception:
        return False

def handle_stripe_webhook(event: dict):
    """Process Stripe webhook events."""
    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})
    
    if event_type == "checkout.session.completed":
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        
        # Update user in database
        if SUPABASE_URL and st.session_state.get("user_id"):
            try:
                tier = Tier.PREMIUM if "premium" in str(data.get("line_items", [])) else Tier.STANDARD
                requests.patch(
                    f"{SUPABASE_URL}/rest/v1/users?id=eq.{st.session_state['user_id']}",
                    headers=_get_service_headers(),
                    json={
                        "stripe_customer_id": customer_id,
                        "subscription_id": subscription_id,
                        "subscription_status": "active",
                        "tier": tier.value,
                    },
                )
                st.session_state["stripe_customer_id"] = customer_id
                st.session_state["subscription_id"] = subscription_id
                st.session_state["subscription_status"] = "active"
                st.session_state["user_tier"] = tier.value
            except Exception as e:
                logger.error(f"Webhook update error: {e}")
    
    elif event_type == "customer.subscription.deleted":
        # Downgrade to free
        update_user_tier(Tier.FREE)
        st.session_state["subscription_status"] = "cancelled"

# ═══════════════════════════════════════════════════════════════════════
# TRIAL MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

def start_trial(tier: Tier = Tier.STANDARD) -> datetime:
    """Start free trial for specified tier."""
    trial_end = datetime.utcnow() + timedelta(days=STRIPE_FREE_TRIAL_DAYS)
    st.session_state["trial_end_date"] = trial_end.isoformat()
    st.session_state["subscription_status"] = "trial"
    st.session_state["user_tier"] = tier.value
    
    # Update in database
    if SUPABASE_URL and st.session_state.get("user_id"):
        try:
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/users?id=eq.{st.session_state['user_id']}",
                headers=_get_service_headers(),
                json={
                    "trial_end": trial_end.isoformat(),
                    "subscription_status": "trial",
                    "tier": tier.value,
                },
            )
        except Exception as e:
            logger.error(f"Trial start error: {e}")
    
    return trial_end

def is_trial_active() -> bool:
    """Check if trial is still active."""
    if st.session_state.get("subscription_status") != "trial":
        return False
    
    trial_end = st.session_state.get("trial_end_date")
    if not trial_end:
        return False
    
    try:
        end_date = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))
        return datetime.utcnow() < end_date
    except Exception:
        return False

def get_trial_days_remaining() -> int:
    """Get remaining trial days."""
    trial_end = st.session_state.get("trial_end_date")
    if not trial_end:
        return 0
    
    try:
        end_date = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))
        remaining = (end_date - datetime.utcnow()).days
        return max(0, remaining)
    except Exception:
        return 0

# ═══════════════════════════════════════════════════════════════════════
# ACCESS CONTROL DECORATOR
# ═══════════════════════════════════════════════════════════════════════

def require_tier(tier: Tier):
    """Decorator to enforce tier-based access."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            current = get_current_tier()
            if current.value not in [t.value for t in Tier] or Tier(current.value).value < tier.value:
                st.error(f"🔒 This feature requires {tier.name} tier or higher.")
                st.info(f"Upgrade at: Settings → Subscription")
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ═══════════════════════════════════════════════════════════════════════
# STRIPE PORTAL (Manage Subscription)
# ═══════════════════════════════════════════════════════════════════════

def open_stripe_portal() -> Optional[str]:
    """Open Stripe customer portal for subscription management."""
    if not STRIPE_API_KEY or not st.session_state.get("stripe_customer_id"):
        return None
    
    try:
        import stripe
        stripe.api_key = STRIPE_API_KEY
        
        session = stripe.billing_portal.Session.create(
            customer=st.session_state["stripe_customer_id"],
            return_url=st.query_params.get("url", "http://localhost:8501"),
        )
        return session.url
    except Exception as e:
        logger.error(f"Stripe portal error: {e}")
        return None

# ─── Cached Resource ───────────────────────────────────────────────────
@st.cache_resource(ttl=3600)
def get_subscription_status() -> Dict[str, Any]:
    """Get cached subscription status."""
    return {
        "tier": get_current_tier().value,
        "features": TIER_FEATURES.get(get_current_tier(), {}),
        "limits": TIER_LIMITS.get(get_current_tier(), {}),
        "trial_active": is_trial_active(),
        "trial_remaining": get_trial_days_remaining(),
        "status": st.session_state.get("subscription_status", "inactive"),
    }