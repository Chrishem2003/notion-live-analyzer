
"""Subscription Engine  Stripe Integration & Tier Management."""
import os
import hashlib
import hmac
import time
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple, List
from enum import Enum

import logging
import streamlit as st
import requests
import pandas as pd

from modules.subscription_core import (
    TRIAL_LENGTH_DAYS as TRIAL_LENGTH_DAYS_CORE,
    SubStatus,
    Subscription,
)

logger = logging.getLogger(__name__)

# Single source of truth for trial length comes from subscription_core.
# Keep a local alias for backwards compatibility with existing callers.
STRIPE_FREE_TRIAL_DAYS = TRIAL_LENGTH_DAYS_CORE

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# TIER DEFINITIONS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class Tier(Enum):
    FREE = "free"
    STANDARD = "standard"  # For verified African students
    PREMIUM = "premium"    # Full features with payment

# Detailed feature access per tier
TIER_FEATURES = {
    Tier.FREE: {
        # Core Features
        "file_upload": True,
        "basic_stats": True,
        "data_preview": True,
        
        # Limited Features (gated)
        "file_exports": False,
        "advanced_stats": False,
        "ai_insights": False,
        "literature_search": False,
        "predictive_modeling": False,
        "dashboard_builder": False,
        "data_simulator": False,
        "meta_analysis": False,
        "automation": False,
        "email_reports": False,
        "notion_workspace": False,
        
        # Usage Limits
        "daily_queries": 10,
        "max_file_rows": 100,
        "max_audits": 3,
        "max_charts": 3,
        "export_limit": "preview",  # preview-only, limited
    },
    Tier.STANDARD: {
        # African/Developing Region Students (Verified via ID)
        "file_upload": True,
        "basic_stats": True,
        "data_preview": True,
        "file_exports": True,
        "advanced_stats": True,
        "ai_insights": True,
        "literature_search": True,
        "dashboard_builder": True,
        "data_simulator": True,
        "predictive_modeling": False,
        "meta_analysis": True,
        "automation": True,
        "email_reports": False,
        "notion_workspace": False,
        
        # Usage Limits
        "daily_queries": 100,
        "max_file_rows": 5000,
        "max_audits": 15,
        "max_charts": 20,
        "export_limit": "full",  # full export
    },
    Tier.PREMIUM: {
        # Full Access - Everything unlocked
        "file_upload": True,
        "basic_stats": True,
        "data_preview": True,
        "file_exports": True,
        "advanced_stats": True,
        "ai_insights": True,
        "literature_search": True,
        "predictive_modeling": True,
        "dashboard_builder": True,
        "data_simulator": True,
        "meta_analysis": True,
        "automation": True,
        "email_reports": True,
        "notion_workspace": True,
        
        # Unlimited
        "daily_queries": float('inf'),
        "max_file_rows": float('inf'),
        "max_audits": float('inf'),
        "max_charts": float('inf'),
        "export_limit": "unlimited",
    },
}

# Page access by tier (organizes pages by priority)
TIER_PAGE_ACCESS = {
    # FREE TIER - Core essential pages only
    Tier.FREE: [
        "1_ðŸ“_File_Analyzer",
        "2_ðŸ”¬_Statistical_Tests",
        "3_ðŸ“ˆ_Advanced_Visuals",
    ],
    # STANDARD TIER - Verified students
    Tier.STANDARD: [
        "1_ðŸ“_File_Analyzer",
        "2_ðŸ”¬_Statistical_Tests",
        "3_ðŸ“ˆ_Advanced_Visuals",
        "4_ðŸ¤–_AI_Insights",
        "5_âš™ï¸_Settings",
        "6_ðŸ§¬_Predictive_Modeling",
        "7_ðŸ·ï¸_Variable_View",
        "8_ðŸ”§_Data_Transformer",
        "9_ðŸ“‹_Methodology_Advisor",
        "10_ðŸ¥_Clinical_Analytics",
        "11_ðŸ’¬_Text_Analysis",
        "12__Dashboard_Builder",
        "13_ðŸ”_Data_Quality",
        "14_ðŸŽ²_Data_Simulator",
        "15_ðŸ“‘_APA_Outputs",
        "16_ðŸ”—_Google_Sheets",
        "18__Presentation_Deck",
        "19_ðŸ“š_Literature_Engine",
        "20__Meta_Analysis",
    ],
    # PREMIUM TIER - Everything
    Tier.PREMIUM: [],  # All pages accessible
}

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# BILLING LIMITS MANAGEMENT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def check_billing_limit(limit_type: str) -> Tuple[bool, str]:
    """
    Check if user has hit a billing limit.
    Returns (can_proceed, message).
    """
    tier = get_current_tier()
    features = TIER_FEATURES.get(tier, {})
    
    limits_config = {
        "file_rows": {
            "free": 100,
            "standard": 5000,
            "premium": float('inf'),
        },
        "exports": {
            "free": "preview",
            "standard": "full", 
            "premium": "unlimited",
        },
        "audits": {
            "free": 3,
            "standard": 15,
            "premium": float('inf'),
        },
        "charts": {
            "free": 3,
            "standard": 20,
            "premium": float('inf'),
        },
    }
    
    config = limits_config.get(limit_type, {})
    tier_key = tier.value
    limit = config.get(tier_key, 0)
    
    # Get current usage
    usage_key = f"{limit_type}_used"
    current_usage = st.session_state.get(usage_key, 0)
    
    if limit == float('inf'):
        return True, " unlimited"
    
    if current_usage >= limit:
        return False, f"{limit_type.capitalize()} limit reached ({current_usage}/{limit}). Upgrade to access more."
    
    return True, f"{limit - current_usage} remaining"

def increment_billingCounter(limit_type: str):
    """Increment usage counter for a billing limit type."""
    usage_key = f"{limit_type}_used"
    current = st.session_state.get(usage_key, 0)
    st.session_state[usage_key] = current + 1

def render_limit_warning(limit_type: str):
    """Render a warning when user approaches their limit."""
    can_proceed, message = check_billing_limit(limit_type)
    
    if not can_proceed:
        st.error(f"ðŸš« {message}")
        st.info("ðŸ’¡ Upgrade to Premium for unlimited access")
        return False
    elif "remaining" in message and int(message.split()[0]) <= 2:
        st.warning(f"âš ï¸ Only {message}")
    return True

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STRIPE CONFIGURATION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

STRIPE_API_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_IDS = {
    Tier.STANDARD: os.environ.get("STRIPE_PRICE_STANDARD", "price_standard"),
    Tier.PREMIUM: os.environ.get("STRIPE_PRICE_PREMIUM", "price_premium"),
}
# STRIPE_FREE_TRIAL_DAYS is defined at the top of this module, sourced from
# subscription_core.TRIAL_LENGTH_DAYS (single source of truth).

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# SUPABASE CONFIGURATION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

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

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# USER SESSION MANAGEMENT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

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
    features = TIER_FEATURES.get(tier, {})
    max_queries = features.get("daily_queries", 10)
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Reset daily usage if new day
    if st.session_state.get("last_usage_date") != today:
        st.session_state["daily_usage"] = {}
        st.session_state["last_usage_date"] = today
    
    usage = st.session_state["daily_usage"].get("queries", 0)
    
    if max_queries == float('inf'):
        return True, usage
    
    return usage < max_queries, usage

def get_user_limits() -> Dict[str, Any]:
    """Get current user's usage limits based on tier."""
    tier = get_current_tier()
    return TIER_FEATURES.get(tier, {})

def check_page_access(page_name: str) -> bool:
    """Check if current tier has access to a specific page."""
    tier = get_current_tier()
    allowed_pages = TIER_PAGE_ACCESS.get(tier, [])
    # Premium has access to all pages (empty list means all)
    if tier == Tier.PREMIUM:
        return True
    # Check if page is in allowed list
    return page_name in allowed_pages

def get_accessible_pages() -> List[str]:
    """Get list of pages accessible to current tier."""
    tier = get_current_tier()
    if tier == Tier.PREMIUM:
        # Return all page files
        return [f.stem for f in __import__('pathlib').Path(__import__('os').path.dirname(__file__)).parent.joinpath('pages').glob('*.py') if f.stem != '__init__']
    return TIER_PAGE_ACCESS.get(tier, [])

def increment_usage():
    """Increment daily usage counter."""
    today = datetime.now().strftime("%Y-%m-%d")
    if st.session_state.get("last_usage_date") != today:
        st.session_state["daily_usage"] = {}
        st.session_state["last_usage_date"] = today

    current = st.session_state["daily_usage"].get("queries", 0)
    st.session_state["daily_usage"]["queries"] = current + 1

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STRIPE CHECKOUT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

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

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# TRIAL MANAGEMENT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

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

def _build_subscription_from_session() -> Optional[Subscription]:
    """Build a subscription_core.Subscription from the current session state.

    This allows the pure-logic ``has_access`` to be the single source of
    truth for trial/paid access, even with session-backed state (no DB yet).
    """
    from modules.subscription_core import Subscription as _Sub
    from modules.subscription_core import start_trial as _start_trial

    status = st.session_state.get("subscription_status", "inactive")
    trial_end = st.session_state.get("trial_end_date")

    if status == "active":
        return _Sub(
            user_id=st.session_state.get("user_id", ""),
            status=SubStatus.ACTIVE,
            trial_started_at=datetime.now(timezone.utc),
            trial_ends_at=datetime.now(timezone.utc) + timedelta(days=STRIPE_FREE_TRIAL_DAYS),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        )

    if status == "trial" and trial_end:
        try:
            end_date = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            return _Sub(
                user_id=st.session_state.get("user_id", ""),
                status=SubStatus.TRIAL,
                trial_started_at=end_date - timedelta(days=STRIPE_FREE_TRIAL_DAYS),
                trial_ends_at=end_date,
            )
        except Exception:
            return None

    return None


def has_access() -> bool:
    """Single source of truth: does the current user have paid/trial access?

    Delegates to ``subscription_core.has_access`` on a subscription built
    from the current session state. Prefer persisting a real Subscription
    row in the database and calling ``subscription_core.has_access(sub)``
    directly for production.
    """
    from modules.subscription_core import has_access as _has_access

    sub = _build_subscription_from_session()
    # If we couldn't build a subscription (e.g. "inactive"), no access.
    if sub is None:
        return False
    return _has_access(sub)


def is_trial_active() -> bool:
    """Check if trial is still active (delegates to the single source of truth)."""
    return has_access() and st.session_state.get("subscription_status") == "trial"


def get_trial_days_remaining() -> int:
    """Get remaining trial days (delegates to subscription_core)."""
    from modules.subscription_core import days_left_in_trial

    sub = _build_subscription_from_session()
    if sub is None:
        return 0
    return days_left_in_trial(sub)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ACCESS CONTROL DECORATOR
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def require_tier(tier: Tier):
    """Decorator to enforce tier-based access."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            current = get_current_tier()
            if current.value not in [t.value for t in Tier] or Tier(current.value).value < tier.value:
                st.error(f"ðŸ”’ This feature requires {tier.name} tier or higher.")
                st.info(f"Upgrade at: Settings â†’ Subscription")
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STRIPE PORTAL (Manage Subscription)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

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

# â”€â”€â”€ Cached Resource â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
