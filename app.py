import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import re
import io
import time
from datetime import datetime

# PDF Report Generation via ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# -----------------------------------------------------------------------------
# PAGE CONFIG & SESSION STATE
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Notion Live Analyzer & Security Dashboard",
    page_icon="🛡️",
    layout="wide"
)

if "user_tier" not in st.session_state:
    st.session_state["user_tier"] = "Admin"

if "scan_queue" not in st.session_state:
    st.session_state["scan_queue"] = []

# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION & PRIVILEGE TIER CONTROLS
# -----------------------------------------------------------------------------
st.sidebar.title("🛡️ Sovereign Engine")
st.sidebar.markdown(f"**Current Access:** `{st.session_state['user_tier']}`")

tier_option = st.sidebar.selectbox("Privilege Level Switcher", ["Admin", "Analyst", "Auditor"], index=0)
st.session_state["user_tier"] = tier_option

st.sidebar.divider()
st.sidebar.header("Navigation Modules")
module = st.sidebar.radio(
    "Select Module",
    [
        "📊 Live Analyzer Overview",
        "🔍 Notion Secret & Exfiltration Scanner",
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
    story.append(Paragraph("Security & Notion Forensic Brief", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
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
if module == "📊 Live Analyzer Overview":
    st.title("📊 Notion Workspace Real-Time Analyzer")
    st.caption("Active monitoring engine tracking API telemetry, sync state, and threat posture.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Sync Pipelines", "12/12", "Operational")
    col2.metric("Scan Frequency", "500ms", "-50ms optimal")
    col3.metric("Detected Anomalies", "3 Flags", "+1 pending review", delta_color="inverse")
    col4.metric("Vault Status", "Locked (TOTP Active)")

    st.subheader("Workspace Activity Feed")
    df = pd.DataFrame({
        "Timestamp": pd.date_range(end=pd.Timestamp.now(), periods=5, freq="min"),
        "Event": ["Page Edited", "Database Query", "API Token Auth", "External Webhook Call", "Permission Change"],
        "Actor": ["User_Admin", "Integration_Bot", "System_Process", "Automation_Engine", "User_Admin"],
        "Risk Score": ["Low", "Low", "Medium", "Low", "High"]
    })
    st.dataframe(df, use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 2: SECRET & EXFILTRATION SCANNER
# -----------------------------------------------------------------------------
elif module == "🔍 Notion Secret & Exfiltration Scanner":
    st.title("🔍 Notion Secret & Exfiltration Detection Engine")
    st.write("Scan Notion page payloads and database logs for inadvertent data exposures.")

    sample_input = st.text_area(
        "Paste Raw Notion Page Payload / Document Stream to Audit:",
        value="""Server configuration:
AWS_SECRET_ACCESS_KEY = AKIAIOSFODNN7EXAMPLE
Notion API Key: secret_abc12345678901234567890123456789
Biological path: /datasets/pathogens/antimicrobial_resistance_log.csv
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0...""",
        height=200
    )

    if st.button("Run Forensic Regex Audit"):
        results = run_secret_scanner(sample_input)
        if not results.empty:
            st.error(f"⚠️ Flagged {len(results)} potential risk targets!")
            st.dataframe(results, use_container_width=True)
        else:
            st.success("✅ No secrets or confidential data patterns detected.")

# -----------------------------------------------------------------------------
# MODULE 3: METASPLOIT TASK QUEUE
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
# MODULE 4: ATTACK SURFACE GRAPH
# -----------------------------------------------------------------------------
elif module == "🕸️ Interactive Attack Surface Graph":
    st.title("🕸️ Interactive Workspace & Network Topology Map")

    nodes = ["Notion API Gateway", "Database Pipeline", "Local Workstation", "Storage Vault", "Metasploit RPC Node"]
    fig = go.Figure()

    # Add network visualization nodes
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
# MODULE 5: BRIEFING & EXPORT
# -----------------------------------------------------------------------------
elif module == "📄 Briefing & Forensic Export":
    st.title("📄 Executive Briefing & Multi-Format Export")
    st.write("Compile real-time operational state into standard reporting formats.")

    st.subheader("Export PDF Executive Summary")
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
    st.subheader("Raw Forensic Structured Export")
    raw_json = json.dumps({"timestamp": datetime.now().isoformat(), "tier": st.session_state["user_tier"], "status": "ACTIVE"}, indent=2)
    st.download_button("📥 Export STIX 2.1 / JSON Audit Log", raw_json, file_name="forensic_log.json", mime="application/json")
