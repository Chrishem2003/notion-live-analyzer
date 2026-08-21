import io
import re
import numpy as np
import pandas as pd
import streamlit as st

def render_comprehensive_ai_nlp_suite():
    st.markdown("### 🧠 CHRISHEM Sovereign AI & Natural Language Processing Studio")
    st.markdown("*Advanced corporate text intelligence, token distribution analytics, heuristic sentiment auditing, and automated pattern extraction.*")

    # Sidebar or top configuration controls for NLP settings
    with st.expander("⚙️ Advanced NLP Engine Parameters", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            min_word_length = st.slider("Minimum Token Length", 1, 5, 3, key="nlp_min_len")
        with c2:
            remove_stopwords = st.checkbox("Filter Standard Stop-Words", value=True, key="nlp_stop_words")
        with c3:
            sentiment_sensitivity = st.select_slider("Sentiment Polarity Threshold", options=["Strict", "Balanced", "Permissive"], value="Balanced", key="nlp_sens")

    # Input source strategy
    input_mode = st.radio("Corpus Ingestion Source", ["Manual Corpus Input", "Upload Multi-Document Text (.txt / .csv)", "Sample System Logs"], horizontal=True, key="nlp_source_mode")
    
    raw_text = ""
    if input_mode == "Manual Corpus Input":
        raw_text = st.text_area(
            "Paste your text payload for system auditing:",
            value="""The Chrishem Sovereign Apex Hub integrates advanced artificial intelligence, 
genomic surveillance data pipelines, and natural language processing tools to streamline 
academic research and creative workflows. System administrator CHRISHEM oversees active deployments 
ensuring operational integrity, security compliance, and seamless multi-page analytics execution. 
Errors or security breaches are logged immediately to prevent pipeline degradation.""",
            height=200,
            key="nlp_corpus_input"
        )
    elif input_mode == "Upload Multi-Document Text (.txt / .csv)":
        uploaded_file = st.file_uploader("Upload Corpus Payload", type=["txt", "csv"], key="nlp_file_upload")
        if uploaded_file is not None:
            if uploaded_file.name.endswith(".csv"):
                temp_df = pd.read_csv(uploaded_file)
                text_col = st.selectbox("Select Target Text Column", temp_df.columns.tolist(), key="nlp_csv_text_col")
                raw_text = " ".join(temp_df[text_col].dropna().astype(str).tolist())
            else:
                raw_text = io.BytesIO(uploaded_file.getvalue()).read().decode("utf-8")
            st.success(f"✅ Successfully ingested: `{uploaded_file.name}` ({len(raw_text):,} characters)")
    else:
        raw_text = """[SYSTEM_LOG 2026-08-21]: Administrator CHRISHEM initialized secure container vault. 
Status: OPTIMAL. All genomics pipelines and Notion live data feeds operating seamlessly. 
Warning: Minor latency detected in external API bridge. Mitigation protocols deployed automatically. 
Research telemetry confirms successful execution of mcr-gene surveillance and wastewater audits at Muni University."""

    if not raw_text.strip():
        st.warning("⚠️ Corpus input is empty. Provide text data to run diagnostics.")
        return

    # Text Metrics Computation
    words = re.findall(r'\b\w+\b', raw_text.lower())
    sentences = [s.strip() for s in re.split(r'[.!?]+', raw_text) if s.strip()]
    paragraphs = [p.strip() for p in raw_text.split('\n') if p.strip()]

    # High-level Metrics Dashboard
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Characters", f"{len(raw_text):,}")
    m2.metric("Tokens (Words)", f"{len(words):,}")
    m3.metric("Sentences", f"{len(sentences):,}")
    m4.metric("Paragraphs", f"{len(paragraphs):,}")
    m5.metric("Avg Token Length", f"{np.mean([len(w) for w in words]):.1f}" if words else "0")

    st.markdown("---")

    # Multi-Tab Analytics Canvas
    tab_freq, tab_sentiment, tab_regex, tab_audit = st.tabs([
        "📊 Token Frequency & N-Grams", 
        "💬 Sentiment & Polarity Audit", 
        "🔍 Regex Pattern & Entity Miner", 
        "📄 Automated Executive Summary"
    ])

    with tab_freq:
        st.markdown("#### Frequency Distribution & Key Vocabulary")
        stop_words = {"the", "and", "to", "of", "a", "in", "is", "it", "that", "for", "on", "with", "as", "this", "an", "by", "or", "at"} if remove_stopwords else set()
        filtered_words = [w for w in words if w not in stop_words and len(w) >= min_word_length]

        if filtered_words:
            freq_df = pd.Series(filtered_words).value_counts().reset_index()
            freq_df.columns = ["Token", "Frequency"]
            
            col_chart, col_data = st.columns([2, 1])
            with col_chart:
                st.bar_chart(freq_df.set_index("Token").head(12))
            with col_data:
                st.dataframe(freq_df.head(15), use_container_width=True, hide_index=True)
        else:
            st.info("No tokens match the current filtering parameters.")

    with tab_sentiment:
        st.markdown("#### Heuristic Sentiment & Tone Polarity Audit")
        
        pos_lexicon = {"apex", "hub", "success", "secure", "advanced", "seamless", "integrity", "optimal", "clean", "robust", "operational", "successful"}
        neg_lexicon = {"error", "fail", "warning", "breach", "degrading", "unstable", "missing", "risk", "latency", "minor"}
        
        pos_found = [w for w in words if w in pos_lexicon]
        neg_found = [w for w in words if w in neg_lexicon]
        
        score = len(pos_found) - len(neg_found)
        if score > 0:
            tone_status = "Positive / Stable"
            color_badge = "🟢"
        elif score == 0:
            tone_status = "Neutral / Balanced"
            color_badge = "🟡"
        else:
            tone_status = "Cautionary / Alert State"
            color_badge = "🔴"

        st.markdown(f"### {color_badge} Assessed Corpus Tone: **{tone_status}** (Polarity Score: `{score}`)")

        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown("**Constructive Indicators:**")
            st.write(", ".join(set(pos_found)) if pos_found else "None detected")
        with sc2:
            st.markdown("**Risk / Warning Indicators:**")
            st.write(", ".join(set(neg_found)) if neg_found else "None detected")

    with tab_regex:
        st.markdown("#### Advanced Regular Expression & Entity Extraction")
        preset = st.selectbox("Select Regex Pattern Preset", [
            "Custom Pattern",
            "Capitalized Entities (Proper Nouns)",
            "Email Addresses",
            "Dates / Timestamps (YYYY-MM-DD)",
            "Numeric Digits / Codes"
        ], key="nlp_regex_preset")

        preset_dict = {
            "Custom Pattern": r"\b[A-Za-z]+\b",
            "Capitalized Entities (Proper Nouns)": r"\b[A-Z][a-z]+\b",
            "EmailAddresses": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "Dates / Timestamps (YYYY-MM-DD)": r"\d{4}-\d{2}-\d{2}",
            "Numeric Digits / Codes": r"\b\d+\b"
        }

        default_pat = preset_dict.get(preset, r"\b[A-Z][a-z]+\b")
        custom_pattern = st.text_input("Active Regular Expression", value=default_pat, key="nlp_custom_regex")

        if custom_pattern:
            try:
                extracted = re.findall(custom_pattern, raw_text)
                st.markdown(f"Found **{len(extracted)}** total matches:")
                if extracted:
                    res_view = pd.DataFrame({"Match Index": range(1, len(extracted)+1), "Extracted Value": extracted})
                    st.dataframe(res_view, use_container_width=True, hide_index=True)
                    
                    # Export button for matches
                    csv_bytes = res_view.to_csv(index=False).encode("utf-8")
                    st.download_button("📥 Download Extracted Matches (CSV)", data=csv_bytes, file_name="regex_matches.csv", mime="text/csv")
            except Exception as e:
                st.error(f"Invalid Regex Syntax: {e}")

    with tab_audit:
        st.markdown("#### Automated Text Audit & Executive Breakdown")
        if st.button("🚀 Generate Full Text Audit Report", type="primary", key="run_text_audit"):
            report_content = f"""# CHRISHEM SOVEREIGN APEX HUB - NLP AUDIT REPORT
Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
Administrator: CHRISHEM

## Corpus Metadata
- Total Character Count: {len(raw_text):,}
- Total Word Count: {len(words):,}
- Sentence Count: {len(sentences):,}
- Paragraph Count: {len(paragraphs):,}

## Tone & Sentiment Evaluation
- Assessed Polarity State: {tone_status} (Score: {score})
- Positive Tokens Identified: {len(set(pos_found))}
- Warning/Risk Tokens Identified: {len(set(neg_found))}

## Top 5 Frequent Terms
{chr(10).join([f'- {row.Token}: {row.Frequency}' for _, row in freq_df.head(5).iterrows()]) if 'freq_df' in locals() and not freq_df.empty else 'N/A'}
"""
            st.code(report_content, language="markdown")
            st.download_button("⬇️ Download Full Audit Report (.md)", data=report_content, file_name="nlp_audit_report.md", mime="text/markdown")

if __name__ == "__main__":
    render_comprehensive_ai_nlp_suite()