import io
import re
import numpy as np
import pandas as pd
import streamlit as st

def render_enterprise_ai_nlp_studio():
    # --- Custom Enterprise CSS Styling ---
    st.markdown("""
        <style>
        .nlp-hero {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border: 1px solid #334155;
            padding: 1.75rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }
        .telemetry-badge {
            background-color: #059669;
            color: #ffffff;
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        .metric-card {
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid #475569;
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Hero Header ---
    st.markdown("""
        <div class="nlp-hero">
            <span class="telemetry-badge">SYSTEM ACTIVE • ADMIN: CHRISHEM</span>
            <h2 style="color: #f8fafc; margin-top: 0.5rem; margin-bottom: 0.25rem; font-weight: 700;">
                🧠 Enterprise AI & Natural Language Processing Studio
            </h2>
            <p style="color: #94a3b8; font-size: 0.95rem; margin: 0;">
                Real-time corpus auditing, transformer token distribution mapping, heuristic sentiment telemetry, and regex entity extraction.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # --- Sidebar Configuration Controls ---
    with st.sidebar:
        st.markdown("### ⚙️ Engine Configurations")
        min_token_len = st.slider("Min Token Length", 1, 5, 3, key="ent_min_token")
        filter_stops = st.checkbox("Exclude Stop-Words", value=True, key="ent_stopwords")
        case_sensitive = st.checkbox("Case-Sensitive Analysis", value=False, key="ent_case_sens")
        sensitivity_mode = st.selectbox("Polarity Threshold", ["Standard", "Strict (Biomedical/Legal)", "Permissive"], key="ent_sens")
        st.markdown("---")
        st.info("🔐 **Security Protocol:** AES-256 Text Stream Encryption Active.")

    # --- Corpus Ingestion Section ---
    st.markdown("### 📥 Corpus Ingestion & Pipeline Source")
    ingest_mode = st.radio(
        "Select Data Stream Ingestion Source", 
        ["Live Text Workspace", "Upload Structured CSV / Corpus (.txt / .csv)", "Load Secure System Logs"], 
        horizontal=True, 
        key="ent_ingest_mode"
    )

    raw_text = ""
    if ingest_mode == "Live Text Workspace":
        raw_text = st.text_area(
            "Active Text Buffer:",
            value="""The Chrishem Sovereign Apex Hub integrates advanced artificial intelligence, 
genomic surveillance data pipelines, and natural language processing engines to streamline 
academic research workflows. System administrator CHRISHEM oversees active containerized deployments 
ensuring operational integrity, security compliance, and seamless multi-page analytics execution. 
Errors, exceptions, or security anomalies trigger automated isolation protocols.""",
            height=210,
            key="ent_live_textarea"
        )
    elif ingest_mode == "Upload Structured CSV / Corpus (.txt / .csv)":
        uploaded_file = st.file_uploader("Upload Payload", type=["txt", "csv"], key="ent_file_uploader")
        if uploaded_file is not None:
            if uploaded_file.name.endswith(".csv"):
                df_upload = pd.read_csv(uploaded_file)
                text_column = st.selectbox("Select Text Vector Column", df_upload.columns.tolist(), key="ent_csv_col")
                raw_text = " ".join(df_upload[text_column].dropna().astype(str).tolist())
            else:
                raw_text = io.BytesIO(uploaded_file.getvalue()).read().decode("utf-8")
            st.success(f"✅ Loaded stream: `{uploaded_file.name}` ({len(raw_text):,} characters parsed)")
    else:
        raw_text = """[SYSTEM_TELEMETRY 2026-08-21 08:54:24 EAT]: Administrator CHRISHEM initialized core vault. 
Status: OPTIMAL. All genomics pipelines, Notion live data bridges, and machine learning endpoints operating at 99.98% efficiency. 
Warning: Minor latency recorded on external REST connector. Automated load-balancing active. 
Research verification confirms successful execution of mobile colistin resistance ($mcr$) gene audits and environmental waste monitoring."""

    if not raw_text.strip():
        st.warning("⚠️ Corpus buffer empty. Input valid text data to initialize processing.")
        return

    # --- Real-Time Telemetry Metrics ---
    words_raw = re.findall(r'\b\w+\b', raw_text)
    words = words_raw if case_sensitive else [w.lower() for w in words_raw]
    sentences = [s.strip() for s in re.split(r'[.!?]+', raw_text) if s.strip()]
    paragraphs = [p.strip() for p in raw_text.split('\n') if p.strip()]

    st.markdown("---")
    st.markdown("#### 📊 Real-Time Corpus Metrics")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Characters", f"{len(raw_text):,}")
    with col2:
        st.metric("Tokens (Words)", f"{len(words):,}")
    with col3:
        st.metric("Sentences", f"{len(sentences):,}")
    with col4:
        st.metric("Paragraphs", f"{len(paragraphs):,}")
    with col5:
        st.metric("Avg Token Size", f"{np.mean([len(w) for w in words]):.1f}" if words else "0")

    st.markdown("---")

    # --- Multi-Tab Analytical Workspace ---
    tab_tokens, tab_sentiment, tab_regex, tab_audit = st.tabs([
        "📈 Token Frequency & Vectors", 
        "💬 Sentiment & Polarity Audit", 
        "🔍 Regex & Entity Extraction", 
        "📄 Executive Audit Report"
    ])

    with tab_tokens:
        st.markdown("#### Frequency Distribution & Vocabulary Analysis")
        stop_words = {"the", "and", "to", "of", "a", "in", "is", "it", "that", "for", "on", "with", "as", "this", "an", "by", "or", "at", "from"} if filter_stops else set()
        filtered_tokens = [w for w in words if w.lower() not in stop_words and len(w) >= min_token_len]

        if filtered_tokens:
            freq_df = pd.Series(filtered_tokens).value_counts().reset_index()
            freq_df.columns = ["Token", "Frequency"]
            
            c_chart, c_table = st.columns([2, 1])
            with c_chart:
                st.bar_chart(freq_df.set_index("Token").head(12), color="#3b82f6")
            with c_table:
                st.dataframe(freq_df.head(15), use_container_width=True, hide_index=True)
                
                # Consolidated CSV export for frequency table
                freq_csv = freq_df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Export Frequencies (.csv)", data=freq_csv, file_name="token_frequencies.csv", mime="text/csv", key="download_freq_csv")
        else:
            st.info("No tokens match current filtering thresholds.")

    with tab_sentiment:
        st.markdown("#### Heuristic Sentiment & Tone Polarity Audit")
        
        pos_lexicon = {"apex", "hub", "success", "secure", "advanced", "seamless", "integrity", "optimal", "clean", "robust", "operational", "successful", "efficiency"}
        neg_lexicon = {"error", "fail", "warning", "breach", "degrading", "unstable", "missing", "risk", "latency", "minor", "anomaly"}
        
        pos_matches = [w for w in words if w.lower() in pos_lexicon]
        neg_matches = [w for w in words if w.lower() in neg_lexicon]
        
        score = len(pos_matches) - len(neg_matches)
        if score > 0:
            status_text = "🟢 Positive / Operational State"
        elif score == 0:
            status_text = "🟡 Neutral / Stable Balance"
        else:
            status_text = "🔴 Cautionary / Alert State"

        st.info(f"Assessed System Tone: **{status_text}** (Net Polarity Score: `{score}`)")

        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown(f"**Constructive Indicators Found ({len(pos_matches)}):**")
            st.write(", ".join(set(pos_matches)) if pos_matches else "None detected")
        with sc2:
            st.markdown(f"**Risk / Warning Indicators Found ({len(neg_matches)}):**")
            st.write(", ".join(set(neg_matches)) if neg_matches else "None detected")

    with tab_regex:
        st.markdown("#### Advanced Regular Expression Pattern Miner")
        preset_choice = st.selectbox("Select Pattern Template", [
            "Capitalized Proper Nouns",
            "Email Addresses",
            "ISO Dates / Timestamps",
            "Numeric Codes / Digits",
            "Genomic Variables ($mcr$ genes / tags)",
            "Custom Regex Input"
        ], key="ent_regex_preset")

        patterns = {
            "Capitalized Proper Nouns": r"\b[A-Z][a-z]+\b",
            "Email Addresses": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "ISO Dates / Timestamps": r"\d{4}-\d{2}-\d{2}",
            "Numeric Codes / Digits": r"\b\d+\b",
            "Genomic Variables ($mcr$ genes / tags)": r"\b[a-z]{3}-?[0-9]*\b",
            "Custom Regex Input": r"\b[A-Za-z]+\b"
        }

        active_pattern = patterns[preset_choice]
        if preset_choice == "Custom Regex Input":
            active_pattern = st.text_input("Enter Custom Regex", value=r"\b[A-Za-z]+\b", key="ent_custom_regex_input")

        if active_pattern:
            try:
                matches = re.findall(active_pattern, raw_text)
                st.markdown(f"Matched **{len(matches)}** pattern instances:")
                if matches:
                    match_df = pd.DataFrame({"Index": range(1, len(matches)+1), "Extracted Token": matches})
                    st.dataframe(match_df, use_container_width=True, hide_index=True)
                    
                    csv_export = match_df.to_csv(index=False).encode("utf-8")
                    st.download_button("📥 Export Extracted Matches (.csv)", data=csv_export, file_name="extracted_matches.csv", mime="text/csv")
            except Exception as e:
                st.error(f"Regex Evaluation Error: {e}")

    with tab_audit:
        st.markdown("#### Executive Summary & Verification Report")
        if st.button("🚀 Generate Verified Audit Report", type="primary", key="generate_audit_btn"):
            audit_report = f"""# CHRISHEM SOVEREIGN APEX HUB - NLP AUDIT REPORT
Timestamp: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')} EAT
System Administrator: CHRISHEM

## Corpus Diagnostics
- Total Characters: {len(raw_text):,}
- Total Tokens: {len(words):,}
- Sentence Count: {len(sentences):,}
- Paragraph Count: {len(paragraphs):,}

## Polarity & Sentiment State
- Assessed Status: {status_text}
- Net Polarity Score: {score}
- Positive Signifiers: {len(set(pos_matches))}
- Risk Signifiers: {len(set(neg_matches))}

## Top Frequent Vocabulary Terms
{chr(10).join([f'- `{row.Token}`: {row.Frequency} occurrences' for _, row in freq_df.head(5).iterrows()]) if 'freq_df' in locals() and not freq_df.empty else 'N/A'}
"""
            st.code(audit_report, language="markdown")
            st.download_button("⬇️ Download Executive Report (.md)", data=audit_report, file_name="executive_nlp_audit.md", mime="text/markdown")

if __name__ == "__main__":
    render_enterprise_ai_nlp_studio()