"""
INTEGRATION SNIPPET — not a standalone file to run.

Two places to wire the new modules/subscription.py + modules/billing_stripe.py
into the app that already exists:

1. Once, near the top of your main app entrypoint (wherever portal.py hands
   off to a logged-in session) — handles the Stripe Checkout return leg:
"""

import streamlit as st
from modules import subscription, billing_stripe

def handle_checkout_return():
    qp = st.query_params
    if qp.get("checkout") == "success" and qp.get("session_id"):
        result = billing_stripe.verify_checkout_session(qp["session_id"])
        st.query_params.clear()
        if result:
            st.toast(f"Upgraded to {result['plan'].title()} — welcome aboard.", icon="✅")
        else:
            st.warning("We couldn't confirm that payment yet. If you were charged, "
                       "use 'Resync billing' in Settings or contact support.")
    elif qp.get("checkout") == "cancelled":
        st.query_params.clear()
        st.info("Checkout cancelled — no charge was made.")


"""
2. At the top of every hub page's main(), one line:

    def main():
        from modules.subscription import require_active_subscription
        require_active_subscription(hub_id="ml")   # <- use this hub's id from HUB_MIN_PLAN
        setup_page(...)
        ...

   This already matches the call Global Mission Control makes today
   (`require_active_subscription()`) — just add the hub_id kwarg so it
   checks the right minimum plan instead of the default "free".

3. Opportunistic resync (put in Settings, or silently on login for
   premium/pro users) so a cancellation made in the Stripe Customer Portal
   doesn't keep granting access until someone remembers to reconcile:

    if st.button("Resync billing status"):
        result = billing_stripe.reconcile_subscription(user_email)
        st.write(result or "No Stripe subscription found for this account.")

4. Customer Portal link (self-service upgrade/downgrade/cancel/invoices),
   e.g. in Settings:

    portal_url = billing_stripe.create_billing_portal_session(user_email)
    if portal_url:
        st.link_button("Manage billing", portal_url)
"""
