import io
import os
import sys
import json
import asyncio
import datetime
import pandas as pd
import streamlit as st

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

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


def safe_load_dataset(uploaded_file) -> pd.DataFrame | None:
    """Safely parse uploaded datasets without crashing session runtime."""
    try:
        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        if ext == "csv":
            return pd.read_csv(uploaded_file)
        elif ext in ("xlsx", "xls"):
            return pd.read_excel(uploaded_file)
        elif ext == "json":
            content = uploaded_file.getvalue().decode("utf-8")
            return pd.read_json(io.StringIO(content))
    except Exception as err:
        st.error(f"⚠️ Data Parsing Error: {err}")
        return None


def render_pii_tab():
    section_header(
        "🔎 Enterprise PII & Secret Scanner",
        "Scan datasets and raw strings for regulated Personally Identifiable Information (GDPR/HIPAA), credit cards, SSNs, and hardcoded API secrets.",
    )

    source_mode = st.radio(
        "Data Source",
        ["Active Session Dataset", "Upload New File", "Paste Raw Text"],
        horizontal=True,
        key="ts_pii_src_mode_v2",
    )

    df = None
    raw_text = ""

    if source_mode == "Active Session Dataset":
        df = get_active_dataframe()
        if df is None:
            st.info("ℹ️ No active dataset loaded in this session. Switch to 'Upload New File' or 'Paste Raw Text'.")
        else:
            st.caption(f"Active dataset: {df.shape[0]:,} rows × {df.shape[1]} columns.")
    elif source_mode == "Upload New File":
        uploaded = st.file_uploader(
            "Upload structured dataset for PII inspection",
            type=["csv", "xlsx", "json"],
            key="ts_pii_file_upg_v2",
        )
        if uploaded:
            df = safe_load_dataset(uploaded)
    else:
        raw_text = st.text_area(
            "Paste unstructured raw text stream",
            placeholder="Paste text payload containing emails, tokens, IP addresses, or secrets...",
            height=140,
            key="ts_pii_text_upg_v2",
        )

    columns = df.columns.tolist() if df is not None else []
    col_sel = st.selectbox(
        "Target Column for Scanning",
        ["(Whole Dataset Ingestion)"] + columns if columns else ["(Whole Dataset Ingestion)"],
        key="ts_pii_col_upg_v2",
    )

    if st.button("🔎 Execute Comprehensive PII Scan", key="ts_pii_run_v2", type="primary"):
        with st.spinner("Analyzing data vectors against compliance signatures..."):
            target_col = None if col_sel == "(Whole Dataset Ingestion)" else col_sel
            result = scan_pii(df=df, column=target_col, text=raw_text if df is None else "")

        overall = result.get("overall", "CLEAN")
        if "CRITICAL" in overall:
            st.error(f"🚨 **{overall}** — Detected {result.get('total_matches', 0):,} compliance violations.")
        elif "REVIEW" in overall:
            st.warning(f"⚠️ **{overall}** — Potential exposure vectors identified.")
        else:
            st.success(f"✅ **{overall}** — No regulatory compliance breaches detected.")

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Findings", result.get("total_findings", 0))
        c2.metric("Total Matches", result.get("total_matches", 0))
        c3.metric("Compliance Status", overall)

        if result.get("findings"):
            st.markdown("#### Detailed Findings Breakdown")
            for finding in result["findings"]:
                with st.expander(
                    f"⚠️ {finding.get('type', 'Unknown')} — {finding.get('count', 0)} match(es) "
                    f"[Risk Level: {finding.get('risk', 'MODERATE')}]"
                ):
                    st.write("Discovered Samples:", finding.get("samples", []))

        st.info(f"**Mitigation Recommendation:** {result.get('recommendation', 'Ensure token masking and encryption at rest.')}")


def render_cve_tab():
    section_header(
        "👾 Live CVE Vulnerability Assessment Engine",
        "Query real-time dependency vulnerabilities against NVD feeds.",
    )

    with st.expander("📄 Real requirements.txt Scope Check"):
        req_path = "requirements.txt"
        if os.path.exists(req_path):
            with open(req_path, "r", encoding="utf-8") as f:
                st.code(f.read(), language="text")
        else:
            st.info("No `requirements.txt` found at the application root.")

    if st.button("🔎 Execute Live CVE Vulnerability Scan", key="ts_cve_run_v2", type="primary"):
        with st.spinner("Querying vulnerability database and dependency tree..."):
            result = scan_cve_packages()

        st.info(f"Feed Source: **{result.get('source', 'NVD Local Cache')}** | Packages Analyzed: `{result.get('package_count', 0)}`")

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
            st.success("✅ All dependencies are up to date with zero known CVE advisories.")


def render_yara_tab():
    section_header(
        "🕷️ YARA-Lite Malware & Exploit Signature Scanner",
        "Scan uploaded artifacts against malware signatures and exploit payloads.",
    )

    uploaded = st.file_uploader("Upload binary artifact for signature inspection", key="ts_yara_upload_v2")
    if not uploaded:
        st.info("ℹ️ Upload a file to execute signature scanning.")
        return

    if st.button("🔬 Execute YARA Signature Scan", key="ts_yara_run_v2", type="primary"):
        with st.spinner("Matching byte streams against rulesets..."):
            data = uploaded.getbuffer()
            result = scan_yara_lite(data, uploaded.name)

        if result.get("clean", True):
            st.success(f"✅ **{result.get('verdict', 'CLEAN')}** — Analyzed `{result.get('bytes_scanned', 0):,}` bytes with zero matches.")
        else:
            st.error(f"🚨 **{result.get('verdict', 'THREAT DETECTED')}**")
            for f in result.get("findings", []):
                st.warning(f"• **Rule:** `{f.get('rule')}` | **Severity:** `{f.get('severity')}`")


def render_integrity_tab():
    section_header(
        "🔍 File Integrity Monitoring & Change Tracker (FIM)",
        "Establish SHA-256 baseline hashes for system assets to detect unauthorized changes.",
    )

    default_files = "app.py,portal.py,requirements.txt,1___Home_Dashboard.py,10____Admin_Security_Center.py"
    paths_input = st.text_area("Monitored File Paths (Comma-Separated)", value=default_files, key="ts_int_paths_v2")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📸 Establish Baseline", key="ts_int_create_v2", type="primary"):
            paths = [p.strip() for p in paths_input.split(",") if p.strip()]
            missing = [p for p in paths if not os.path.exists(p)]
            if missing:
                st.warning(f"⚠️ Skipping missing paths: {', '.join(missing)}")
            result = create_integrity_baseline(paths)
            st.success(f"✅ Baseline established for `{result.get('baseline_files', 0)}` assets.")

    with col_b:
        if st.button("✅ Verify Ledger Integrity", key="ts_int_verify_v2", type="primary"):
            result = verify_integrity()
            if result.get("changed_or_deleted", 0) == 0:
                st.success(f"🔍 **{result.get('verdict', 'INTEGRITY VERIFIED')}** — `{result.get('verified_unchanged', 0)}` files intact.")
            else:
                st.warning(f"⚠️ **{result.get('verdict', 'MODIFICATIONS DETECTED')}**")
                if changes := result.get("changes", []):
                    st.dataframe(pd.DataFrame(changes), use_container_width=True, hide_index=True)


def render_port_tab():
    section_header(
        "🖥️ Network Port Scanner & Socket Probe",
        "Execute asynchronous TCP socket connection scans with explicit authorization checks.",
    )

    st.warning("⚠️ **Strict Authorization Notice:** Ethical use only. Only scan systems you own or have permission to test.")
    target = st.text_input("Target Host Address / IP", value="127.0.0.1", key="ts_port_host_v2")
    authorized = st.checkbox("I certify explicit authorization to scan this host", key="ts_port_auth_v2")

    if st.button("🖥️ Execute Port Scan Probe", key="ts_port_run_v2", type="primary"):
        if not authorized:
            st.error("🚨 Authorization confirmation is required.")
            return

        with st.spinner(f"Probing network vectors on `{target}`..."):
            result = scan_host_ports(target, timeout=0.8)

        c1, c2 = st.columns(2)
        c1.metric("Open Ports Discovered", len(result.get("open_ports", [])))
        c2.metric("Total Ports Probed", result.get("ports_scanned", 0))

        if open_ports := result.get("open_ports", []):
            df_ports = pd.DataFrame([r for r in result.get("results", []) if r.get("status") == "OPEN"])
            st.dataframe(df_ports, use_container_width=True, hide_index=True)
            render_export_buttons(df_ports, base_name=f"port_scan_{target}")
        else:
            st.success("✅ No open ports discovered.")


def render_threat_tab():
    section_header(
        "🛡️ Global Threat Intelligence Hub",
        "Cross-reference threat feeds, domain registration WHOIS, and phishing indicators.",
    )

    tab_ip, tab_domain, tab_url = st.tabs(["🌐 IP Reputation", "🏷️ Domain WHOIS", "🔗 Phishing Analyzer"])

    with tab_ip:
        ip = st.text_input("Target IP Address", value="8.8.8.8", key="ts_ip_input_v2")
        if st.button("🔎 Query IP Reputation", key="ts_ip_run_v2", type="primary"):
            result = check_ip_reputation(ip)
            risk = result.get("risk", "LOW")
            if risk == "HIGH":
                st.error(f"🚨 Risk Level: **{risk}** — Confidence: `{result.get('abuse_confidence', 0)}%`")
            elif risk == "MEDIUM":
                st.warning(f"⚠️ Risk Level: **{risk}** — Confidence: `{result.get('abuse_confidence', 0)}%`")
            else:
                st.success(f"✅ Risk Level: **{risk}** — Clean Reputation.")
            st.json({k: v for k, v in result.items() if k != "risk"})

    with tab_domain:
        domain = st.text_input("Target Domain", value="example.com", key="ts_domain_input_v2")
        if st.button("🔎 Execute WHOIS Query", key="ts_domain_run_v2", type="primary"):
            result = domain_whois(domain)
            if "error" in result:
                st.error(f"🚨 WHOIS Error: {result['error']}")
            else:
                st.success(f"✅ Record Retrieved for: **{result.get('domain', domain)}**")
                st.json({k: v for k, v in result.items() if k != "domain"})

    with tab_url:
        url = st.text_input("Suspicious URL", value="http://paypal-secure-login.xyz/verify", key="ts_url_input_v2")
        if st.button("🔎 Analyze Phishing Risk", key="ts_url_run_v2", type="primary"):
            result = analyze_url(url)
            risk = result.get("risk", "LOW")
            if risk == "HIGH":
                st.error(f"🚨 **{result.get('verdict', 'Malicious')}** — Score: `{result.get('risk_score', 0)}/100`")
            elif risk == "MEDIUM":
                st.warning(f"⚠️ **{result.get('verdict', 'Suspicious')}**")
            else:
                st.success(f"✅ **{result.get('verdict', 'Clean')}**")

            st.markdown("#### Heuristic Analysis")
            for item in result.get("findings", []):
                st.markdown(f"• {item}")


def render_playbook_tab():
    section_header(
        "📋 Automated Incident Response Playbooks",
        "Generate triage workflows, containment checklists, and remediation procedures.",
    )

    incident = st.selectbox(
        "Incident Classification",
        [
            "Brute-Force Attack",
            "Phishing Campaign",
            "Malware Detection",
            "Data Breach / PII Exposure",
            "DDoS / Resource Exhaustion",
        ],
        key="ts_pb_type_v2",
    )

    context = st.text_area("Incident Telemetry & Notes", height=80, key="ts_pb_ctx_v2")

    if st.button("🚀 Generate Response Playbook", key="ts_pb_run_v2", type="primary"):
        result = run_incident_playbook(incident, context)
        st.success(
            f"✅ Playbook **{result.get('playbook_id', 'IR-001')}** generated — "
            f"Assessed Severity: **{result.get('severity_assessment', 'HIGH')}**"
        )
        st.markdown("#### 📋 Containment & Mitigation Workflow")
        for idx, step in enumerate(result.get("steps", []), 1):
            st.markdown(f"**{idx}.** {step}")
        
        utc_now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        st.caption(f"Generated Timestamp (UTC): {result.get('created', utc_now)}")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription(hub_id="threat")

    setup_page("Threat & Scanner Suite", "🛡️", initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "🛡️ Threat & Scanner Suite — Premium Security Operations",
        "Enterprise-grade security engine for automated PII detection, CVE dependency audits, YARA malware signatures, File Integrity Monitoring (FIM), and threat intelligence orchestration.",
        badge_text="THREAT & SCANNER SUITE • SEC OPS",
    )

    tabs = st.tabs([
        "🔎 PII Scanner",
        "👾 CVE Scanner",
        "🕷️ Malware Scan",
        "🔍 Integrity FIM",
        "🖥️ Port Scan",
        "🛡️ Threat Intel",
        "📋 Playbooks",
    ])

    tab_renderers = [
        render_pii_tab,
        render_cve_tab,
        render_yara_tab,
        render_integrity_tab,
        render_port_tab,
        render_threat_tab,
        render_playbook_tab,
    ]

    for tab, renderer in zip(tabs, tab_renderers):
        with tab:
            renderer()

    render_standard_footer("THREAT & SCANNER SUITE")


if __name__ == "__main__":
    main()
