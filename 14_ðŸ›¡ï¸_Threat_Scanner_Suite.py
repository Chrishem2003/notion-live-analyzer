import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
"""
🛡️ Threat & Scanner Suite � Enterprise Production Grade (Fully Functional)
PII/secret scanning, CVE vulnerability checks, YARA-lite malware signatures, file integrity
monitoring, TCP port probes with mandatory authorization guardrails, threat intelligence lookups,
and incident response playbooks. Built on actual underlying operational module implementations.
"""

import io
import os
import json
import socket
import datetime
import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import get_active_dataframe
from modules.shared_ui import hero_card, section_header, metric_card, render_export_buttons
from modules.scanner_engine import (
    scan_pii,
    scan_cve_packages,
    scan_yara_lite,
    scan_duplicates,
    create_integrity_baseline,
    verify_integrity,
    scan_host_ports,
    hash_reputation_lookup,
)
from modules.threat_intel import (
    check_ip_reputation,
    domain_whois,
    analyze_url,
    aggregate_threat_geodata,
    run_incident_playbook,
)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def render_pii_tab():
    section_header("🔍 Enterprise PII & Secret Scanner", "Scan datasets and raw strings for regulated Personally Identifiable Information (GDPR/HIPAA), credit cards, SSNs, and hardcoded API secrets.")

    source_mode = st.radio("Data Source", ["Active Session Dataset", "Upload New File", "Paste Raw Text"], horizontal=True, key="ts_pii_source_mode")

    df = None
    raw_text = ""

    if source_mode == "Active Session Dataset":
        df = get_active_dataframe()
        if df is None:
            st.info("ℹ️ No active dataset loaded in this session � load one via Data Studio, or switch to 'Upload New File' / 'Paste Raw Text' above.")
        else:
            st.caption(f"Scanning the currently active dataset: {df.shape[0]:,}} rows × {df.shape[1]}} columns.")
    elif source_mode == "Upload New File":
        uploaded = st.file_uploader("Upload structured dataset for PII inspection", type=["csv", "xlsx", "json"], key="ts_pii_upload_upg")
        if uploaded is not None:
            try:
                ext = uploaded.name.rsplit(".", 1)[-1].lower()
                if ext == "csv":
                    df = pd.read_csv(io.BytesIO(uploaded.getvalue()))
                elif ext in ("xlsx", "xls"):
                    df = pd.read_excel(uploaded)
                elif ext == "json":
                    df = pd.read_json(uploaded)
            except Exception as e:
                st.error(f"⚠️ Failed to parse uploaded file: {e}}")
    else:
        raw_text = st.text_area(
            "Paste unstructured raw text stream",
            placeholder="Paste text payload containing emails, tokens, IP addresses, or secrets...",
            height=140,
            key="ts_pii_text_upg",
        )

    col_sel = st.selectbox("Target Column for Scanning", df.columns.tolist() if df is not None else ["(Whole Dataset Ingestion)"], key="ts_pii_col_upg")

    if st.button("🔍 Execute Comprehensive PII Scan", key="ts_pii_run_upg", type="primary"):
        with st.spinner("Analyzing byte patterns against regulatory PII and secret signatures..."):
            if df is not None and col_sel != "(Whole Dataset Ingestion)":
                result = scan_pii(df=df, column=col_sel)
            else:
                result = scan_pii(df=df if df is not None else None, text=raw_text)

        overall = result.get("overall", "CLEAN")
        if "CRITICAL" in overall:
            st.error(f"🚨 **{overall}}** � Detected {result.get('total_matches', 0):,}} severe compliance violations.")
        elif "REVIEW" in overall:
            st.warning(f"⚠️ **{overall}}** � Potential exposure vectors identified.")
        else:
            st.success(f"? **{overall}}** � No regulatory compliance breaches detected.")

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Findings", result.get("total_findings", 0))
        c2.metric("Total Matches", result.get("total_matches", 0))
        c3.metric("Compliance Status", overall)

        if result.get("findings"):
            st.markdown("#### Detailed Findings Breakdown")
            for f in result["findings"]:
                with st.expander(f"⚠️ {f.get('type', 'Unknown')}} � {f.get('count', 0)}} match(es) [Risk Level: {f.get('risk', 'MODERATE')}}]"):
                    st.write("Discovered Samples:", f.get("samples", []))

        st.info(f"**Mitigation Recommendation:** {result.get('recommendation', 'Ensure proper token masking and encryption at rest.')}}")


def render_cve_tab():
    section_header("🐞 Live CVE Vulnerability Assessment Engine", "Query real-time dependency vulnerabilities against the National Vulnerability Database (NVD) feeds.")

    with st.expander("📄 This Deployment's Real requirements.txt (for cross-checking scan scope)"):
        req_path = "requirements.txt"
        if os.path.exists(req_path):
            with open(req_path, "r") as f:
                req_content = f.read()
            st.code(req_content, language="text")
            st.caption("Compare this against the scan results below to confirm coverage � the scanner call itself takes no parameters from this page, so this is the honest way to verify scope.")
        else:
            st.info("No `requirements.txt` found at the app root from this page's working directory.")

    if st.button("🔍 Execute Live CVE Vulnerability Scan", key="ts_cve_run_upg", type="primary"):
        with st.spinner("Polling NVD Vulnerability Database and local dependency tree..."):
            result = scan_cve_packages()

        st.info(f"Database Feed Source: **{result.get('source', 'NVD Local Cache')}}** | Packages Analyzed: `{result.get('package_count', 0)}}`")

        c1, c2, c3 = st.columns(3)
        c1.metric("Critical / Review Items", result.get("critical_count", 0))
        c2.metric("Secure Dependencies", result.get("secure_count", 0))
        c3.metric("Total Vulnerabilities", len(result.get("vulnerabilities", [])))

        vulnerabilities = result.get("vulnerabilities", [])
        if vulnerabilities:
            df_vuln = pd.DataFrame(vulnerabilities)
            st.dataframe(df_vuln, use_container_width=True, hide_index=True)
            render_export_buttons(df_vuln, base_name="cve_vulnerability_report")
        else:
            st.success("? All scanned packages are up to date with zero known CVE advisories.")


def render_yara_tab():
    section_header("🕷️ YARA-Lite Malware & Exploit Signature Scanner", "Scan uploaded evidentiary artifacts against advanced malware signatures, ransomware strings, and exploit payloads.")

    uploaded = st.file_uploader("Upload binary artifact for signature inspection", key="ts_yara_upload_upg")
    if uploaded is None:
        st.info("ℹ️ Upload a file to execute signature scanning.")
        return

    if st.button("🔬 Execute YARA Signature Scan", key="ts_yara_run_upg", type="primary"):
        data = uploaded.read()
        with st.spinner("Matching byte streams against YARA heuristic ruleset..."):
            result = scan_yara_lite(data, uploaded.name)

        if result.get("clean", True):
            st.success(f"? **{result.get('verdict', 'CLEAN')}}** � Analyzed `{result.get('bytes_scanned', 0):,}}` bytes with zero signature matches.")
        else:
            st.error(f"🚨 **{result.get('verdict', 'THREAT DETECTED')}}**")
            st.markdown("#### Triggered Signature Rules")
            for f in result.get("findings", []):
                st.warning(f"• **Rule:** `{f.get('rule')}}` | **Severity:** `{f.get('severity')}}`")


def render_integrity_tab():
    section_header("🔐 File Integrity Monitoring & Change Tracker (FIM)", "Establish SHA-256 baseline hashes for critical system assets and instantly detect unauthorized filesystem modifications.")

    default_files = "app.py,portal.py,requirements.txt,1___Home_Dashboard.py,10____Admin_Security_Center.py"
    paths_input = st.text_area("Monitored File Paths (Comma-Separated)", value=default_files, key="ts_int_paths_upg")
    st.caption("Adjust this list to match the actual entry points and critical files in your deployment.")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📸 Establish Cryptographic Baseline", key="ts_int_create_upg", type="primary"):
            paths = [p.strip() for p in paths_input.split(",") if p.strip()]
            missing = [p for p in paths if not os.path.exists(p)]
            if missing:
                st.warning(f"⚠️ These paths don't exist from the app's working directory and will be skipped: {', '.join(missing)}}")
            result = create_integrity_baseline(paths)
            st.success(f"? Baseline established successfully for `{result.get('baseline_files', 0)}}` critical system files.")

    with col_b:
        if st.button("? Verify File Integrity Ledger", key="ts_int_verify_upg", type="primary"):
            result = verify_integrity()
            if result.get("changed_or_deleted", 0) == 0:
                st.success(f"🔐 **{result.get('verdict', 'INTEGRITY VERIFIED')}}** � `{result.get('verified_unchanged', 0)}}` files verified unchanged.")
            else:
                st.warning(f"⚠️ **{result.get('verdict', 'MODIFICATIONS DETECTED')}}**")
                changes = result.get("changes", [])
                if changes:
                    df_changes = pd.DataFrame(changes)
                    st.dataframe(df_changes, use_container_width=True, hide_index=True)


def render_port_tab():
    section_header("🖧 Network Port Scanner & Socket Probe", "Execute real TCP socket connection scans across target hosts with mandatory authorization guardrails.")

    st.warning("⚠️ **Strict Authorization Notice:** Ethical use only. Only scan systems, IP addresses, or infrastructure you own or possess explicit written authorization to test.")
    target = st.text_input("Target Host Address / IP", value="127.0.0.1", key="ts_port_host_upg")
    authorized = st.checkbox("I legally certify that I possess explicit authorization to scan this target host", key="ts_port_auth_upg")

    if st.button("🖧 Execute Port Scan Probe", key="ts_port_run_upg", type="primary"):
        if not authorized:
            st.error("🚨 Authorization confirmation required prior to executing network scans.")
        else:
            with st.spinner(f"Probing standard TCP ports on `{target}}`..."):
                result = scan_host_ports(target, timeout=0.8)

            c1, c2 = st.columns(2)
            c1.metric("Open Ports Discovered", len(result.get("open_ports", [])))
            c2.metric("Total Ports Probed", result.get("ports_scanned", 0))

            open_ports = result.get("open_ports", [])
            if open_ports:
                st.markdown("#### Discovered Open Ports")
                df_ports = pd.DataFrame([r for r in result.get("results", []) if r.get("status") == "OPEN"])
                st.dataframe(df_ports, use_container_width=True, hide_index=True)
                render_export_buttons(df_ports, base_name=f"port_scan_{target}}")
            else:
                st.success("? No open ports discovered among standard vectors.")


def render_threat_tab():
    section_header("🛡️ Global Threat Intelligence Hub", "Cross-reference IP reputation feeds, extract domain WHOIS registration intelligence, and run heuristic phishing URL analysis.")

    tab_ip, tab_domain, tab_url = st.tabs(["🌐 IP Reputation", "🏷️ Domain WHOIS", "🔗 URL Phishing Analyzer"])

    with tab_ip:
        ip = st.text_input("Target IP Address", value="8.8.8.8", key="ts_threat_ip_upg")
        if st.button("🔍 Query IP Reputation", key="ts_threat_ip_run_upg", type="primary"):
            result = check_ip_reputation(ip)
            risk = result.get("risk", "LOW")
            if risk == "HIGH":
                st.error(f"🚨 Threat Risk Assessment: **{risk}}** � Abuse Confidence Score: `{result.get('abuse_confidence', 0)}}%`")
            elif risk == "MEDIUM":
                st.warning(f"⚠️ Threat Risk Assessment: **{risk}}** � Abuse Confidence Score: `{result.get('abuse_confidence', 0)}}%`")
            else:
                st.success(f"? Threat Risk Assessment: **{risk}}** � Clean Reputation.")
            st.json({k: v for k, v in result.items() if k != "risk"})

    with tab_domain:
        domain = st.text_input("Target Domain Name", value="example.com", key="ts_threat_domain_upg")
        if st.button("🔍 Execute WHOIS Lookup", key="ts_threat_domain_run_upg", type="primary"):
            result = domain_whois(domain)
            if "error" in result:
                st.error(f"🚨 WHOIS Lookup Error: {result['error']}}")
            else:
                st.success(f"? Domain Record Retrieved: **{result.get('domain', domain)}}**")
                st.json({k: v for k, v in result.items() if k != "domain"})

    with tab_url:
        url = st.text_input("Suspicious URL Payload", value="http://paypal-secure-login.xyz/verify", key="ts_threat_url_upg")
        if st.button("🔍 Analyze URL Phishing Vectors", key="ts_threat_url_run_upg", type="primary"):
            result = analyze_url(url)
            risk = result.get("risk", "LOW")
            if risk == "HIGH":
                st.error(f"🚨 **{result.get('verdict', 'Malicious URL')}}** � Risk Score: `{result.get('risk_score', 0)}} / 100`")
            elif risk == "MEDIUM":
                st.warning(f"⚠️ **{result.get('verdict', 'Suspicious URL')}}**")
            else:
                st.success(f"? **{result.get('verdict', 'Clean URL')}}**")

            st.markdown("#### Heuristic Findings")
            for f in result.get("findings", []):
                st.markdown(f"• {f}}")
            st.caption(f"**Recommendation:** {result.get('recommendation', 'Block domain at gateway.')}}")


def render_playbook_tab():
    section_header("?? Automated Incident Response Playbooks", "Generate structured triage workflows, containment checklists, and remediation steps for active security incidents.")

    incident = st.selectbox("Select Incident Classification", [
        "Brute-Force Attack", "Phishing Campaign", "Malware Detection",
        "Data Breach / PII Exposure", "DDoS / Resource Exhaustion",
    ], key="ts_pb_type_upg")

    context = st.text_area("Incident Context & Telemetry Notes (Optional)", height=80, key="ts_pb_ctx_upg")

    if st.button("🚀 Generate Incident Response Playbook", key="ts_pb_run_upg", type="primary"):
        result = run_incident_playbook(incident, context)
        st.success(f"? Playbook **{result.get('playbook_id', 'IR-001')}}** generated successfully � Assessed Severity: **{result.get('severity_assessment', 'HIGH')}}**")
        st.markdown("#### ?? Structured Containment & Response Steps")
        for i, step in enumerate(result.get("steps", []), 1):
            st.markdown(f"**{i}}.** {step}}")
        st.caption(f"Generated Timestamp (UTC): {result.get('created', datetime.datetime.now(datetime.UTC).isoformat())}}")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription(hub_id="threat")

    setup_page("Threat & Scanner Suite", "🛡️", initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "🛡️ Threat & Scanner Suite � Premium Security Operations",
        "Regulated PII scanning connected to your active dataset, live CVE vulnerability feeds with an honest scope cross-check, YARA malware signature detection, file integrity monitoring against real files, TCP port probes, and automated incident response playbooks.",
        badge_text="THREAT & SCANNER SUITE • SECURITY OPS",
    )

    tabs = st.tabs([
        "🔍 PII Scanner",
        "🐞 CVE Scanner",
        "🕷️ Malware Scan",
        "🔐 Integrity FIM",
        "🖧 Port Scan",
        "🛡️ Threat Intel",
        "?? Playbooks",
    ])

    with tabs[0]:
        render_pii_tab()
    with tabs[1]:
        render_cve_tab()
    with tabs[2]:
        render_yara_tab()
    with tabs[3]:
        render_integrity_tab()
    with tabs[4]:
        render_port_tab()
    with tabs[5]:
        render_threat_tab()
    with tabs[6]:
        render_playbook_tab()

    render_standard_footer("THREAT & SCANNER SUITE")


if __name__ == "__main__":
    main()


