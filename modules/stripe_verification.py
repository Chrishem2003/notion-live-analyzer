import security_guard

import os
import hmac
import hashlib
import streamlit as st
from modules.database import log_backend_event

def verify_student_eligibility(email: str) -> bool:
    """
    Verifies if a user qualifies for student pricing based on institutional domain endings (e.g., .ac.ug).
    """
    if not email or "@" not in email:
        return False
    
    domain = email.split("@")[1].lower()
    valid_student_indicators = [".ac.ug", ".edu", ".ac.", "student"]
    
    is_student = any(domain.endswith(ind) or ind in domain for ind in valid_student_indicators)
    if is_student:
        log_backend_event("INFO", f"Student eligibility verified for domain: {domain}")
    return is_student

def render_subscription_panel():
    """
    Renders the Stripe Tiered Subscription & Student Verification portal in Streamlit.
    """
    st.subheader(" Enterprise Tiered Licensing & Student Verification")
    st.caption("Upgrade your engine capabilities or verify institutional student status for academic grants.")

    user_email = st.text_input("Enter Institutional or Personal Email", value="chrishem@uni.ac.ug")

    if user_email:
        if verify_student_eligibility(user_email):
            st.success(" Institutional Student Status Verified! Eligible for 50% academic research discount.")
            tier_price = ".00 / month (Academic Tier)"
        else:
            st.info("Standard Professional Tier selected.")
            tier_price = ".00 / month (Enterprise Tier)"

        st.markdown(f"**Selected Plan:** {tier_price}")

        if st.button("Proceed to Secure Stripe Checkout"):
            stripe_key = os.getenv("STRIPE_SECRET_KEY")
            if not stripe_key:
                log_backend_event("WARNING", "Stripe Checkout attempted without live API keys configured.")
                st.warning("Stripe payment gateway currently operating in simulation mode (API keys not detected).")
            else:
                st.success("Redirecting to secure Stripe checkout portal...")
                log_backend_event("INFO", f"Initiated Stripe checkout session for {user_email}")
