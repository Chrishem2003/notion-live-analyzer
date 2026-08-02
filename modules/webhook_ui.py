
import streamlit as st
from modules.webhook_manager import send_enterprise_webhook
from modules.database import log_backend_event

def render_webhook_panel():
    """
    Renders the Webhook Management & Event Dispatcher interface in Streamlit.
    """
    st.subheader(" Enterprise Webhook Event Dispatcher")
    st.caption("Configure and test real-time notification streams to external endpoints or collaboration channels.")

    webhook_url = st.text_input("Webhook Endpoint URL", value="https://your-webhook-endpoint.com/v1/events", type="default")
    event_type = st.selectbox("Event Classification", ["SECURITY_ALERT", "SYSTEM_HEALTH", "DATA_SYNC", "CUSTOM_NOTIFICATION"])
    message = st.text_area("Event Payload Message", value="Routine telemetry check completed successfully.")

    if st.button("Dispatch Webhook Event Now"):
        with st.spinner("Broadcasting event payload..."):
            result = send_enterprise_webhook(webhook_url, event_type, message, {"triggered_by": "Chrishem Admin"})
            
            if result["status"] == "success":
                st.success(f"Webhook successfully dispatched! HTTP Status: {result['status_code']}")
            elif result["status"] == "skipped":
                st.warning("Webhook dispatch skipped: Please provide a valid active endpoint URL.")
            else:
                st.error(f"Webhook dispatch failed: {result.get('message', 'Unknown error')}")
