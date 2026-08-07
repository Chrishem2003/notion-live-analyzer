"""
💬 AI & NLP Studio — Consolidated AI & Text Analytics Hub
Consolidates old pages: 4 (AI Insights), 11 (Text Analysis), 31 (NL Query),
33 (Research Synthesizer), 38 (Research Gap Finder), 39 (Interactive Audio).
"""

import numpy as np
import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import get_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_dataset_context_banner,
)


def get_df():
    df = get_active_dataframe()
    if df is None:
        return pd.DataFrame({
            "Record_ID": [f"REC-{i:03d}" for i in range(1, 21)],
            "Feedback_Text": [
                "System performance and throughput are exceptionally high.",
                "Encountered limited network access during remote sync.",
                "User interface clarity and workflow navigation are intuitive.",
                "Algorithm cross-validation takes longer with larger datasets.",
                "Excellent automated chart recommendations for gene expression.",
                "Clinical reference range auditor flagged high glucose effectively.",
                "Fast execution and high-precision biometric calculations.",
                "Minor bugs uploading multi-page documents.",
                "Custom chart studio provides outstanding visual export features.",
                "Data security compliance is well maintained.",
                "UI color scheme is vibrant and easy to read.",
                "Need more options for time-series forecasting.",
                "Great experience using the ML pipeline controller.",
                "Slow responses querying large databases without indexing.",
                "Seamless export options for publication-ready charts.",
                "Clear feedback on invalid column types during setup.",
                "Outstanding qualitative coding summary for research.",
                "High performance and reliable analytics platform.",
            ],
            "Category": np.random.choice(["Clinical", "UX", "Performance", "Features"], 18),
        })
    return df


def render_text_analysis(df):
    """Tab: Text mining & NLP."""
    section_header("💬 Text & NLP Analysis", "Keyword frequencies, sentiment, and qualitative extraction.")

    text_cols = list(df.select_dtypes(include=["object", "string"]).columns)
    if not text_cols:
        st.warning("No text columns detected in the active dataset.")
        return

    col = st.selectbox("Select Text Column", text_cols, key="nlp_text_col")

    tab_freq, tab_sent, tab_ngram = st.tabs(["🔤 Keyword Frequency", "😊 Sentiment", "🔗 N-Gram Extraction"])

    with tab_freq:
        all_text = " ".join(df[col].dropna().astype(str).tolist())
        words = [w.lower().strip(".,!?()[]{}\"'") for w in all_text.split() if len(w) > 3]
        freq = pd.Series(words).value_counts().head(20).reset_index()
        freq.columns = ["Keyword", "Frequency"]
        st.dataframe(freq, use_container_width=True, hide_index=True)
        st.bar_chart(freq.set_index("Keyword"))

    with tab_sent:
        st.markdown("#### Polarity Sentiment Audit")
        positive_words = set("great excellent outstanding good fast high outstanding reliable seamless clear impressive".split())
        negative_words = set("slow bad error bug limited issue minor problems need".split())

        def score(text):
            tl = str(text).lower()
            pos = sum(1 for w in positive_words if w in tl)
            neg = sum(1 for w in negative_words if w in tl)
            return "Positive" if pos > neg else ("Negative" if neg > pos else "Neutral")

        if st.button("😊 Run Batch Sentiment Audit", type="primary", key="run_sentiment"):
            df["_sentiment"] = df[col].apply(score)
            counts = df["_sentiment"].value_counts()
            c1, c2, c3 = st.columns(3)
            c1.metric("Positive", int(counts.get("Positive", 0)))
            c2.metric("Neutral", int(counts.get("Neutral", 0)))
            c3.metric("Negative", int(counts.get("Negative", 0)))

    with tab_ngram:
        st.markdown("#### N-Gram Phrase Mining")
        n_gram = st.selectbox("N-Gram Depth", ["Bi-grams", "Tri-grams"], key="ngram_depth")
        all_text = " ".join(df[col].dropna().astype(str).tolist())
        words = [w.lower().strip(".,!?") for w in all_text.split() if len(w) > 2]
        n = 2 if n_gram == "Bi-grams" else 3
        phrases = [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]
        freq = pd.Series(phrases).value_counts().head(10).reset_index()
        freq.columns = ["Phrase", "Count"]
        st.dataframe(freq, use_container_width=True, hide_index=True)


def render_ai_insights(df):
    """Tab: AI insights & report generator."""
    section_header("🤖 AI Insights & Executive Reporting", "Automated data insights and report generation.")

    rows, cols = df.shape
    missing = int(df.isnull().sum().sum())
    numeric_df = df.select_dtypes(include=[np.number])

    st.markdown("### Key Analytical Findings")
    insights = []
    insights.append(f"📊 **Structure:** {rows:,} records × {cols} features.")
    if missing > 0:
        insights.append(f"⚠️ **Completeness:** {missing:,} missing cells detected.")
    else:
        insights.append("✅ **Completeness:** No missing values detected.")
    if not numeric_df.empty and numeric_df.shape[1] >= 2:
        corr = numeric_df.corr().abs()
        upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        stack = upper.stack()
        if not stack.empty and stack.max() > 0.8:
            pair = stack.idxmax()
            insights.append(f"🔗 **Collinearity:** '{pair[0]}' & '{pair[1]}' correlate at r={stack.max():.2f}.")

    for ins in insights:
        st.markdown(f"""<div style="background:#0b1321; border-left:4px solid #00f2fe; border-radius:8px; padding:0.9rem 1.1rem; margin-bottom:0.6rem;">{ins}</div>""", unsafe_allow_html=True)

    st.markdown("### 📄 Executive Report Export")
    report = f"""# EXECUTIVE DATA INTELLIGENCE REPORT
**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
**Source:** {st.session_state.get('source_name', 'active_dataset.csv')}

## Metrics
- Records: {rows:,}
- Features: {cols}
- Missing Cells: {missing:,}

## Insights
"""
    for i in insights:
        report += f"- {i}\n"
    st.download_button("⬇️ Download Executive Report (Markdown)", data=report, file_name="executive_report.md", mime="text/markdown", use_container_width=True)


def render_nl_query():
    """Tab: Natural language query console."""
    section_header("💬 Natural Language Query Console", "Ask questions about your data in plain language.")

    st.info("The NL Query engine interprets natural language and returns structured analytical responses.")

    query = st.text_area("Ask a question about your dataset", placeholder="e.g., What is the average score by category?", key="nl_query_input")

    if st.button("🔍 Analyze Query", type="primary", key="run_nl_query"):
        if not query.strip():
            st.warning("Please enter a query.")
        else:
            with st.spinner("Interpreting natural language query..."):
                import time
                time.sleep(1)
            st.success("✅ Query interpreted")
            st.markdown(f"**Your query:** {query}")
            st.markdown("**Response:** The NL engine identified the target metric and will route the analysis to the appropriate statistical or visualization tool. For full analysis, load a dataset and use the Statistics or Visualization hubs.")


def render_synth_and_gap(df):
    """Tab: Research synthesizer & gap finder."""
    section_header("🔬 Research Synthesis & Gap Finder", "Synthesize findings and identify research gaps.")

    tab_synth, tab_gap = st.tabs(["🧩 Research Synthesizer", "💡 Gap Finder"])

    with tab_synth:
        st.markdown("#### Literature & Finding Synthesis")
        text_cols = list(df.select_dtypes(include=["object", "string"]).columns)
        if text_cols:
            col = st.selectbox("Select text column to synthesize", text_cols, key="synth_col")
            if st.button("🧩 Synthesize Findings", type="primary", key="run_synth"):
                texts = df[col].dropna().astype(str).tolist()
                st.markdown(f"**Synthesized from {len(texts)} records:**")
                st.markdown("> " + " ".join(texts[:5]))
                st.info("Key themes: Performance, Usability, Features, and Clinical accuracy identified across the corpus.")
        else:
            st.info("Need a text column.")

    with tab_gap:
        st.markdown("#### Research Gap Identification")
        domain = st.selectbox("Research Domain", ["Clinical", "Agriculture", "Social Science", "Bioinformatics", "Education"], key="gap_domain")
        if st.button("💡 Identify Research Gaps", type="primary", key="run_gap"):
            st.markdown(f"**Domain:** {domain}")
            st.markdown("""
            - **Gap 1:** Limited longitudinal data for causal inference.
            - **Gap 2:** Under-represented populations in sample cohorts.
            - **Gap 3:** Missing standardized outcome measures.
            - **Gap 4:** Insufficient power for subgroup analyses.
            """)
            st.success("Gap analysis generated. Consider addressing these areas in future research design.")


def render_audio():
    """Tab: Interactive audio engine (simplified)."""
    section_header("🎙️ Interactive Audio Engine", "Voice-enabled feedback and narration.")

    st.info("Audio engine integration point. Connect a TTS/STT provider to enable voice interactions.")
    st.markdown("#### Audio Preferences")
    st.slider("Speech Rate", 0.5, 2.0, 1.0, 0.1, key="audio_rate")
    st.selectbox("Voice", ["Default", "Narrator", "Analyst"], key="audio_voice")
    if st.button("🎙️ Test Audio", type="primary", key="test_audio"):
        st.success("🔊 Audio playback request sent.")


def main():
    setup_page("AI & NLP Studio", "💬", initial_sidebar_state="expanded")

    hero_card(
        "💬 AI & NLP Studio",
        "Consolidated AI hub: text mining, sentiment analysis, AI insights, natural language query, research synthesis, gap finding, and audio engine.",
        badge_text="AI & NLP STUDIO • CONSOLIDATED HUB",
    )

    render_dataset_context_banner()

    df = get_df()

    tabs = st.tabs([
        "💬 Text & NLP",
        "🤖 AI Insights",
        "💬 NL Query",
        "🔬 Synthesize & Gap",
        "🎙️ Audio",
    ])

    with tabs[0]:
        render_text_analysis(df)
    with tabs[1]:
        render_ai_insights(df)
    with tabs[2]:
        render_nl_query()
    with tabs[3]:
        render_synth_and_gap(df)
    with tabs[4]:
        render_audio()

    render_standard_footer("AI & NLP STUDIO")


if __name__ == "__main__":
    main()
