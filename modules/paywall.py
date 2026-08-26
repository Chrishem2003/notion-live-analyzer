import streamlit as st
from modules import subscription, billing_stripe

def enforce_paywall(allowed_plans=("pro", "business", "premium"), feature_name="this premium feature", allow_trial=False):
    """
    Blocks access to gated features for unpaid or trial users.
    Admin users (CHRISHEM) automatically bypass all paywalls.
    """
    user_identity = st.session_state.get("user_identity", {})
    email = user_identity.get("email", "")
    is_admin = user_identity.get("role") == "admin" or user_identity.get("is_admin", False)

    if is_admin:
        return True  # Admin bypass

    status = subscription.get_status(email)
    current_plan = status.get("effective_plan", "free")
    is_trial = status.get("status") == "trialing"

    # Block trial users if allow_trial is False
    if is_trial and not allow_trial:
        st.warning(f"ðŸ”’ **Trial Access Restricted:** Trial accounts cannot access {feature_name}. Please upgrade to a paid subscription.")
        render_paywall_cta()
        st.stop()

    if current_plan not in allowed_plans and status.get("status") != "active":
        st.error(f"ðŸ”’ **Subscription Required:** You need an active paid plan ({', '.join(allowed_plans).upper()}) to access {feature_name}.")
        render_paywall_cta()
        st.stop()

    return True

def render_paywall_cta():
    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("âš¡ Unlock Sovereign Apex Business Access")
        st.write("Get instant access to Bio-Research Notion Planners, Brain FM Focus Soundscapes, and advanced analytics pipelines.")
    with col2:
        if st.button("ðŸ’³ Upgrade Subscription Now", type="primary", width='stretch'):
            st.session_state["menu_selection"] = "ðŸ’³ Billing & Subscription"
            st.rerun()
