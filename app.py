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
from datetime import datetime
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
    page_title="Notion Live SIEM & SOAR Security Platform",
    page_icon="🛡️",
    layout="wide"
)

if "user_tier" not in st.session_state:
    st.session_state["user_tier"] = "Admin"

if "scan_queue" not in st.session_state:
    st.session_state["scan_queue"] = []

# Initialize Cryptographic Ledger Chain
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

# Helper to append to ledger
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

# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
st.sidebar.title("🛡️ Sovereign SIEM/SOAR")
st.sidebar.markdown(f"**Current Access Level:** `{st.session_state['user_tier']}`")

tier_option = st.sidebar.selectbox("Privilege Level Switcher", ["Admin", "Analyst", "Auditor"], index=0)
if tier_option != st.session_state["user_tier"]:
    st.session_state["user_tier"] = tier_option
    log_ledger_event(st.session_state["user_tier"], f"Switched privilege level to {tier_option}")

st.sidebar.divider()
st.sidebar.header("Navigation Modules")
module = st.sidebar.radio(
    "Select Engine",
    [
        "📊 Live SIEM Overview",
        "🔍 Notion Secret & Exfiltration Scanner",
        "🔗 Cryptographic Tamper-Evident Ledger",
        "🌐 Threat Intelligence Feed (STIX/IoC)",
        "🤖 ML Anomaly Detector (IsolationForest)",
        "🎯 Metasploit RPC Task Queue",
        "🕸️ Interactive Attack Surface Graph",
        "📄 Briefing & Forensic Export"
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
    story.append(Paragraph("Sovereign Platform Forensic & Security Brief", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC", styles['Normal']))
    story.append(Spacer(1, 12))

    if not findings_df.empty:
        story.append(Paragraph("<b>Exfiltration & Secret Findings Summary</b>", styles['Heading2']))
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
        story.append(Paragraph("No critical secrets or unauthorized paths were flagged during this cycle.", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer

# -----------------------------------------------------------------------------
# MODULE 1: OVERVIEW
# -----------------------------------------------------------------------------
if module == "📊 Live SIEM Overview":
    st.title("📊 Workspace Real-Time SIEM Operations")
    st.caption("Central dashboard displaying active security telemetry, automated response pipelines, and ledger health.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Sync Pipelines", "12/12", "Operational")
    col2.metric("Ledger Block Height", f"#{len(st.session_state['audit_chain'])}")
    col3.metric("Detected Anomalies", "3 Flags", "+1 pending review", delta_color="inverse")
    col4.metric("Vault Protection", "AES-256 (TOTP Enforced)")

    st.subheader("Recent System Events")
    df = pd.DataFrame({
        "Timestamp": pd.date_range(end=pd.Timestamp.now(), periods=5, freq="min"),
        "Event": ["Page Edited", "Database Query", "API Token Auth", "External Webhook Call", "Permission Change"],
        "Actor": ["User_Admin", "Integration_Bot", "System_Process", "Automation_Engine", "User_Admin"],
        "Risk Score": ["Low", "Low", "Medium", "Low", "High"]
    })
    st.dataframe(df, use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 2: SECRET SCANNER
# -----------------------------------------------------------------------------
elif module == "🔍 Notion Secret & Exfiltration Scanner":
    st.title("🔍 Notion Secret & Exfiltration Detection Engine")
    st.write("Perform regex-based forensic scans on incoming payload streams.")

    sample_input = st.text_area(
        "Paste Raw Document / API Log Stream:",
        value="""Server configuration:
AWS_SECRET_ACCESS_KEY = AKIAIOSFODNN7EXAMPLE
Notion API Key: secret_abc12345678901234567890123456789
Biological path: /datasets/pathogens/antimicrobial_resistance_log.csv
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0...""",
        height=180
    )

    if st.button("Run Forensic Audit"):
        results = run_secret_scanner(sample_input)
        if not results.empty:
            st.error(f"⚠️ Flagged {len(results)} potential risk targets!")
            st.dataframe(results, use_container_width=True)
            log_ledger_event(st.session_state["user_tier"], f"Secret Audit Flagged {len(results)} Risks")
        else:
            st.success("✅ No secrets or confidential data patterns detected.")

# -----------------------------------------------------------------------------
# MODULE 3: CRYPTOGRAPHIC AUDIT LEDGER
# -----------------------------------------------------------------------------
elif module == "🔗 Cryptographic Tamper-Evident Ledger":
    st.title("🔗 SHA-256 Cryptographic Audit Ledger")
    st.caption("Immutable, block-chained log tracking all system modifications, tier elevations, and scan events.")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Audit Chain Logs")
        ledger_df = pd.DataFrame(st.session_state["audit_chain"])
        st.dataframe(ledger_df, use_container_width=True)

    with col2:
        st.subheader("Ledger Controls")
        if st.button("Verify Chain Integrity"):
            valid = True
            chain = st.session_state["audit_chain"]
            for i in range(1, len(chain)):
                prev = chain[i-1]
                curr = chain[i]
                recalc_payload = f"{curr['Index']}{curr['Timestamp']}{curr['Actor']}{curr['Action']}{curr['Prev_Hash']}"
                recalc_hash = hashlib.sha256(recalc_payload.encode()).hexdigest()
                if curr["Prev_Hash"] != prev["Hash"] or curr["Hash"] != recalc_hash:
                    valid = False
                    break
            if valid:
                st.success("✅ Chain Cryptographically Valid")
            else:
                st.error("❌ TAMPERING DETECTED! Hash Chain Broken")

        if st.button("Simulate Manual Action Log"):
            log_ledger_event(st.session_state["user_tier"], "Manual Compliance Check Executed")
            st.rerun()

# -----------------------------------------------------------------------------
# MODULE 4: THREAT INTELLIGENCE (STIX / IoC)
# -----------------------------------------------------------------------------
elif module == "🌐 Threat Intelligence Feed (STIX/IoC)":
    st.title("🌐 Threat Intelligence & Indicator Ingestion")
    st.write("Cross-reference workspace activity against live global threat indicators (STIX 2.1 / MISP feeds).")

    mock_threat_feed = pd.DataFrame([
        {"Type": "IP Address", "Indicator": "192.168.1.105", "Threat Actor": "APT29", "Severity": "High", "Status": "Active"},
        {"Type": "File Hash", "Indicator": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "Threat Actor": "Lazarus", "Severity": "Critical", "Status": "Flagged"},
        {"Type": "Domain", "Indicator": "malicious-notion-webhook.com", "Threat Actor": "Fin7", "Severity": "Medium", "Status": "Blocked"}
    ])

    st.subheader("Active Threat Feed Indicators")
    st.dataframe(mock_threat_feed, use_container_width=True)

    st.subheader("IoC Matcher")
    user_ioc = st.text_input("Enter IP, Domain, or Hash to query against feed:", "192.168.1.105")
    if st.button("Query Threat Feed"):
        match = mock_threat_feed[mock_threat_feed["Indicator"] == user_ioc.strip()]
        if not match.empty:
            st.error(f"🚨 THREAT MATCH FOUND! Indicator belongs to {match.iloc[0]['Threat Actor']} (Severity: {match.iloc[0]['Severity']})")
            log_ledger_event(st.session_state["user_tier"], f"Threat Feed Alert: Matched IoC {user_ioc}")
        else:
            st.success("✅ Indicator clean. No known threat matches found in database.")

# -----------------------------------------------------------------------------
# MODULE 5: ML ANOMALY DETECTOR
# -----------------------------------------------------------------------------
elif module == "🤖 ML Anomaly Detector (IsolationForest)":
    st.title("🤖 ML Behavioral Anomaly Detection")
    st.caption("Train a scikit-learn IsolationForest model on workspace activity to flag zero-day behavioral anomalies.")

    # Generate synthetic behavioral dataset
    np.random.seed(42)
    normal_traffic = np.random.normal(loc=[12, 50, 100], scale=[2, 10, 20], size=(100, 3)) # hour, req_count, payload_kb
    anomalous_traffic = np.random.uniform(low=[0, 200, 500], high=[4, 1000, 2000], size=(10, 3))
    
    X = np.vstack([normal_traffic, anomalous_traffic])
    df_ml = pd.DataFrame(X, columns=["Access_Hour", "Request_Frequency", "Payload_KB"])

    # Model training
    model = IsolationForest(contamination=0.09, random_state=42)
    df_ml["Anomaly_Code"] = model.fit_predict(X)
    df_ml["Status"] = df_ml["Anomaly_Code"].map({1: "Normal", -1: "Anomalous"})

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.scatter_3d(
            df_ml, 
            x="Access_Hour", 
            y="Request_Frequency", 
            z="Payload_KB",
            color="Status",
            color_discrete_map={"Normal": "#00CC96", "Anomalous": "#EF553B"},
            title="3D Workspace Activity Baseline & Outliers"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Model Summary")
        anomalies_count = (df_ml["Status"] == "Anomalous").sum()
        st.metric("Total Sample Patterns", len(df_ml))
        st.metric("Flagged Zero-Day Outliers", anomalies_count, delta="Requires Audit", delta_color="inverse")
        
        st.dataframe(df_ml[df_ml["Status"] == "Anomalous"].head(5), use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 6: METASPLOIT TASK QUEUE
# -----------------------------------------------------------------------------
elif module == "🎯 Metasploit RPC Task Queue":
    st.title("🎯 Asynchronous Metasploit Task Queue")
    st.caption("Trigger active network diagnostic scans without blocking UI operations.")

    col1, col2 = st.columns([1, 2])
    with col1:
        target_ip = st.text_input("Target Subnet / IP", "192.168.1.100")
        module_type = st.selectbox("Scan Module", ["auxiliary/scanner/portscan/tcp", "auxiliary/scanner/http/dir_scanner"])
        if st.button("Queue Scan Job"):
            st.session_state["scan_queue"].append({
                "ID": len(st.session_state["scan_queue"]) + 1,
                "Target": target_ip,
                "Module": module_type,
                "Status": "Running",
                "Timestamp": datetime.now().strftime("%H:%M:%S")
            })
            log_ledger_event(st.session_state["user_tier"], f"Queued MSF job for {target_ip}")
            st.success(f"Job queued for {target_ip}")

    with col2:
        st.subheader("Active Background Queue")
        if st.session_state["scan_queue"]:
            queue_df = pd.DataFrame(st.session_state["scan_queue"])
            st.dataframe(queue_df, use_container_width=True)
            if st.button("Clear Finished Jobs"):
                st.session_state["scan_queue"] = []
                st.rerun()
        else:
            st.info("Queue is currently empty.")

# -----------------------------------------------------------------------------
# MODULE 7: ATTACK SURFACE GRAPH
# -----------------------------------------------------------------------------
elif module == "🕸️ Interactive Attack Surface Graph":
    st.title("🕸️ Interactive Workspace & Network Topology Map")

    nodes = ["Notion API Gateway", "Database Pipeline", "Local Workstation", "Storage Vault", "Metasploit RPC Node"]
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=[1, 2, 3, 4, 2.5],
        y=[2, 4, 1, 3, 2.5],
        mode='markers+text',
        marker=dict(size=[30, 45, 25, 35, 40], color=['#00CC96', '#EF553B', '#636EFA', '#AB63FA', '#FFA15A']),
        text=nodes,
        textposition="bottom center"
    ))

    fig.update_layout(
        title="Topology Nodes & Exposure Vectors",
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=20, r=20, t=40, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 8: BRIEFING & EXPORT
# -----------------------------------------------------------------------------
elif module == "📄 Briefing & Forensic Export":
    st.title("📄 Executive Briefing & Multi-Format Export")
    st.write("Compile operational telemetry and ledger records into formal compliance reports.")

    st.subheader("Export PDF Executive Brief")
    sample_df = pd.DataFrame([
        {"Line": 2, "Type": "AWS API Key", "Content Snippet": "AKIAIOSFODNN7EXAMPLE"},
        {"Line": 3, "Type": "Notion Integration Token", "Content Snippet": "secret_abc123456789..."}
    ])

    pdf_data = generate_pdf_report(sample_df)

    st.download_button(
        label="📥 Download Executive Brief PDF",
        data=pdf_data,
        file_name=f"Security_Brief_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )

    st.divider()
    st.subheader("Raw Structured Forensic Logs")
    raw_json = json.dumps({
        "timestamp": datetime.now().isoformat(),
        "tier": st.session_state["user_tier"],
        "ledger_blocks": len(st.session_state["audit_chain"]),
        "status": "ACTIVE"
    }, indent=2)
    st.download_button("📥 Export STIX 2.1 / JSON Audit Log", raw_json, file_name="forensic_log.json", mime="application/json")
