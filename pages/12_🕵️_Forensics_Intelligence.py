"""
🕵️ Forensics Intelligence — Digital Evidence Laboratory (Enterprise Production Grade)
Advanced digital forensics hub featuring real bit-level byte stream inspection, LSB entropy steganography profiling, 
deep EXIF/geolocation mapping, SMTP envelope/DKIM/SPF analysis, and cryptographically immutable chain-of-custody ledgers.
"""

import io
import json
import hashlib
import datetime
import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import hero_card, section_header, metric_card, render_export_buttons
from modules.forensics_engine import (
    compute_hashes,
    detect_file_type,
    compare_extension,
    extract_exif,
    extract_common_metadata,
    analyze_lsb_steganography,
    investigate_bytes,
    analyze_email_headers,
    open_evidence_case,
    append_custody_record,
    verify_chain,
)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def render_evidence_lab_tab():
    section_header("💼 Bit-Level Digital Evidence Laboratory", "Perform deep binary inspection, magic byte verification, entropy profiling, cryptographic hashing, and automated chain-of-custody logging.")

    uploaded = st.file_uploader("Upload evidentiary artifact for forensic analysis", key="fe_upload_upg")
    if uploaded is None:
        st.info("ℹ️ Upload any file artifact to initiate comprehensive bit-level forensic investigation.")
        return

    data = uploaded.read()
    filename = uploaded.name

    if "fe_case_id" not in st.session_state:
        case = open_evidence_case(filename, summary=f"Forensic evidentiary ingestion: {filename}")
        st.session_state["fe_case_id"] = case["case_id"]
    case_id = st.session_state["fe_case_id"]

    st.success(f"🔗 Immutable Chain-of-Custody Case Bound: **{case_id}**")
    append_custody_record(case_id, "EVIDENCE_INGESTED_AND_HASHED", st.session_state.get("user_identity", {}).get("name", "Forensic Analyst"))

    with st.spinner("Executing low-level byte parsing and entropy profiling..."):
        report = investigate_bytes(data, filename)

    st.markdown("#### 🔐 Cryptographic Hashes & Integrity Signatures")
    hash_df = pd.DataFrame(
        [
            {"Algorithm": "SHA-256", "Value": report["hashes"]["sha256"]},
            {"Algorithm": "SHA-1", "Value": report["hashes"]["sha1"]},
            {"Algorithm": "MD5", "Value": report["hashes"]["md5"]},
            {"Algorithm": "CRC32", "Value": report["hashes"]["crc32"]},
            {"Algorithm": "Payload Size", "Value": f"{report['hashes']['size_bytes']} bytes"},
        ]
    )
    st.dataframe(hash_df, use_container_width=True, hide_index=True)

    st.markdown("#### 🧬 Magic Byte Signature & Extension Anomaly Detection")
    det = report["signature_detection"]
    ext = report["extension_check"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Detected File Type", det["detected_type"])
    c2.metric("Signature Confidence", det["confidence"])
    c3.metric("Extension Status", ext["verdict"])
    st.info(f"**Forensic Verdict:** Declared extension `{ext.get('declared_extension','n/a')}` vs Inferred Magic Signature `{det['detected_type']}`")

    st.markdown("#### 🔍 Embedded IOCs, Artifact Carving & Strings")
    meta = report["embedded"]
    col_i1, col_i2, col_i3 = st.columns(3)
    col_i1.metric("Extracted URLs", len(meta.get("urls", [])))
    col_i2.metric("Extracted Emails", len(meta.get("emails", [])))
    col_i3.metric("Extracted IP Addrs", len(meta.get("ip_addresses", [])))

    if meta.get("urls"):
        st.write("**Discovered URLs:**", ", ".join(meta["urls"]))
    if meta.get("emails"):
        st.write("**Discovered Email Indicators:**", ", ".join(meta["emails"]))
    if meta.get("ip_addresses"):
        st.write("**Discovered IP Addresses:**", ", ".join(meta["ip_addresses"]))

    if meta.get("printable_strings"):
        with st.expander(f"Extracted ASCII/Unicode Strings ({len(meta['printable_strings'])} tokens)", expanded=False):
            st.text("\n".join(meta["printable_strings"][:200]))

    st.markdown("#### 📊 Shannon Entropy Distribution")
    entropy = report.get("entropy_bits_per_byte", 0.0)
    st.metric("Shannon Entropy (bits/byte)", f"{entropy:.4f} / 8.0")
    if PLOTLY_AVAILABLE:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=float(entropy) if isinstance(entropy, (int, float)) else 0.0,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Entropy (8.0 = Max Randomness / Encrypted)"},
            gauge={
                'axis': {'range': [None, 8]},
                'bar': {'color': "#00f2fe"},
                'steps': [
                    {'range': [0, 4], 'color': "rgba(0,255,0,0.2)"},
                    {'range': [4, 7], 'color': "rgba(255,255,0,0.2)"},
                    {'range': [7, 8], 'color': "rgba(255,0,0,0.2)"}
                ],
            }
        ))
        fig.update_layout(height=220, margin=dict(t=30, b=10, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
        st.plotly_graph(fig, use_container_width=True)

    st.markdown("#### 📦 Export Cryptographic Evidence Dossier")
    dossier = json.dumps(report, indent=2)
    st.download_button("⬇️ Download Complete Evidence Dossier (JSON)", data=dossier, file_name=f"evidence_dossier_{case_id}.json", mime="application/json", key="fe_download_upg")


def render_metadata_tab():
    section_header("🖼️ Deep Metadata & EXIF Geolocation Forensics", "Extract hidden EXIF tags, device manufacturer signatures, original capture timestamps, and interactive GPS coordinate mapping.")

    uploaded = st.file_uploader("Upload image evidentiary artifact (JPEG / PNG / TIFF)", type=["jpg", "jpeg", "png", "tiff"], key="fe_meta_upload_upg")
    if uploaded is None:
        st.info("ℹ️ Upload an image to extract embedded EXIF parameters and geolocation data.")
        return

    data = uploaded.read()
    st.markdown("#### 🔍 Extracted EXIF & Device Parameters")
    exif = extract_exif(data)
    if exif.get("has_exif"):
        col1, col2, col3 = st.columns(3)
        col1.metric("Camera Make", exif.get("Make", "—"))
        col2.metric("Camera Model", exif.get("Model", "—"))
        col3.metric("Software Tool", exif.get("Software", "—"))

        if exif.get("GPS"):
            gps = exif["GPS"]
            lat, lon = gps["latitude"], gps["longitude"]
            st.success(f"📍 Geolocation Coordinates Discovered: `{lat}, {lon}`")
            map_df = pd.DataFrame([{"lat": lat, "lon": lon}])
            st.map(map_df, zoom=12)
        else:
            st.info("ℹ️ No GPS coordinates embedded in EXIF block.")
    else:
        st.warning(exif.get("note", "No EXIF metadata detected. The file may have been scrubbed or stripped prior to acquisition."))

    if st.button("🔗 Append Extraction Event to Custody Ledger", key="fe_meta_custody_upg"):
        case_id = st.session_state.get("fe_case_id")
        if case_id:
            append_custody_record(case_id, "METADATA_EXIF_EXTRACTED", "Forensic Analyst")
            st.success("✅ Metadata extraction successfully logged to immutable custody ledger.")
        else:
            st.warning("⚠️ No active case found. Ingest a primary evidence file in the Evidence Lab first.")


def render_stego_tab():
    section_header("🧩 LSB Steganography & Bitstream Anomaly Detector", "Mathematically analyze least-significant bit (LSB) variance, chi-square pixel distributions, and bitstream entropy to uncover hidden payloads.")

    uploaded = st.file_uploader("Upload image for steganographic analysis (PNG / BMP / JPEG)", type=["png", "jpg", "jpeg", "bmp"], key="fe_stego_upload_upg")
    if uploaded is None:
        st.info("ℹ️ Upload an image to perform LSB steganographic profiling.")
        return

    data = uploaded.read()
    with st.spinner("Executing LSB bitstream statistical analysis..."):
        result = analyze_lsb_steganography(data)

    if result.get("supported"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Bits Sampled", result.get("bits_sampled", "—"))
        c2.metric("Ones Ratio", result.get("ones_ratio", "—"))
        c3.metric("Bitstream Entropy", result.get("entropy", "—"))

        st.markdown("#### 🔍 Steganographic Verdict")
        likelihood = result.get("hidden_payload_likelihood", "LOW")
        if likelihood == "HIGH":
            st.error("🚨 **HIGH LIKELIHOOD OF HIDDEN PAYLOAD.** The LSB bitstream exhibits near-random statistical variance indicative of encrypted or compressed steganographic embedding.")
        else:
            st.success("✅ **No Significant Steganographic Payload Detected.** LSB bitstream aligns with natural sensor noise distribution.")
        st.write(result.get("estimate", ""))
    else:
        st.warning(result.get("note", "Steganographic analysis is unsupported for this file format."))


def render_phishing_tab():
    section_header("📧 SMTP Header & Email Phishing Forensics", "Inspect raw RFC 5322 email headers, evaluate DKIM/SPF alignment flags, trace transmission hop relays, and detect domain spoofing.")

    raw_email = st.text_area(
        "Paste raw SMTP email payload (Headers + Body)",
        height=280,
        placeholder="Received: from mail.attacker-domain.com ...\nFrom: Executive <admin@legit-bank.com>\nReply-To: support@evil-domain.com\nSubject: Urgent Security Verification Required",
        key="fe_email_input_upg",
    )

    if raw_email and st.button("🔍 Execute Email Forensic Analysis", key="fe_analyze_email_upg", type="primary"):
        result = analyze_email_headers(raw_email)

        risk = result.get("phishing_risk", "LOW")
        if risk == "HIGH":
            st.error(f"🚨 **{result.get('verdict', 'Potential Phishing')}** — Assessed Risk Level: **{risk}**")
        elif risk == "MEDIUM":
            st.warning(f"⚠️ **{result.get('verdict', 'Suspicious Headers')}** — Assessed Risk Level: **{risk}**")
        else:
            st.success(f"✅ **{result.get('verdict', 'Clean Headers')}** — Assessed Risk Level: **{risk}**")

        if result.get("suspicious_findings"):
            st.markdown("#### 🚩 Identified Indicator Anomalies (IoCs)")
            for finding in result["suspicious_findings"]:
                st.warning(f"• {finding}")

        if result.get("keyword_hits"):
            st.markdown("#### 🔑 Social Engineering Trigger Keywords")
            st.write(", ".join(result["keyword_hits"]))

        st.markdown("#### 📋 Domain Envelope Alignment")
        cols = st.columns(3)
        cols[0].metric("From Domain", result.get("from_domain", "—"))
        cols[1].metric("Reply-To Domain", result.get("reply_to_domain", "—"))
        cols[2].metric("Return-Path Domain", result.get("return_path_domain", "—"))
        
        st.info(
            f"**Authentication Status:** SPF Present: `{result.get('spf_present')}` | "
            f"DKIM Present: `{result.get('dkim_present')}` | "
            f"Relay Hop Count: `{result.get('received_chain_count')}`"
        )


def render_custody_tab():
    section_header("🔗 Cryptographic Chain-of-Custody Vault", "Court-admissible tamper-evident ledger where every investigative action is cryptographically chained via SHA-256 blocks.")

    case_id = st.session_state.get("fe_case_id")
    if case_id:
        st.metric("Active Case Identifier", case_id)
        if st.button("✅ Verify Cryptographic Ledger Integrity", key="fe_verify_chain_upg", type="primary"):
            result = verify_chain(case_id)
            if result.get("valid"):
                st.success(f"🔐 Chain integrity verified successfully — {result['records']} immutable ledger entries intact.")
            else:
                st.error(f"🚨 **CHAIN TAMPER DETECTED:** {result.get('reason')}")
    else:
        st.info("ℹ️ No active forensic case session. Ingest evidentiary artifacts in the Evidence Lab to initialize a case.")

    st.markdown("#### About Cryptographic Chain-of-Custody")
    st.markdown("""
    - Every upload, hashing operation, extraction, and analysis is recorded with a strict UTC timestamp.
    - Records are chained together using preceding SHA-256 hashes.
    - Any unauthorized modification or file tampering instantly invalidates the cryptographic proof chain, ensuring strict legal admissibility.
    """)


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()

    setup_page("Forensics Intelligence", "🕵️", initial_sidebar_state="expanded")

    hero_card(
        "🕵️ Forensic Intelligence & Digital Evidence Laboratory — Enterprise Suite",
        "Advanced digital forensics suite featuring bit-level byte stream parsing, Shannon entropy profiling, LSB steganography detection, EXIF geolocation mapping, SMTP phishing forensics, and cryptographically immutable chain-of-custody ledgers.",
        badge_text="FORENSIC INTELLIGENCE • DIGITAL EVIDENCE LAB",
    )

    tabs = st.tabs([
        "💼 Evidence Lab",
        "🖼️ Metadata & GPS",
        "🧩 Steganography",
        "📧 Phishing Analyzer",
        "🔗 Chain of Custody",
    ])

    with tabs[0]:
        render_evidence_lab_tab()
    with tabs[1]:
        render_metadata_tab()
    with tabs[2]:
        render_stego_tab()
    with tabs[3]:
        render_phishing_tab()
    with tabs[4]:
        render_custody_tab()

    render_standard_footer("FORENSIC INTELLIGENCE")


if __name__ == "__main__":
    main()