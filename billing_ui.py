import streamlit as st
from modules import subscription, billing_stripe

def render_notion_style_billing(user_email, user_name=""):
    st.markdown("""
        <style>
        .billing-container {
            background: #0B0E11;
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 16px;
            padding: 24px;
            color: #EDEFF2;
        }
        .billing-card {
            background: #262B33;
            border: 1px solid #3A4048;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            cursor: pointer;
        }
        .billing-card-selected {
            border: 2px solid #4fb8a6 !important;
            background: rgba(56, 189, 248, 0.05);
        }
        .badge-discount {
            background: #b5790e;
            color: white;
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: 6px;
            float: right;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### ðŸ’³ Upgrade Your Subscription")

    col_left, col_right = st.columns([1.1, 0.9])

    with col_left:
        st.markdown("**Customer & Payment Details**")
        c_name = st.text_input("Name", value=user_name or "Chris Shem", key="bill_name")
        c_biz = st.text_input("Business name (optional)", placeholder="Acme Inc.", key="bill_biz")
        
        st.markdown("**Payment Method**")
        st.info(f"ðŸ”’ Payment Link verification active for **{user_email}**")
        
        card_num = st.text_input("Card number", placeholder="1234 1234 1234 1234", key="bill_card")
        c_exp, c_cvc = st.columns(2)
        with c_exp:
            st.text_input("Expiration date", placeholder="MM / YY", key="bill_exp")
        with c_cvc:
            st.text_input("Security code", placeholder="CVC", type="password", key="bill_cvc")

    with col_right:
        st.markdown("**Billing options**")
        
        billing_cycle = st.radio(
            "Select Cycle",
            ["Pay monthly ($24 / month / member)", "Pay annually ($20 / month / member - Save 17%)"],
            label_visibility="collapsed"
        )
        
        is_annual = "annually" in billing_cycle
        selected_plan_key = "business"
        selected_interval = "annual" if is_annual else "monthly"
        price_display = "$20" if is_annual else "$24"

        st.markdown(f"""
            <div class="billing-container" style="margin-top: 15px;">
                <h2 style="margin:0; font-size: 2rem;">{price_display} <span style="font-size: 1rem; color: #6B7280;">/ month</span></h2>
                <p style="font-size: 0.85rem; color: #6B7280; margin-top: 8px;">
                    Your subscription auto-renews each period unless canceled.
                </p>
            </div>
        """, unsafe_allow_html=True)

        agree_terms = st.checkbox("I agree to the auto-renewal terms & subscription agreement.", key="bill_terms")

        if st.button("ðŸš€ Upgrade to Business", type="primary", width='stretch', disabled=not agree_terms):
            if billing_stripe.is_configured():
                checkout_url = billing_stripe.create_checkout_session(user_email, selected_plan_key, selected_interval)
                if checkout_url:
                    st.link_button("âž¡ï¸ Proceed to Stripe Secure Checkout", checkout_url, type="primary", width='stretch')
                else:
                    st.error("Error creating Stripe checkout session. Check API keys.")
            else:
                st.warning("Stripe credentials not fully configured in environment variables.")

        st.button("ðŸ’¬ Contact Sales", width='stretch')
