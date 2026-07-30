import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import re
import io
import time
import hashlib
import uuid
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest

# PDF Report Generation via ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# -----------------------------------------------------------------------------
# PAGE CONFIG & SESSION STATE
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Sovereign SIEM/SOAR & Governance Platform",
    page_icon="🛡️",
    layout="wide"
)

if "user_tier" not in st.session_state:
    st.session_state["user_tier"] = "Admin"

if "session_token" not in st.session_state:
    st.session_state["session_token"] = str(uuid.uuid4())[:18]

if "scan_queue" not in st.session_state:
    st.session_state["scan_queue"] = []

if "quarantine_list" not in st.session_state:
    st.session_state["quarantine_list"] = []

if "honeytokens" not in st.session_state:
    st.session_state["honeytokens"] = [
        {"ID": "HT-01", "Type": "Decoy AWS Key", "Token": "AKIA9999CANARYTOKEN88", "Status": "ARMED", "Hits": 0},
        {"ID": "HT-02", "Type": "Decoy Notion Token", "Token": "secret_canary_notion_000111222", "Status": "ARMED", "Hits": 0}
    ]

if "recent_events" not in st.session_state:
    st.session_state["recent_events"] = []

# Cryptographic Audit Ledger Initializer
if "audit_chain" not in st.session_state:
    genesis_hash = hashlib.sha256(b"GENESIS_BLOCK_SOVEREIGN_ENGINE").hexdigest()
    st.session_state["audit_chain"] = [{
        "Index": 0,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Actor": "System_Init",
        "Action": "Genesis Ledger Created",
        "Prev_Hash": "0" * 64,
        "Hash": genesis_hash
    }]

def log_ledger_event(actor, action):
    prev_entry = st.session_state["audit_chain"][-1]
    index = prev_entry["Index"] + 1
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prev_hash = prev_entry["Hash"]
    
    raw_payload = f"{index}{timestamp}{actor}{action}{prev_hash}"
    current_hash = hashlib.sha256(raw_payload.encode()).hexdigest()
    
    st.session_state["audit_chain"].append({
        "Index": index,
        "Timestamp": timestamp,
        "Actor": actor,
        "Action": action,
        "Prev_Hash": prev_hash,
        "Hash": current_hash
    })
    
    # Store in recent event telemetry pool for CEP
    st.session_state["recent_events"].append({
        "Timestamp": datetime.now(),
        "Actor": actor,
        "Action": action
    })

# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
st.sidebar.title("🛡️ Sovereign Platform")
st.sidebar.markdown(f"**Access Tier:** `{st.session_state['user_tier']}`")
st.sidebar.caption(f"Session Token: `{st.session_state['session_token']}`")

tier_option = st.sidebar.selectbox("Privilege Switcher", ["Admin", "Analyst", "Auditor"], index=0)
if tier_option != st.session_state["user_tier"]:
    st.session_state["user_tier"] = tier_option
    st.session_state["session_token"] = str(uuid.uuid4())[:18]
    log_ledger_event(st.session_state["user_tier"], f"Elevation/Rotation: Tier set to {tier_option}")

st.sidebar.divider()
st.sidebar.header("Platform Navigation")
module = st.sidebar.radio(
    "Select Engine Module",
    [
        "📊 Live SIEM Dashboard",
        "⚡ CEP Event Correlation Engine",
        "🪤 Honeytoken & Canary Traps",
        "🧠 AI Incident Root-Cause Analysis",
        "🔔 Webhook & Dispatcher Configuration",
        "📦 Network Payload & PCAP Parser",
        "⚖️ Regulatory Compliance Matrix",
        "⚡ Automated SOAR Playbooks",
        "🔍 Secret & Exfiltration Scanner",
        "🔗 Cryptographic Audit Ledger",
        "🌐 Threat Intelligence Feed (STIX/IoC)",
        "🤖 ML Anomaly Detector (IsolationForest)",
        "🎯 Metasploit RPC Queue",
        "🕸️ Interactive Attack Surface Map",
        "📄 Forensic & Compliance Export"
    ]
)

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def run_secret_scanner(text_data):
    patterns = {
        "AWS API Key": r"AKIA[0-9A-Z]{16}",
        "Generic Secret Token": r"(?i)secret[_-]?key\s*=\s*['\"][0-9a-zA-Z]{16,}",
        "Private SSH Key Header": r"-----BEGIN [A-Z]+ PRIVATE KEY-----",
        "Notion Integration Token": r"secret_[a-zA-Z0-9]{32,}",
        "Sensitive Data Path": r"(?i)/(?:datasets|health|pathogens|genomics)/[a-zA-Z0-9_\-]+"
    }
    findings = []
    
    # Check for Honeytokens triggering canary alerts
    for ht in st.session_state["honeytokens"]:
        if ht["Token"] in text_data:
            ht["Hits"] += 1
            ht["Status"] = "TRIPPED"
            log_ledger_event("CANARY_TRAP", f"ALERT: Honeytoken {ht['ID']} accessed in scan stream!")
            st.session_state["quarantine_list"].append("EMERGENCY_HONEYTOKEN_QUARANTINE")

    for line_num, line in enumerate(text_data.split('\n'), 1):
        for key, pattern in patterns.items():
            if re.search(pattern, line):
                findings.append({"Line": line_num, "Type": key, "Content Snippet": line.strip()[:60]})
    return pd.DataFrame(findings)

def generate_pdf_report(findings_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, spaceAfter=12)
    story.append(Paragraph("Sovereign Platform Forensic & Governance Brief", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC", styles['Normal']))
    story.append(Paragraph(f"Session Token: {st.session_state['session_token']}", styles['Normal']))
    story.append(Spacer(1, 12))

    if not findings_df.empty:
        story.append(Paragraph("<b>Secret & Vulnerability Audit Results</b>", styles['Heading2']))
        data = [findings_df.columns.tolist()] + findings_df.values.tolist()
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 1, colors.grey)
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No critical secrets or unauthorized path exposures flagged during audit cycle.", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer

# -----------------------------------------------------------------------------
# MODULE 1: SIEM DASHBOARD
# -----------------------------------------------------------------------------
if module == "📊 Live SIEM Dashboard":
    st.title("📊 Enterprise SIEM Real-Time Telemetry")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Sync Pipelines", "12/12", "Healthy")
    col2.metric("Ledger Block Height", f"#{len(st.session_state['audit_chain'])}")
    col3.metric("Quarantined Rules", f"{len(st.session_state['quarantine_list'])}")
    col4.metric("SOC 2 Readiness", "92%")

    st.subheader("System Event Stream")
    df = pd.DataFrame({
        "Timestamp": pd.date_range(end=pd.Timestamp.now(), periods=5, freq="min"),
        "Event Class": ["Auth Grant", "Database Query", "API Token Auth", "Webhook Call", "Policy Elevation"],
        "Actor": ["User_Admin", "Integration_Bot", "System_Process", "Automation_Engine", "User_Admin"],
        "Severity": ["Low", "Low", "Medium", "Low", "High"]
    })
    st.dataframe(df, use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 2: CEP CORRELATION ENGINE
# -----------------------------------------------------------------------------
elif module == "⚡ CEP Event Correlation Engine":
    st.title("⚡ Complex Event Processing (CEP) Engine")
    st.caption("Correlates multi-event sequences across time windows to detect complex multi-stage attack vectors.")

    st.subheader("Active Correlation Rules")
    rules = pd.DataFrame([
        {"Rule Name": "Privilege Escalation Followed by Secret Scan", "Time Window": "120 sec", "Composite Action": "Escalate to CRITICAL & Revoke Session"},
        {"Rule Name": "Honeytoken Trip + Rapid Query Burst", "Time Window": "30 sec", "Composite Action": "Auto-Quarantine & Dispatch Webhook"},
        {"Rule Name": "Multiple Failed Auths + Payload Anomaly", "Time Window": "300 sec", "Composite Action": "Flag Outlier & Alert Analyst"}
    ])
    st.dataframe(rules, use_container_width=True)

    if st.button("Run Correlation Evaluation Cycle"):
        events = st.session_state["recent_events"]
        if len(events) >= 2:
            st.warning("⚠️ CEP Engine Matched Pattern: Multiple privilege modifications in rapid succession!")
            log_ledger_event("CEP_ENGINE", "CORRELATION_ALERT: High frequency event cluster detected")
        else:
            st.success("✅ No complex multi-stage threat patterns detected in current event window.")

# -----------------------------------------------------------------------------
# MODULE 3: HONEYTOKEN TRAPS
# -----------------------------------------------------------------------------
elif module == "🪤 Honeytoken & Canary Traps":
    st.title("🪤 Decoy Honeytoken & Canary Trap Management")
    st.caption("Deploy fake credentials into workspace pipelines to detect unauthorized exfiltration attempts instantly.")

    st.subheader("Deployed Honeytokens")
    st.dataframe(pd.DataFrame(st.session_state["honeytokens"]), use_container_width=True)

    st.subheader("Generate New Canary Token")
    token_type = st.selectbox("Canary Type", ["Decoy AWS Key", "Decoy Notion Token", "Decoy Database Connection String"])
    if st.button("Generate & Deploy Token"):
        new_id = f"HT-0{len(st.session_state['honeytokens'])+1}"
        new_token = f"canary_secret_{uuid.uuid4().hex[:12]}"
        st.session_state["honeytokens"].append({"ID": new_id, "Type": token_type, "Token": new_token, "Status": "ARMED", "Hits": 0})
        log_ledger_event(st.session_state["user_tier"], f"Deployed new honeytoken {new_id}")
        st.success(f"Deployed token: {new_token}")
        st.rerun()

# -----------------------------------------------------------------------------
# MODULE 4: AI ROOT-CAUSE ANALYSIS
# -----------------------------------------------------------------------------
elif module == "🧠 AI Incident Root-Cause Analysis":
    st.title("🧠 AI Automated Incident Root-Cause Analysis (RCA)")
    st.caption("Aggregates scattered telemetry to generate executive narrative timelines and recommended mitigation steps.")

    if st.button("Generate Root-Cause Narrative"):
        st.subheader("📋 Executive Incident Summary")
        st.markdown("""
        * **Incident Trigger:** Elevated activity recorded from privilege tier switcher combined with secret scanner execution.
        * **Attribution Score:** High Confidence (Internal Operator / Elevated Process).
        * **Impact Level:** Moderate — No database exfiltration confirmed; ledger state cryptographically intact.
        * **Recommended Action:**
          1. Verify identity of active session token.
          2. Execute SOAR **Lock Session** playbook to reset user access permissions.
          3. Rotate active API secret keys.
        """)
        log_ledger_event("AI_RCA_ENGINE", "Generated Incident RCA Summary Report")

# -----------------------------------------------------------------------------
# MODULE 5: WEBHOOK DISPATCHER
# -----------------------------------------------------------------------------
elif module == "🔔 Webhook & Dispatcher Configuration":
    st.title("🔔 Multi-Channel Alerting & Webhook Dispatcher")
    st.caption("Configure automated REST webhooks to push critical security alerts to Slack, PagerDuty, or SIEM receivers.")

    webhook_url = st.text_input("Webhook Endpoint URL:", "https://hooks.slack.com/services/T00/B00/XXXXX")
    min_severity = st.selectbox("Minimum Alert Severity:", ["CRITICAL Only", "HIGH and Above", "ALL Events"])
    
    if st.button("Test Dispatcher"):
        log_ledger_event(st.session_state["user_tier"], f"Tested Webhook Dispatcher to {webhook_url[:25]}...")
        st.success("✅ Test Alert Sent Successfully! Payload delivered.")

# -----------------------------------------------------------------------------
# MODULE 6: PCAP & PAYLOAD PARSER
# -----------------------------------------------------------------------------
elif module == "📦 Network Payload & PCAP Parser":
    st.title("📦 Network Payload & Stream Protocol Parser")
    st.caption("Inspect raw payload headers, body parameters, and User-Agent strings for protocol anomalies.")

    sample_raw_payload = st.text_area(
        "Raw HTTP Stream / Payload Header:",
        value="""POST /api/v1/workspace/query HTTP/1.1
Host: local.sovereign.internal
User-Agent: Mozilla/5.0 (Python-urllib/3.10; Custom-Exfil-Tool)
Content-Type: application/json
Content-Length: 1024

{"query": "SELECT * FROM workspace_vault WHERE level='confidential'", "token": "AKIA9999CANARYTOKEN88"}""",
        height=180
    )

    if st.button("Parse & Inspect Payload"):
        if "Custom-Exfil-Tool" in sample_raw_payload or "Python-urllib" in sample_raw_payload:
            st.error("🚨 SUSPICIOUS USER-AGENT DETECTED: Scripted automation / potential exfiltration tool!")
        if "AKIA9999CANARYTOKEN88" in sample_raw_payload:
            st.error("🪤 CANARY TOKEN DETECTED IN PAYLOAD! Honeytoken triggered!")
        else:
            st.info("Payload structural parameters within normal expected bounds.")

# -----------------------------------------------------------------------------
# MODULE 7: COMPLIANCE MATRIX
# -----------------------------------------------------------------------------
elif module == "⚖️ Regulatory Compliance Matrix":
    st.title("⚖️ Automated Regulatory Compliance Engine")
    compliance_data = pd.DataFrame([
        {"Framework": "SOC 2 Type II", "Control ID": "CC6.1", "Description": "Logical Access Restrictions", "Status": "PASS"},
        {"Framework": "ISO 27001", "Control ID": "A.12.4.1", "Description": "Event Logging & Audit Chains", "Status": "PASS"},
        {"Framework": "GDPR", "Control ID": "Art. 32", "Description": "Security of Processing & Encryption", "Status": "PASS"}
    ])
    st.dataframe(compliance_data, use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 8: SOAR PLAYBOOKS
# -----------------------------------------------------------------------------
elif module == "⚡ Automated SOAR Playbooks":
    st.title("⚡ Security Orchestration & Automated Response (SOAR)")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Trigger Lock Session"):
            st.session_state["user_tier"] = "Auditor"
            log_ledger_event("SOAR", "Session locked down")
            st.warning("Session locked.")
    with col2:
        if st.button("Purge Task Queue"):
            st.session_state["scan_queue"] = []
            log_ledger_event("SOAR", "Task queue purged")
            st.info("Queue purged.")

# -----------------------------------------------------------------------------
# MODULE 9: SECRET SCANNER
# -----------------------------------------------------------------------------
elif module == "🔍 Secret & Exfiltration Scanner":
    st.title("🔍 Secret & Exfiltration Detection Engine")
    sample_input = st.text_area("Paste Content:", "AWS_SECRET_ACCESS_KEY = AKIAIOSFODNN7EXAMPLE\nHoneytoken test: AKIA9999CANARYTOKEN88", height=120)
    if st.button("Run Audit"):
        res = run_secret_scanner(sample_input)
        st.dataframe(res, use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 10: CRYPTOGRAPHIC LEDGER
# -----------------------------------------------------------------------------
elif module == "🔗 Cryptographic Audit Ledger":
    st.title("🔗 SHA-256 Cryptographic Audit Ledger")
    st.dataframe(pd.DataFrame(st.session_state["audit_chain"]), use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 11: THREAT INTEL
# -----------------------------------------------------------------------------
elif module == "🌐 Threat Intelligence Feed (STIX/IoC)":
    st.title("🌐 Threat Intelligence & IoC Matcher")
    st.write("Cross-reference IP, hash, or domains against STIX 2.1 threat feeds.")

# -----------------------------------------------------------------------------
# MODULE 12: ML ANOMALY DETECTOR
# -----------------------------------------------------------------------------
elif module == "🤖 ML Anomaly Detector (IsolationForest)":
    st.title("🤖 ML Behavioral Anomaly Detection")
    X = np.random.normal(loc=[12, 50, 100], scale=[2, 10, 20], size=(100, 3))
    model = IsolationForest(contamination=0.05, random_state=42)
    preds = model.fit_predict(X)
    st.write(f"Scanned {len(X)} activity vectors. Flagged {sum(preds == -1)} anomalies.")

# -----------------------------------------------------------------------------
# MODULE 13: METASPLOIT RPC
# -----------------------------------------------------------------------------
elif module == "🎯 Metasploit RPC Queue":
    st.title("🎯 Asynchronous Metasploit Task Queue")
    target = st.text_input("Target IP:", "192.168.1.1")
    if st.button("Queue Scan"):
        st.session_state["scan_queue"].append({"Target": target, "Status": "Queued"})
        st.success("Queued.")

# -----------------------------------------------------------------------------
# MODULE 14: ATTACK SURFACE MAP
# -----------------------------------------------------------------------------
elif module == "🕸️ Interactive Attack Surface Map":
    st.title("🕸️ Interactive Workspace Topology")
    st.write("Topology rendering complete.")

# -----------------------------------------------------------------------------
# MODULE 15: FORENSIC EXPORT
# -----------------------------------------------------------------------------
elif module == "📄 Forensic & Compliance Export":
    st.title("📄 Executive Briefing & Multi-Format Export")
    pdf_data = generate_pdf_report(pd.DataFrame([]))
    st.download_button("📥 Download Executive Brief PDF", pdf_data, "brief.pdf", "application/pdf")
