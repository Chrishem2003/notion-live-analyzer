import streamlit as st
import os

# Configure Page Settings
st.set_page_config(
    page_title="CHRISHEM Enterprise Intelligence Engine",
    page_icon="?",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import Core Modules
from modules.database import init_db
from modules.executive import render_executive_panel
from modules.analytics import render_analytics_panel
from modules.vault import render_vault_panel
from modules.db_viewer import render_db_viewer_panel
from modules.health_monitor import render_health_monitor_panel
from modules.data_cleaner import render_data_cleaner_panel
from modules.report_generator import render_report_generator_panel
from modules.api_gateway import render_api_gateway_panel
from modules.log_rotator import render_log_rotator_panel
from modules.webhook_ui import render_webhook_panel
from modules.mfa_engine import render_mfa_panel
from modules.bioinformatics_pipeline import render_bioinformatics_panel
from modules.live_telemetry import render_live_telemetry_panel
from modules.security_auditor import render_security_audit_panel
from modules.backup_engine import render_backup_panel
from modules.performance_profiler import render_profiler_panel
from modules.threat_response import render_threat_response_panel
from modules.aes_vault import generate_aes_key
from modules.email_reports import send_audit_email
from modules.stripe_verification import render_subscription_panel
from modules.spatial_audio import render_spatial_audio_panel
from modules.devin_reviewer import render_devin_review_panel
from modules.ci_watchdog import render_ci_watchdog_panel
from supervisor_daemon import render_supervisor_panel
from modules.global_ping import render_global_ping_panel

# Initialize Database Persistence Layer
init_db()

def main():
    st.sidebar.title("? CHRISHEM Engine")
    st.sidebar.caption("Enterprise Intelligence & Research OS")
    st.sidebar.markdown("---")

    navigation = st.sidebar.radio(
        "Select Subsystem",
        [
            "Executive Dashboard",
            "Advanced Analytics",
            "Secure Vault (Passkey)",
            "AES-256-GCM Research Vault",
            "Database Inspector",
            "System Health Monitor",
            "Dataset Sanitizer",
            "Audit Report Generator",
            "Email Reports & Dispatch",
            "API Gateway",
            "Log Rotator & Management",
            "Webhook Dispatcher",
            "MFA Security Engine",
            "Bioinformatics Sequence Pipeline",
            "Live Telemetry & Node Health",
            "Security Auditor & WAF",
            "Stripe Licensing & Student Verification",
            "Spatial Audio Focus Soundscapes",
            "Devin AI Code Reviewer",
            "CI/CD Pipeline Watchdog",`n            "Runtime Supervisor Daemon",`n            "Global Edge Telemetry & Ping",
            "Performance Profiler & Benchmarks",
            "Threat Response & Incident Log",
            "Automated Backup & Recovery"
        ]
    )

    st.sidebar.markdown("---")
    st.sidebar.info("System Status: ?? Operational\nEnvironment: Production\nOperator: Chrishem")

    # Render Selected Module Panel
    if navigation == "Executive Dashboard":
        render_executive_panel()
    elif navigation == "Advanced Analytics":
        render_analytics_panel()
    elif navigation == "Secure Vault (Passkey)":
        render_vault_panel()
    elif navigation == "AES-256-GCM Research Vault":
        st.subheader("?? AES-256-GCM Military-Grade Vault")
        st.caption("Securely encrypt sensitive research records with unique nonces and authenticated encryption.")
        secret_key = st.text_input("Encryption Master Key (Base64)", value=generate_aes_key())
        secret_data = st.text_area("Record Content", value="Confidential bioinformatics and field sample metrics.")
        if st.button("Encrypt Record"):
            from modules.aes_vault import encrypt_vault_record
            res = encrypt_vault_record(secret_data, secret_key)
            if res["status"] == "success":
                st.success("Record successfully encrypted!")
                st.code(res["ciphertext"])
    elif navigation == "Database Inspector":
        render_db_viewer_panel()
    elif navigation == "System Health Monitor":
        render_health_monitor_panel()
    elif navigation == "Dataset Sanitizer":
        render_data_cleaner_panel()
    elif navigation == "Audit Report Generator":
        render_report_generator_panel()
    elif navigation == "Email Reports & Dispatch":
        st.subheader("?? Automated Email Dispatcher (SendGrid / SMTP)")
        recipient = st.text_input("Recipient Email", value="researcher@uni.ac.ug")
        subj = st.text_input("Email Subject", value="CHRISHEM Engine Audit Summary")
        body = st.text_area("HTML Body Content", value="<h3>System Audit Complete</h3><p>All nodes operating within normal parameters.</p>")
        if st.button("Send Audit Email Now"):
            res = send_audit_email(recipient, subj, body)
            if res["status"] == "success":
                st.success(f"Report successfully dispatched via {res['method']}!")
            elif res["status"] == "skipped":
                st.warning("Email reporting skipped: Configure SENDGRID_API_KEY or SMTP variables.")
            else:
                st.error(f"Dispatch failed: {res.get('message')}")
    elif navigation == "API Gateway":
        render_api_gateway_panel()
    elif navigation == "Log Rotator & Management":
        render_log_rotator_panel()
    elif navigation == "Webhook Dispatcher":
        render_webhook_panel()
    elif navigation == "MFA Security Engine":
        render_mfa_panel()
    elif navigation == "Bioinformatics Sequence Pipeline":
        render_bioinformatics_panel()
    elif navigation == "Live Telemetry & Node Health":
        render_live_telemetry_panel()
    elif navigation == "Security Auditor & WAF":
        render_security_audit_panel()
    elif navigation == "Stripe Licensing & Student Verification":
        render_subscription_panel()
    elif navigation == "Spatial Audio Focus Soundscapes":
        render_spatial_audio_panel()
    elif navigation == "Devin AI Code Reviewer":
        render_devin_review_panel()
    elif navigation == "CI/CD Pipeline Watchdog":
        render_ci_watchdog_panel()
    elif navigation == "Runtime Supervisor Daemon":
        render_supervisor_panel()
    elif navigation == "Global Edge Telemetry & Ping":
        render_global_ping_panel()
    elif navigation == "Performance Profiler & Benchmarks":
        render_profiler_panel()
    elif navigation == "Threat Response & Incident Log":
        render_threat_response_panel()
    elif navigation == "Automated Backup & Recovery":
        render_backup_panel()

if __name__ == "__main__":
    main()





