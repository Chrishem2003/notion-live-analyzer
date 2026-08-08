"""
🛡️ Threat & Scanner Suite
 Advanced threat intelligence, security scanning, and incident response.
"""

import io
import json

import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import hero_card, section_header
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


def render_pii_tab():
    """Tab: PII & secret scanner."""
    section_header("🔍 PII & Secret Scanner", "Scan datasets/text for emails, SSNs, credit cards, API keys, and secrets (GDPR/HIPAA readiness).")

    uploaded = st.file_uploader("Upload dataset to scan (optional)", type=["csv", "xlsx", "json"], key="ts_pii_upload")
    raw_text = st.text_area(
        "Or paste raw text to scan",
        placeholder="Copy text containing emails, SSNs, API keys...",
        height=140,
        key="ts_pii_text",
    )

    df = None
    if uploaded is not None:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded) if uploaded.name.endswith((".xlsx", ".xls")) else pd.read_json(uploaded)
        except Exception as e:
            st.error(f"Could not load file: {e}")

    col_sel = st.selectbox("Column to scan (if dataset loaded)", df.columns.tolist() if df is not None else ["(whole dataset)"], key="ts_pii_col")

    if st.button("🔍 Run PII Scan", key="ts_pii_run", type="primary"):
        with st.spinner("Scanning for PII and secrets..."):
            if df is not None and col_sel != "(whole dataset)":
                result = scan_pii(df=df, column=col_sel)
            else:
                result = scan_pii(df=df if df is not None else None, text=raw_text)

        overall = result["overall"]
        if overall.startswith("CRITICAL"):
            st.error(f"🚨 **{overall}** — {result['total_matches']} matches found")
        elif overall == "REVIEW NEEDED":
            st.warning(f"⚠️ **{overall}**")
        else:
            st.success(f"✅ **{overall}**")

        c1, c2 = st.columns(2)
        c1.metric("Findings", result["total_findings"])
        c2.metric("Total Matches", result["total_matches"])

        if result["findings"]:
            st.markdown("#### Findings Detail")
            for f in result["findings"]:
                with st.expander(f"{f['type']} — {f['count']} match(es) [{f['risk']}]"):
                    st.write("Samples:", f["samples"])
        st.caption(result["recommendation"])


def render_cve_tab():
    """Tab: CVE vulnerability scanner."""
    section_header("🐞 Live CVE Vulnerability Scanner", "Real-time dependency vulnerability scanning against the NVD database.")

    if st.button("🔍 Run Live CVE Scan", key="ts_cve_run", type="primary"):
        with st.spinner("Querying NVD Vulnerability Database..."):
            result = scan_cve_packages()
        st.info(f"Source: **{result['source']}** | {result['package_count']} packages scanned")
        c1, c2 = st.columns(2)
        c1.metric("Critical/Review", result["critical_count"])
        c2.metric("Secure", result["secure_count"])
        st.dataframe(result["vulnerabilities"], use_container_width=True, hide_index=True)


def render_yara_tab():
    """Tab: YARA-lite signature scanner."""
    section_header("🕷️ YARA-lite Signature Scanner", "Scan files for malware, ransomware, and exploit indicators.")

    uploaded = st.file_uploader("Upload a file to scan", key="ts_yara_upload")
    if uploaded is None:
        st.info("Upload a file to run signature scanning.")
        return

    if st.button("🔬 Run Signature Scan", key="ts_yara_run", type="primary"):
        data = uploaded.read()
        with st.spinner("Scanning signatures..."):
            result = scan_yara_lite(data, uploaded.name)
        if result["clean"]:
            st.success(f"✅ **{result['verdict']}** — {result['bytes_scanned']:,} bytes scanned")
        else:
            st.error(f"🚨 **{result['verdict']}**")
            st.markdown("#### Detected Signatures")
            for f in result["findings"]:
                st.warning(f"• **{f['rule']}** [{f['severity']}]")


def render_integrity_tab():
    """Tab: File integrity baseline."""
    section_header("🔐 File Integrity & Change Tracker", "Create SHA-256 baselines and detect file modifications over time.")

    default_files = "app.py,requirements.txt,portal.py,main.py,agents.py"
    paths_input = st.text_area("File paths (comma-separated)", value=default_files, key="ts_int_paths")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📸 Create Baseline", key="ts_int_create", type="primary"):
            paths = [p.strip() for p in paths_input.split(",") if p.strip()]
            result = create_integrity_baseline(paths)
            st.success(f"Baseline created for {result['baseline_files']} files.")
    with col_b:
        if st.button("✅ Verify Integrity", key="ts_int_verify", type="primary"):
            result = verify_integrity()
            if result["changed_or_deleted"] == 0:
                st.success(f"✅ **{result['verdict']}** — {result['verified_unchanged']} files unchanged")
            else:
                st.warning(f"⚠️ **{result['verdict']}**")
                if result["changes"]:
                    st.dataframe(pd.DataFrame(result["changes"]), use_container_width=True, hide_index=True)


def render_port_tab():
    """Tab: Port scanner."""
    section_header("🖧 Network Port Scanner", "Real TCP port scanning with ethical-use guardrails.")

    st.warning("⚠️ **Authorization required.** Only scan systems you own or have explicit permission to test.")
    target = st.text_input("Target host/IP", value="127.0.0.1", key="ts_port_host")
    authorized = st.checkbox("I confirm I have authorization to scan this target", key="ts_port_auth")

    if st.button("🖧 Run Port Scan", key="ts_port_run", type="primary"):
        if not authorized:
            st.error("You must confirm authorization before scanning.")
        else:
            with st.spinner(f"Scanning common ports on {target}..."):
                result = scan_host_ports(target, timeout=1.0)
            st.metric("Open Ports", result["open_ports"], delta=f"{result['ports_scanned']} scanned")
            if result["open_ports"]:
                st.markdown("#### Open Ports")
                open_ports_df = pd.DataFrame([r for r in result["results"] if r["status"] == "OPEN"])
                st.dataframe(open_ports_df, use_container_width=True, hide_index=True)


def render_threat_tab():
    """Tab: Threat intelligence."""
    section_header("🛡️ Threat Intelligence", "IP reputation, domain WHOIS, and URL phishing analysis.")

    tab_ip, tab_domain, tab_url = st.tabs(["🌐 IP Reputation", "🏷️ WHOIS/Domain", "🔗 URL Analyzer"])

    with tab_ip:
        ip = st.text_input("IP address", value="8.8.8.8", key="ts_threat_ip")
        if st.button("🔍 Check IP", key="ts_threat_ip_run", type="primary"):
            result = check_ip_reputation(ip)
            risk = result.get("risk", "LOW")
            if risk == "HIGH":
                st.error(f"🚨 Risk: **{risk}** — abuse confidence {result.get('abuse_confidence', 0)}")
            elif risk == "MEDIUM":
                st.warning(f"⚠️ Risk: **{risk}** — abuse confidence {result.get('abuse_confidence', 0)}")
            else:
                st.success(f"✅ Risk: **{risk}**")
            st.json({k: v for k, v in result.items() if k != "risk"})

    with tab_domain:
        domain = st.text_input("Domain", value="example.com", key="ts_threat_domain")
        if st.button("🔍 Lookup WHOIS", key="ts_threat_domain_run", type="primary"):
            result = domain_whois(domain)
            if "error" in result:
                st.error(f"Lookup error: {result['error']}")
            else:
                st.success(f"✅ Domain: **{result['domain']}**")
                st.json({k: v for k, v in result.items() if k != "domain"})

    with tab_url:
        url = st.text_input("URL", value="http://paypal-secure-login.xyz/verify", key="ts_threat_url")
        if st.button("🔍 Analyze URL", key="ts_threat_url_run", type="primary"):
            result = analyze_url(url)
            risk = result["risk"]
            if risk == "HIGH":
                st.error(f"🚨 **{result['verdict']}** — risk score {result['risk_score']}")
            elif risk == "MEDIUM":
                st.warning(f"⚠️ **{result['verdict']}**")
            else:
                st.success(f"✅ **{result['verdict']}**")
            st.write("**Findings:**")
            for f in result["findings"]:
                st.markdown(f"• {f}")
            st.caption(result["recommendation"])


def render_playbook_tab():
    """Tab: Incident response playbooks."""
    section_header("📋 Automated Incident Response Playbooks", "Triage incidents and execute structured response workflows.")

    incident = st.selectbox("Incident type", [
        "Brute-Force Attack", "Phishing Campaign", "Malware Detection",
        "Data Breach / PII Exposure", "DDoS / Resource Exhaustion",
    ], key="ts_pb_type")

    context = st.text_area("Incident context (optional)", height=80, key="ts_pb_ctx")

    if st.button("🚀 Generate Playbook", key="ts_pb_run", type="primary"):
        result = run_incident_playbook(incident, context)
        st.success(f"Playbook **{result['playbook_id']}** generated — severity: **{result['severity_assessment']}**")
        st.markdown("#### 📋 Response Steps")
        for i, step in enumerate(result["steps"], 1):
            st.markdown(f"**{i}.** {step}")
        st.caption(f"Created: {result['created']}")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()  # paywall/trial gate, real DB check

    setup_page("Threat & Scanner Suite", "🛡️", initial_sidebar_state="expanded")

    hero_card(
        "🛡️ Threat & Scanner Suite",
        "PII/secret detection, live CVE scanning, malware signature detection, file integrity monitoring, network port scanning, threat intelligence, and automated incident response.",
        badge_text="THREAT & SCANNER SUITE • SECURITY OPS",
    )

    tabs = st.tabs([
        "🔍 PII Scanner",
        "🐞 CVE Scanner",
        "🕷️ Malware Scan",
        "🔐 Integrity",
        "🖧 Port Scan",
        "🛡️ Threat Intel",
        "📋 Playbooks",
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
