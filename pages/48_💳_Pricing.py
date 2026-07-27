"""
💳 Pricing — plan comparison and Stripe checkout.
"""
import streamlit as st

st.set_page_config(page_title="Pricing", layout="wide", page_icon="💳")

from modules.accounts import AccountError, Tier
from modules.billing import (
    FEATURE_LABELS,
    PLANS,
    UNLIMITED,
    create_checkout_session,
    plan_for_user,
    stripe_configured,
)
from modules.config import init_session_state
from modules.runtime_perf import resolve_app_url
from modules.session_auth import current_user, render_account_badge
from modules.ui_components import hero_card, load_css, section_header, watermark

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("💳 Plans & Pricing", "Every plan includes the full analysis workspace.", "Pricing")
watermark("CHRISHEM")

with st.sidebar:
    render_account_badge()

user = current_user(refresh=True)
active_tier = plan_for_user(user).tier if user else Tier.FREE

columns = st.columns(3)
for column, tier in zip(columns, (Tier.FREE, Tier.STANDARD, Tier.PREMIUM)):
    plan = PLANS[tier]
    with column:
        with st.container(border=True):
            st.markdown(f"### {plan.name}")
            price = "Free" if plan.price_usd == 0 else f"${plan.price_usd:.0f}/mo"
            st.markdown(f"## {price}")
            st.caption(plan.tagline)
            for highlight in plan.highlights:
                st.markdown(f"- {highlight}")

            if tier is active_tier:
                st.success("Your current plan")
            elif tier is Tier.FREE:
                st.caption("Always available")
            elif user is None:
                st.page_link("pages/47_👤_Account.py", label="Create an account", icon="👤")
            elif not stripe_configured():
                st.caption("💤 Checkout is not configured on this deployment yet.")
            elif st.button(f"Upgrade to {plan.name}", key=f"buy_{tier.value}", type="primary"):
                base_url = resolve_app_url() or ""
                try:
                    session = create_checkout_session(
                        user,
                        tier,
                        success_url=f"{base_url}/Account?checkout=success",
                        cancel_url=f"{base_url}/Pricing?checkout=cancelled",
                    )
                    st.link_button("Continue to secure checkout", session["url"], type="primary")
                except AccountError as exc:
                    st.error(str(exc))

section_header("📋 Full comparison")
rows = []
for feature, label in FEATURE_LABELS.items():
    row = {"Feature": label}
    for tier in (Tier.FREE, Tier.STANDARD, Tier.PREMIUM):
        plan = PLANS[tier]
        quota = plan.quota(feature)
        if quota == UNLIMITED:
            row[plan.name] = "Unlimited"
        elif quota:
            row[plan.name] = f"{quota}/month"
        else:
            row[plan.name] = "✅" if feature in plan.features else "—"
    rows.append(row)
st.dataframe(rows, use_container_width=True, hide_index=True)

st.caption(
    "🎓 Students at universities in African Union member states and qualifying "
    "developing countries get the Standard plan free — verify from your "
    "[Account](/Account) page."
)
