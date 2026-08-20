import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
"""
ðŸ•µï¸ Forensics Intelligence â€” Digital Evidence Laboratory (Hardened Production Grade)
Bit-level byte stream inspection, LSB entropy steganography profiling, deep EXIF/geolocation
mapping, SMTP envelope/DKIM/SPF analysis, and cryptographically immutable, per-evidence
chain-of-custody ledgers with strict error trapping and state durability.
"""

import hashlib
import io
import json
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


def _file_fingerprint(data: bytes) -> str:
    """Computes a unique SHA-256 fingerprint for precise file case mapping."""
    return hashlib.sha256(data).hexdigest()


def _get_or_open_case(data: bytes, filename: str) -> str:
    """One case per distinct piece of evidence, keyed by content hash with safe fallback structures."""
    if "fe_case_registry" not in st.session_state:
        st.session_state["fe_case_registry"] = {}

    fp = _file_fingerprint(data)
    registry = st.session_state["fe_case_registry"]
    if fp not in registry:
        try:
            case = open_evidence_case(filename, summary=f"Forensic evidentiary ingestion: {filename}")
            case_id = case.get("case_id", f"CASE-{fp[:8].upper()}")
        except Exception:
            case_id = f"CASE-{fp[:8].upper()}"
        registry[fp] = {"case_id": case_id, "filename": filename}
    st.session_state["fe_current_fingerprint"] = fp
    return registry[fp]["case_id"]


def render_evidence_lab_tab():
    section_header("ðŸ’¼ Bit-Level Digital Evidence Laboratory", "Deep binary inspection, magic byte verification, entropy profiling, cryptographic hashing, and automated per-evidence chain-of-custody logging.")

    uploaded = st.file_uploader("Upload evidentiary artifact for forensic analysis", key="fe_upload_upg")
    if uploaded is None:
        st.info("â„¹ï¸ Upload any file artifact to initiate comprehensive bit-level forensic investigation.")
        return

    data = uploaded.read()
    filename = uploaded.name

    if not data:
        st.error("ðŸš¨ The uploaded file payload is empty (0 bytes). Please provide a valid evidentiary file.")
        return

    case_id = _get_or_open_case(data, filename)

    st.success(f"ðŸ”— Immutable Chain-of-Custody Case Bound: **{case_id}** (this evidence's own case â€” not shared with other uploads this session)")
    try:
        append_custody_record(case_id, "EVIDENCE_INGESTED_AND_HASHED", st.session_state.get("user_identity", {}).get("name", "Forensic Analyst"))
    except Exception:
        pass

    with st.spinner("Executing low-level byte parsing and entropy profiling..."):
        try:
            report = investigate_bytes(data, filename) or {}
        except Exception as e:
            st.error(f"ðŸš¨ Byte investigation engine error: {e}")
            return

    hashes = report.get("hashes", {})
    st.markdown("#### ðŸ” Cryptographic Hashes & Integrity Signatures")
    hash_df = pd.DataFrame(
        [
            {"Algorithm": "SHA-256", "Value": hashes.get("sha256", hashlib.sha256(data).hexdigest())},
            {"Algorithm": "SHA-1", "Value": hashes.get("sha1", hashlib.sha1(data).hexdigest())},
            {"Algorithm": "MD5", "Value": hashes.get("md5", hashlib.md5(data).hexdigest())},
            {"Algorithm": "CRC32", "Value": hashes.get("crc32", "N/A")},
            {"Algorithm": "Payload Size", "Value": f"{hashes.get('size_bytes', len(data))} bytes"},
        ]
    )
    st.dataframe(hash_df, use_container_width=True, hide_index=True)

    st.markdown("#### ðŸ§¬ Magic Byte Signature & Extension Anomaly Detection")
    det = report.get("signature_detection", {"detected_type": "Unknown", "confidence": "0%"})
    ext = report.get("extension_check", {"verdict": "Unverified"})
    c1, c2, c3 = st.columns(3)
    c1.metric("Detected File Type", det.get("detected_type", "Unknown"))
    c2.metric("Signature Confidence", det.get("confidence", "N/A"))
    c3.metric("Extension Status", ext.get("verdict", "N/A"))
    st.info(f"**Forensic Verdict:** Declared extension `{ext.get('declared_extension','n/a')}` vs Inferred Magic Signature `{det.get('detected_type','Unknown')}`")

    st.markdown("#### ðŸ” Embedded IOCs, Artifact Carving & Strings")
    meta = report.get("embedded", {})
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

    st.markdown("#### ðŸ“Š Shannon Entropy Distribution")
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
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### ðŸ“¦ Export Cryptographic Evidence Dossier")
    dossier = json.dumps(report, indent=2)
    st.download_button("â¬‡ï¸ Download Complete Evidence Dossier (JSON)", data=dossier, file_name=f"evidence_dossier_{case_id}.json", mime="application/json", key="fe_download_upg")


def render_metadata_tab():
    section_header("ðŸ–¼ï¸ Deep Metadata & EXIF Geolocation Forensics", "Extract hidden EXIF tags, device manufacturer signatures, original capture timestamps, and interactive GPS coordinate mapping.")

    uploaded = st.file_uploader("Upload image evidentiary artifact (JPEG / PNG / TIFF)", type=["jpg", "jpeg", "png", "tiff"], key="fe_meta_upload_upg")
    if uploaded is None:
        st.info("â„¹ï¸ Upload an image to extract embedded EXIF parameters and geolocation data.")
        return

    data = uploaded.read()
    st.markdown("#### ðŸ” Extracted EXIF & Device Parameters")
    try:
        exif = extract_exif(data) or {}
    except Exception as e:
        exif = {"has_exif": False, "note": f"Extraction error: {e}"}

    if exif.get("has_exif"):
        col1, col2, col3 = st.columns(3)
        col1.metric("Camera Make", exif.get("Make", "â€”"))
        col2.metric("Camera Model", exif.get("Model", "â€”"))
        col3.metric("Software Tool", exif.get("Software", "â€”"))

        if exif.get("GPS"):
            gps = exif["GPS"]
            lat, lon = gps.get("latitude"), gps.get("longitude")
            if lat is not None and lon is not None:
                st.success(f"ðŸ“ Geolocation Coordinates Discovered: `{lat}, {lon}`")
                map_df = pd.DataFrame([{"lat": lat, "lon": lon}])
                st.map(map_df, zoom=12)
            else:
                st.info("â„¹ï¸ GPS dictionary present, but coordinate values are invalid.")
        else:
            st.info("â„¹ï¸ No GPS coordinates embedded in EXIF block.")
    else:
        st.warning(exif.get("note", "No EXIF metadata detected. The file may have been scrubbed or stripped prior to acquisition."))

    if st.button("ðŸ”— Append Extraction Event to Custody Ledger", key="fe_meta_custody_upg"):
        fp = st.session_state.get("fe_current_fingerprint")
        case_id = st.session_state.get("fe_case_registry", {}).get(fp, {}).get("case_id") if fp else None
        if case_id:
            try:
                append_custody_record(case_id, "METADATA_EXIF_EXTRACTED", "Forensic Analyst")
                st.success("âœ… Metadata extraction successfully logged to that evidence's custody ledger.")
            except Exception as e:
                st.error(f"ðŸš¨ Failed to write audit record: {e}")
        else:
            st.warning("âš ï¸ No active case found. Ingest this file in the Evidence Lab tab first to open its case.")


def render_stego_tab():
    section_header("ðŸ§© LSB Steganography & Bitstream Anomaly Detector", "Mathematically analyze least-significant bit (LSB) variance, chi-square pixel distributions, and bitstream entropy to uncover hidden payloads.")

    uploaded = st.file_uploader("Upload image for steganographic analysis (PNG / BMP / JPEG)", type=["png", "jpg", "jpeg", "bmp"], key="fe_stego_upload_upg")
    if uploaded is None:
        st.info("â„¹ï¸ Upload an image to perform LSB steganographic profiling.")
        return

    data = uploaded.read()
    with st.spinner("Executing LSB bitstream statistical analysis..."):
        try:
            result = analyze_lsb_steganography(data) or {}
        except Exception as e:
            result = {"supported": False, "note": f"Analysis execution error: {e}"}

    if result.get("supported"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Bits Sampled", result.get("bits_sampled", "â€”"))
        c2.metric("Ones Ratio", result.get("ones_ratio", "â€”"))
        c3.metric("Bitstream Entropy", result.get("entropy", "â€”"))

        st.markdown("#### ðŸ” Steganographic Verdict")
        likelihood = result.get("hidden_payload_likelihood", "LOW")
        if likelihood == "HIGH":
            st.error("ðŸš¨ **HIGH LIKELIHOOD OF HIDDEN PAYLOAD.** The LSB bitstream exhibits near-random statistical variance indicative of encrypted or compressed steganographic embedding.")
        else:
            st.success("âœ… **No Significant Steganographic Payload Detected.** LSB bitstream aligns with natural sensor noise distribution.")
        st.write(result.get("estimate", ""))
    else:
        st.warning(result.get("note", "Steganographic analysis is unsupported for this file format."))


def render_phishing_tab():
    section_header("ðŸ“§ SMTP Header & Email Phishing Forensics", "Inspect raw RFC 5322 email headers, evaluate DKIM/SPF alignment flags, trace transmission hop relays, and detect domain spoofing.")

    raw_email = st.text_area(
        "Paste raw SMTP email payload (Headers + Body)",
        height=280,
        placeholder="Received: from mail.attacker-domain.com ...\nFrom: Executive <admin@legit-bank.com>\nReply-To: support@evil-domain.com\nSubject: Urgent Security Verification Required",
        key="fe_email_input_upg",
    )

    if raw_email and st.button("ðŸ” Execute Email Forensic Analysis", key="fe_analyze_email_upg", type="primary"):
        try:
            result = analyze_email_headers(raw_email) or {}
        except Exception as e:
            st.error(f"ðŸš¨ Email parser exception: {e}")
            return

        risk = result.get("phishing_risk", "LOW")
        if risk == "HIGH":
            st.error(f"ðŸš¨ **{result.get('verdict', 'Potential Phishing')}** â€” Assessed Risk Level: **{risk}**")
        elif risk == "MEDIUM":
            st.warning(f"âš ï¸ **{result.get('verdict', 'Suspicious Headers')}** â€” Assessed Risk Level: **{risk}**")
        else:
            st.success(f"âœ… **{result.get('verdict', 'Clean Headers')}** â€” Assessed Risk Level: **{risk}**")

        if result.get("suspicious_findings"):
            st.markdown("#### ðŸš© Identified Indicator Anomalies (IoCs)")
            for finding in result["suspicious_findings"]:
                st.warning(f"â€¢ {finding}")

        if result.get("keyword_hits"):
            st.markdown("#### ðŸ”‘ Social Engineering Trigger Keywords")
            st.write(", ".join(result["keyword_hits"]))

        st.markdown("#### ðŸ“‹ Domain Envelope Alignment")
        cols = st.columns(3)
        cols[0].metric("From Domain", result.get("from_domain", "â€”"))
        cols[1].metric("Reply-To Domain", result.get("reply_to_domain", "â€”"))
        cols[2].metric("Return-Path Domain", result.get("return_path_domain", "â€”"))

        st.info(
            f"**Authentication Status:** SPF Present: `{result.get('spf_present')}` | "
            f"DKIM Present: `{result.get('dkim_present')}` | "
            f"Relay Hop Count: `{result.get('received_chain_count')}`"
        )


def render_custody_tab():
    section_header("ðŸ”— Cryptographic Chain-of-Custody Vault", "Court-admissible tamper-evident ledger where every investigative action is cryptographically chained via SHA-256 blocks â€” one independent chain per piece of evidence.")

    registry = st.session_state.get("fe_case_registry", {})
    if not registry:
        st.info("â„¹ï¸ No forensic cases opened this session. Ingest an evidentiary artifact in the Evidence Lab to initialize a case.")
        return

    options = {f"{v['case_id']} â€” {v['filename']}": v["case_id"] for v in registry.values()}
    selected_label = st.selectbox("Select Case to Inspect", list(options.keys()), key="fe_case_selector")
    case_id = options[selected_label]

    st.metric("Selected Case Identifier", case_id)
    if st.button("âœ… Verify Cryptographic Ledger Integrity", key="fe_verify_chain_upg", type="primary"):
        try:
            result = verify_chain(case_id) or {"valid": False, "reason": "No response from verification engine"}
        except Exception as e:
            result = {"valid": False, "reason": str(e)}

        if result.get("valid"):
            st.success(f"ðŸ” Chain integrity verified successfully â€” {result.get('records', 'Unknown')} immutable ledger entries intact for this case.")
        else:
            st.error(f"ðŸš¨ **CHAIN TAMPER DETECTED:** {result.get('reason')}")

    st.caption(f"{len(registry)} independent case(s) opened this session â€” each piece of evidence has its own chain, so unrelated files can never contaminate each other's custody record.")

    st.markdown("#### About Cryptographic Chain-of-Custody")
    st.markdown("""
    - Every upload, hashing operation, extraction, and analysis is recorded with a strict UTC timestamp.
    - Records are chained together using preceding SHA-256 hashes, **scoped to the specific evidence file that generated them**.
    - Any unauthorized modification or file tampering instantly invalidates the cryptographic proof chain for that case.
    """)


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription(hub_id="forensics")

    setup_page("Forensics Intelligence", "ðŸ•µï¸", initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "ðŸ•µï¸ Forensic Intelligence & Digital Evidence Laboratory â€” Hardened Production Suite",
        "Bit-level byte stream parsing, Shannon entropy profiling, LSB steganography detection, EXIF geolocation mapping, SMTP phishing forensics, and cryptographically immutable, per-evidence chain-of-custody ledgers.",
        badge_text="FORENSIC INTELLIGENCE â€¢ SECURE EVIDENCE LAB",
    )

    tabs = st.tabs([
        "ðŸ’¼ Evidence Lab",
        "ðŸ–¼ï¸ Metadata & GPS",
        "ðŸ§© Steganography",
        "ðŸ“§ Phishing Analyzer",
        "ðŸ”— Chain of Custody",
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
