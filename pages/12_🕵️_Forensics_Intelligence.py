"""
🕵️ Forensics Intelligence — Digital Evidence Laboratory
Consolidates the CHRISHEM Forensic Intelligence Engine into an interactive hub.
"""

import io
import json

import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import hero_card, section_header, metric_card
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


def render_evidence_lab_tab():
    """Tab: Digital evidence lab — full file investigation."""
    section_header("💼 Digital Evidence Lab", "Analyze any file at the bit level: hashing, signature detection, metadata forensics, and steganalysis.")

    uploaded = st.file_uploader("Upload evidence file (any type)", key="fe_upload")
    if uploaded is None:
        st.info("Upload a file to begin the forensic investigation.")
        return

    data = uploaded.read()
    filename = uploaded.name

    # Open a chain-of-custody case
    if "fe_case_id" not in st.session_state:
        case = open_evidence_case(filename, summary=f"Forensic evidence upload: {filename}")
        st.session_state["fe_case_id"] = case["case_id"]
    case_id = st.session_state["fe_case_id"]

    st.success(f"🔗 Chain-of-Custody Case: **{case_id}**")
    append_custody_record(case_id, "EVIDENCE_UPLOADED", st.session_state.get("user_identity", {}).get("name", "Analyst"))

    with st.spinner("Running full forensic investigation..."):
        report = investigate_bytes(data, filename)

    st.markdown("#### 🔐 Cryptographic Hashes")
    hash_df = pd.DataFrame(
        [
            {"Algorithm": "SHA-256", "Value": report["hashes"]["sha256"]},
            {"Algorithm": "SHA-1", "Value": report["hashes"]["sha1"]},
            {"Algorithm": "MD5", "Value": report["hashes"]["md5"]},
            {"Algorithm": "CRC32", "Value": report["hashes"]["crc32"]},
            {"Algorithm": "Size (bytes)", "Value": report["hashes"]["size_bytes"]},
        ]
    )
    st.dataframe(hash_df, use_container_width=True, hide_index=True)

    st.markdown("#### 🧬 File Signature & Type Detection")
    det = report["signature_detection"]
    ext = report["extension_check"]
    c1, c2 = st.columns(2)
    c1.metric("Detected Type", det["detected_type"])
    c2.metric("Confidence", det["confidence"])
    st.info(f"**Extension verdict:** {ext['verdict']} — declared type `{ext.get('declared_extension','n/a')}` vs actual `{det['detected_type']}`")

    st.markdown("#### 🔍 Embedded Metadata & Memory Carving")
    meta = report["embedded"]
    if meta.get("urls"):
        st.write("**URLs found:**", ", ".join(meta["urls"]))
    if meta.get("emails"):
        st.write("**Emails found:**", ", ".join(meta["emails"]))
    if meta.get("ip_addresses"):
        st.write("**IP addresses found:**", ", ".join(meta["ip_addresses"]))
    if meta.get("printable_strings"):
        with st.expander("Extracted printable strings", expanded=False):
            st.write(meta["printable_strings"])
    if not meta.get("urls") and not meta.get("emails") and not meta.get("ip_addresses"):
        st.caption("No URLs/emails/IPs embedded in the byte stream.")

    st.markdown("#### 🧩 EXIF & Steganography Analysis")
    if report.get("exif"):
        exif = report["exif"]
        if exif.get("has_exif"):
            ecols = st.columns(3)
            ecols[0].metric("Make", exif.get("Make", "—"))
            ecols[1].metric("Model", exif.get("Model", "—"))
            if exif.get("GPS"):
                ecols[2].metric("GPS Coords", f"{exif['GPS']['latitude']}, {exif['GPS']['longitude']}")
        else:
            st.caption(exif.get("note", "No EXIF metadata."))

    stego = report["lsb_stego"]
    if stego.get("supported"):
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("LSB Entropy", stego.get("entropy", "—"))
        sc2.metric("Ones Ratio", stego.get("ones_ratio", "—"))
        sc3.metric("Hidden Payload", stego.get("hidden_payload_likelihood", "—"))
        st.write(stego.get("estimate", ""))
    else:
        st.caption(stego.get("note", ""))

    st.markdown("#### 📊 Entropy Analysis")
    st.metric("Entropy (bits/byte)", report.get("entropy_bits_per_byte", "—"))
    st.caption("High entropy (approaching 8) suggests compressed or encrypted data; low entropy suggests plaintext.")

    # Export evidence report
    st.markdown("#### 📦 Export Evidence Dossier")
    dossier = json.dumps(report, indent=2)
    st.download_button("⬇️ Download Evidence Dossier (JSON)", data=dossier, file_name=f"evidence_{case_id}.json", mime="application/json", key="fe_download")


def render_metadata_tab():
    """Tab: Metadata forensics."""
    section_header("🖼️ Metadata & EXIF Forensics", "Extract hidden metadata from images — GPS, camera, and timestamps.")

    uploaded = st.file_uploader("Upload an image (JPEG/PNG/TIFF)", type=["jpg", "jpeg", "png", "tiff"], key="fe_meta_upload")
    if uploaded is None:
        st.info("Upload an image to extract embedded metadata.")
        return

    data = uploaded.read()
    st.markdown("#### 🔍 Extracted Metadata")
    exif = extract_exif(data)
    if exif.get("has_exif"):
        st.write("**Make:**", exif.get("Make", "—"))
        st.write("**Model:**", exif.get("Model", "—"))
        st.write("**Software:**", exif.get("Software", "—"))
        if exif.get("GPS"):
            gps = exif["GPS"]
            st.success(f"📍 GPS coordinates found: {gps['latitude']}, {gps['longitude']}")
            st.map(pd.DataFrame([{"lat": gps["latitude"], "lon": gps["longitude"]}]))
        else:
            st.info("No GPS coordinates embedded.")
    else:
        st.warning(exif.get("note", "No EXIF metadata found. The image may have been stripped of metadata."))

    st.markdown("#### 🧠 Embedded Content")
    meta = extract_common_metadata(data)
    if meta.get("printable_strings"):
        with st.expander(f"Extracted {len(meta['printable_strings'])} strings", expanded=False):
            st.write(meta["printable_strings"])

    if st.button("🔗 Append to Custody Ledger", key="fe_meta_custody"):
        case_id = st.session_state.get("fe_case_id")
        if case_id:
            append_custody_record(case_id, "METADATA_EXTRACTED", "Analyst")
            st.success("Metadata extraction logged to custody ledger.")


def render_stego_tab():
    """Tab: Steganography detection."""
    section_header("🧩 Steganography Detector", "Analyze the least-significant bits of images for hidden payloads.")

    uploaded = st.file_uploader("Upload image to analyze for hidden data", type=["png", "jpg", "jpeg", "bmp"], key="fe_stego_upload")
    if uploaded is None:
        st.info("Upload an image to run LSB steganalysis.")
        return

    data = uploaded.read()
    with st.spinner("Analyzing LSB bitstream..."):
        result = analyze_lsb_steganography(data)

    if result.get("supported"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Bits Sampled", result.get("bits_sampled", "—"))
        c2.metric("Ones Ratio", result.get("ones_ratio", "—"))
        c3.metric("Entropy", result.get("entropy", "—"))

        st.markdown("#### 🔍 Interpretation")
        likelihood = result.get("hidden_payload_likelihood", "LOW")
        if likelihood == "HIGH":
            st.error("⚠️ **HIGH likelihood of hidden payload.** The LSB bitstream is near-random, consistent with embedded data.")
        else:
            st.success("✅ **No significant hidden payload detected.** LSB bitstream appears natural.")
        st.write(result.get("estimate", ""))
    else:
        st.warning(result.get("note", "Analysis not supported for this file type."))


def render_phishing_tab():
    """Tab: Email & phishing analyzer."""
    section_header("📧 Email Header & Phishing Analyzer", "Paste raw email headers to detect spoofing and phishing indicators.")

    raw_email = st.text_area(
        "Paste raw email (headers + body)",
        height=280,
        placeholder="From: attacker@evil.com\nReply-To: support@lookalike.com\nSubject: Your account has been suspended\nReceived-From: mail.evil.com...",
        key="fe_email_input",
    )

    if raw_email and st.button("🔍 Analyze Email", key="fe_analyze_email", type="primary"):
        result = analyze_email_headers(raw_email)

        risk = result.get("phishing_risk", "LOW")
        if risk == "HIGH":
            st.error(f"🚨 **{result['verdict']}** — Phishing risk: {risk}")
        elif risk == "MEDIUM":
            st.warning(f"⚠️ **{result['verdict']}** — Phishing risk: {risk}")
        else:
            st.success(f"✅ **{result['verdict']}** — Phishing risk: {risk}")

        if result.get("suspicious_findings"):
            st.markdown("#### 🚩 Suspicious Findings")
            for finding in result["suspicious_findings"]:
                st.warning(f"• {finding}")

        if result.get("keyword_hits"):
            st.markdown("#### 🔑 Suspicious Keywords")
            st.write(", ".join(result["keyword_hits"]))

        st.markdown("#### 📋 Parsed Headers")
        cols = st.columns(3)
        cols[0].metric("From Domain", result.get("from_domain", "—"))
        cols[1].metric("Reply-To Domain", result.get("reply_to_domain", "—"))
        cols[2].metric("Return-Path Domain", result.get("return_path_domain", "—"))
        st.caption(f"SPF present: {result.get('spf_present')} | DKIM present: {result.get('dkim_present')} | Received chain count: {result.get('received_chain_count')}")


def render_custody_tab():
    """Tab: Chain-of-custody vault."""
    section_header("🔗 Chain-of-Custody Vault", "Tamper-evident evidence ledger with cryptographic chaining.")

    case_id = st.session_state.get("fe_case_id")
    if case_id:
        st.metric("Active Case", case_id)
        if st.button("✅ Verify Chain Integrity", key="fe_verify_chain"):
            result = verify_chain(case_id)
            if result.get("valid"):
                st.success(f"Chain integrity verified — {result['records']} records intact.")
            else:
                st.error(f"Chain tamper detected: {result.get('reason')}")
    else:
        st.info("No active forensic case. Upload evidence in the Evidence Lab tab to open a case.")

    st.markdown("#### About Chain-of-Custody")
    st.info(
        "Each evidence action is appended to a cryptographic ledger where every record is "
        "chained to the previous via SHA-256 hashing. Any alteration breaks the chain, "
        "making tampering detectable — critical for court-ready digital evidence."
    )


def main():
    setup_page("Forensics Intelligence", "🕵️", initial_sidebar_state="expanded")

    hero_card(
        "🕵️ Forensic Intelligence & Digital Evidence Lab",
        "Bit-level file investigation, metadata & EXIF extraction, steganography detection, email phishing analysis, and tamper-evident chain-of-custody.",
        badge_text="FORENSIC INTELLIGENCE • DIGITAL EVIDENCE",
    )

    tabs = st.tabs([
        "💼 Evidence Lab",
        "🖼️ Metadata",
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
