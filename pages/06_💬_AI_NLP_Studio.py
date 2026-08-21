import os
import sys
import re
import html
import json
import logging
from typing import Tuple, Optional, List, Dict, Any

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import get_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_dataset_context_banner,
    render_export_buttons,
)

# Setup Logger
logger = logging.getLogger("AINLPStudio")
logger.setLevel(logging.INFO)

# Optional Imports
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    SKLEARN_TEXT_AVAILABLE = True
except ImportError:
    SKLEARN_TEXT_AVAILABLE = False

# Pre-compiled Regex Patterns
RE_WORDS = re.compile(r"[a-zA-Z']+")
RE_CLEAN = re.compile(r"[^\w\s]")
RE_ROWS = re.compile(r"how many rows|row count|number of records|dataset size", re.IGNORECASE)
RE_CORR = re.compile(r"correlation between (.+?) and (.+)", re.IGNORECASE)
RE_TOP = re.compile(r"top (\d+)\s+(.+?)\s+by\s+(.+)", re.IGNORECASE)
RE_AGG_GROUP = re.compile(
    r"(average|avg|mean|sum|total|count|max|maximum|highest|min|minimum|lowest|median|std|standard deviation)\s+(?:of\s+)?(.+?)\s+by\s+(.+)",
    re.IGNORECASE
)
RE_AGG_SINGLE = re.compile(
    r"(average|avg|mean|sum|total|count|max|maximum|highest|min|minimum|lowest|median|std|standard deviation)\s+(?:of\s+)?(.+)",
    re.IGNORECASE
)

_POSITIVE_WORDS = frozenset([
    "great", "excellent", "outstanding", "good", "fast", "high", "reliable", "seamless", 
    "clear", "impressive", "robust", "exceptional", "optimal", "love", "best", "amazing", 
    "wonderful", "helpful", "efficient", "smooth", "intuitive", "responsive", "stable", 
    "accurate", "easy", "simple", "flexible", "powerful", "strong"
])

_NEGATIVE_WORDS = frozenset([
    "slow", "bad", "error", "bug", "limited", "issue", "minor", "problems", "need", 
    "missing", "failed", "delay", "poor", "terrible", "awful", "confusing", "broken", 
    "crash", "fail", "difficult", "hard", "weak", "inconsistent", "frustrating", 
    "buggy", "unstable", "lacking", "disappointing"
])

_AGG_WORDS = {
    "average": "mean", "avg": "mean", "mean": "mean",
    "sum": "sum", "total": "sum",
    "count": "count",
    "max": "max", "maximum": "max", "highest": "max",
    "min": "min", "minimum": "min", "lowest": "min",
    "median": "median",
    "std": "std", "standard deviation": "std",
}

def get_df() -> pd.DataFrame:
    """Retrieve active session dataframe or produce synchronized mock data."""
    df = get_active_dataframe()
    if df is None or df.empty:
        records = [
            "System performance and analytical throughput are exceptionally high.",
            "Encountered limited network access during remote synchronization.",
            "User interface clarity and workflow navigation are intuitive.",
            "Algorithm cross-validation requires extended processing time with larger datasets.",
            "Excellent automated chart recommendations for bioinformatics gene expression analysis.",
            "Clinical reference range auditor flagged elevated glucose levels effectively.",
            "Fast execution speeds and high-precision bioinformatics calculations.",
            "Minor bugs encountered uploading multi-page document archives.",
            "Custom chart studio provides outstanding visual export features.",
            "Data security compliance and encryption standards are well maintained.",
            "UI color scheme is vibrant, ergonomic, and easy to read.",
            "Need more granular options for automated time-series forecasting.",
            "Great overall experience using the integrated ML pipeline controller.",
            "Slow response times querying large databases without prior indexing.",
            "Seamless export options for publication-ready visual assets.",
            "Clear feedback messages provided on invalid column types during data setup.",
            "Outstanding qualitative coding summary for academic research synthesis.",
            "High performance, reliability, and robust stability across analytics platforms.",
            "Advanced integration capabilities streamline complex workflow orchestrations.",
            "Scalable architecture handles high-density data workloads with absolute precision."
        ]
        categories = ["Clinical", "UX", "Performance", "Features"]
        np.random.seed(42)
        return pd.DataFrame({
            "Record_ID": [f"REC-{i:03d}" for i in range(1, 21)],
            "Feedback_Text": records,
            "Category": np.random.choice(categories, 20),
            "Metric_Value": np.random.uniform(10.0, 99.0, 20).round(2)
        })
    return df.copy()

def _lexicon_sentiment(text: str) -> Tuple[str, float]:
    tokens = RE_WORDS.findall(str(text).lower())
    if not tokens:
        return "Neutral", 0.0
    pos = sum(1 for t in tokens if t in _POSITIVE_WORDS)
    neg = sum(1 for t in tokens if t in _NEGATIVE_WORDS)
    compound = (pos - neg) / (pos + neg + 1.0)
    label = "Positive" if compound > 0.05 else ("Negative" if compound < -0.05 else "Neutral")
    return label, round(compound, 4)

@st.cache_resource
def _get_vader_analyzer():
    if VADER_AVAILABLE:
        return SentimentIntensityAnalyzer()
    return None

def score_sentiment(text: str) -> Tuple[str, float]:
    analyzer = _get_vader_analyzer()
    if analyzer is not None:
        scores = analyzer.polarity_scores(str(text))
        compound = scores["compound"]
        label = "Positive" if compound >= 0.05 else ("Negative" if compound <= -0.05 else "Neutral")
        return label, round(compound, 4)
    return _lexicon_sentiment(text)

@st.cache_data(show_spinner=False)
def _perform_tfidf_kmeans(texts: List[str], n_clusters: int) -> Tuple[List[int], pd.DataFrame]:
    n_clusters = max(1, min(n_clusters, len(texts)))
    vectorizer = TfidfVectorizer(stop_words="english", max_features=500, min_df=1)
    X = vectorizer.fit_transform(texts)
    
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(X).tolist()
    
    terms = vectorizer.get_feature_names_out()
    order_centroids = km.cluster_centers_.argsort()[:, ::-1]
    
    themes = []
    for i in range(n_clusters):
        top_terms = [terms[ind] for ind in order_centroids[i, :6] if ind < len(terms)]
        doc_count = int(sum(1 for lbl in labels if lbl == i))
        themes.append({
            "Cluster": i, 
            "Top Terms": ", ".join(top_terms), 
            "Document Count": doc_count
        })
    return labels, pd.DataFrame(themes)

def render_text_analysis(df: pd.DataFrame) -> None:
    section_header(
        "💬 Advanced Text Mining & Sentiment Intelligence", 
        "Extract keyword frequencies, sentiment polarities, and semantic n-gram phrase structures."
    )
    if not VADER_AVAILABLE:
        st.caption("ℹ️ Using built-in fallback lexicon. Install vaderSentiment for accurate sentiment intensity analysis.")

    text_cols = list(df.select_dtypes(include=["object", "string"]).columns)
    if not text_cols:
        st.warning("⚠️ No string or text columns detected in the active dataset.")
        return

    col = st.selectbox("Select Text Corpus Column", text_cols, key="nlp_text_col_v2")
    tab_freq, tab_sent, tab_ngram = st.tabs(["🔤 Keyword Frequency", "😊 Sentiment Engine", "🔗 N-Gram Phrase Mining"])

    with tab_freq:
        st.markdown("#### High-Frequency Token Analysis")
        series_data = df[col].dropna().astype(str)
        all_words = [
            w.lower().strip(".,!?()[]{}\"'") 
            for text in series_data 
            for w in text.split() 
            if len(w) > 3
        ]
        
        if not all_words:
            st.info("No tokens longer than 3 characters were found.")
        else:
            freq = pd.Series(all_words).value_counts().head(20).reset_index()
            freq.columns = ["Keyword", "Frequency"]

            col1, col2 = st.columns([1, 1])
            with col1:
                st.dataframe(freq, use_container_width=True, hide_index=True)
            with col2:
                if PLOTLY_AVAILABLE:
                    fig = px.bar(
                        freq.head(10), x="Frequency", y="Keyword", orientation="h",
                        template="plotly_dark", height=380, title="Top 10 Token Frequencies"
                    )
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.bar_chart(freq.set_index("Keyword").head(10))

    with tab_sent:
        engine_label = "VADER Engine" if VADER_AVAILABLE else "Lexicon Fallback"
        st.markdown(f"#### Sentiment Polarity Audit ({engine_label})")

        if st.button("😊 Run Sentiment Audit", type="primary", key="run_sentiment_v2"):
            anal_df = df[[col]].dropna().copy()
            anal_df[col] = anal_df[col].astype(str)
            
            results = anal_df[col].apply(score_sentiment)
            anal_df["Sentiment_Label"] = [r[0] for r in results]
            anal_df["Sentiment_Score"] = [r[1] for r in results]

            counts = anal_df["Sentiment_Label"].value_counts()
            c1, c2, c3 = st.columns(3)
            c1.metric("Positive", int(counts.get("Positive", 0)))
            c2.metric("Neutral", int(counts.get("Neutral", 0)))
            c3.metric("Negative", int(counts.get("Negative", 0)))

            if PLOTLY_AVAILABLE:
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    fig_pie = px.pie(names=counts.index, values=counts.values, hole=0.4, template="plotly_dark", height=280, title="Sentiment Split")
                    fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig_pie, use_container_width=True)
                with col_chart2:
                    fig_hist = px.histogram(anal_df, x="Sentiment_Score", nbins=15, template="plotly_dark", height=280, title="Score Distribution")
                    fig_hist.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig_hist, use_container_width=True)

            st.dataframe(anal_df, use_container_width=True, hide_index=True)
            render_export_buttons(anal_df, base_name="sentiment_analysis_results")

    with tab_ngram:
        st.markdown("#### N-Gram Phrase Collocation Mining")
        depth = st.selectbox("N-Gram Depth", ["Bi-grams (2-word)", "Tri-grams (3-word)"], key="ngram_depth_v2")
        n = 2 if "Bi-grams" in depth else 3
        
        raw_texts = df[col].dropna().astype(str).tolist()
        phrases = []
        for text in raw_texts:
            tokens = [w.lower().strip(".,!?()[]") for w in text.split() if len(w) > 2]
            if len(tokens) >= n:
                phrases.extend([" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)])

        if not phrases:
            st.info("Insufficient token length to form n-grams.")
        else:
            freq_ngrams = pd.Series(phrases).value_counts().head(15).reset_index()
            freq_ngrams.columns = ["Collocation Phrase", "Frequency Count"]
            st.dataframe(freq_ngrams, use_container_width=True, hide_index=True)

def render_ai_insights(df: pd.DataFrame) -> None:
    section_header("🤖 AI Insights & Executive Intelligence Reporting", "Automated exploratory data profiling, collinearity detection, and executive summary generation.")

    rows, cols = df.shape
    missing = int(df.isnull().sum().sum())
    numeric_df = df.select_dtypes(include=[np.number])

    st.markdown("### 📊 Automated Structural Findings")
    insights: List[str] = []
    insights.append(f"**Dataset Architecture:** Dimensions of `{rows:,}` rows by `{cols}` features.")
    
    if missing > 0:
        insights.append(f"**Data Completeness:** Detected `{missing:,}` missing cells requiring handling or imputation.")
    else:
        insights.append("**Data Completeness Optimal:** Zero missing values detected across active records.")

    if not numeric_df.empty and numeric_df.shape[1] >= 2:
        corr = numeric_df.corr(numeric_only=True).abs()
        np.fill_diagonal(corr.values, 0)
        max_corr = corr.max().max()
        if max_corr > 0.75:
            col_max = corr.max().idxmax()
            row_max = corr[col_max].idxmax()
            insights.append(f"**Multivariate Collinearity:** Strong correlation between `{row_max}` and `{col_max}` ($r = {max_corr:.2f}$).")

    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        pct = (dup_count / rows) * 100 if rows > 0 else 0
        insights.append(f"**Duplicate Records:** `{dup_count:,}` duplicate rows detected ({pct:.1f}% of total).")

    for ins in insights:
        st.markdown(
            f'<div style="background:#0b1321; border-left:4px solid #00f2fe; border-radius:8px; padding:0.9rem 1.1rem; margin-bottom:0.6rem; color:#f8fafc;">{ins}</div>', 
            unsafe_allow_html=True
        )

    st.markdown("### 📄 Executive Report Generation")
    report_lines = [
        "# EXECUTIVE DATA INTELLIGENCE REPORT",
        f"**Generated timestamp:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Active Source:** {st.session_state.get('source_name', 'active_dataset.csv')}",
        "",
        "## Core Metrics",
        f"- Total Record Count: {rows:,}",
        f"- Total Feature Count: {cols}",
        f"- Missing Cell Count: {missing:,}",
        f"- Duplicate Rows: {dup_count:,}",
        "",
        "## Key Analytical Insights"
    ] + [f"- {ins}" for ins in insights]

    report = "\n".join(report_lines)
    st.download_button(
        "⬇️ Download Enterprise Markdown Report", 
        data=report, 
        file_name="executive_intelligence_report.md", 
        mime="text/markdown", 
        use_container_width=True
    )

def _find_column(text: str, columns: List[str]) -> Optional[str]:
    text_clean = RE_CLEAN.sub("", text).lower().strip()
    col_map = {RE_CLEAN.sub("", c).lower().strip(): c for c in columns}
    
    if text_clean in col_map:
        return col_map[text_clean]
        
    for cleaned_name, original_name in sorted(col_map.items(), key=lambda x: -len(x[0])):
        if cleaned_name in text_clean or text_clean in cleaned_name:
            return original_name
            
    tokens = set(text_clean.split())
    best, max_overlap = None, 0
    for cleaned_name, original_name in col_map.items():
        overlap = len(tokens & set(cleaned_name.split()))
        if overlap > max_overlap:
            best = original_name
            max_overlap = overlap
    return best

def parse_and_execute_nl_query(query: str, df: pd.DataFrame) -> Tuple[str, Any, Optional[str]]:
    q = query.strip()
    if not q:
        return "error", "Query string cannot be empty.", None

    all_cols = list(df.columns)
    num_cols = list(df.select_dtypes(include=[np.number]).columns)

    if RE_ROWS.search(q):
        return "metric", f"{len(df):,} rows", "Total Row Count"

    m = RE_CORR.search(q)
    if m:
        c1 = _find_column(m.group(1), all_cols)
        c2 = _find_column(m.group(2), all_cols)
        if c1 and c2 and c1 in num_cols and c2 in num_cols:
            val = df[c1].corr(df[c2])
            return "metric", f"r = {val:.4f}", f"Correlation between '{c1}' and '{c2}'"
        return "error", "Could not identify valid numeric columns for correlation analysis.", None

    m = RE_TOP.search(q)
    if m:
        n_str, dim_raw, metric_raw = m.groups()
        dim_col = _find_column(dim_raw, all_cols)
        metric_col = _find_column(metric_raw, num_cols)
        if dim_col and metric_col:
            res = df.groupby(dim_col, as_index=False)[metric_col].mean().sort_values(metric_col, ascending=False).head(int(n_str))
            return "table", res, f"Top {n_str} '{dim_col}' grouped by mean '{metric_col}'"
        return "error", f"Could not match dimension '{dim_raw}' or numeric metric '{metric_raw}'.", None

    m = RE_AGG_GROUP.search(q)
    if m:
        func_word, metric_raw, group_raw = m.groups()
        func = _AGG_WORDS.get(func_word.lower(), "mean")
        metric_col = _find_column(metric_raw, num_cols if func != "count" else all_cols)
        group_col = _find_column(group_raw, all_cols)
        if metric_col and group_col:
            res = df.groupby(group_col, as_index=False).agg({metric_col: func}).sort_values(metric_col, ascending=False)
            return "table", res, f"{func.title()} of '{metric_col}' grouped by '{group_col}'"
        return "error", f"Unable to resolve columns: metric '{metric_raw}', group '{group_raw}'.", None

    m = RE_AGG_SINGLE.search(q)
    if m:
        func_word, metric_raw = m.groups()
        func = _AGG_WORDS.get(func_word.lower(), "mean")
        metric_col = _find_column(metric_raw, num_cols if func != "count" else all_cols)
        if metric_col:
            if func == "count":
                val = df[metric_col].count()
                return "metric", f"{val:,}", f"Count of non-null entries in '{metric_col}'"
            val = getattr(df[metric_col], func)()
            return "metric", f"{val:,.4f}", f"{func.title()} of '{metric_col}'"
        return "error", f"Could not identify target numeric column '{metric_raw}'.", None

    return "unrecognized", None, None

def render_nl_query(df: pd.DataFrame) -> None:
    section_header("💬 Natural Language Query Console", "Pattern-matched NL-to-Pandas execution engine operating over active dataset columns.")

    with st.expander("ℹ️ Supported Analytical Question Patterns"):
        st.markdown(
            "- `how many rows are there`\n"
            "- `average of <column>` / `sum of <column>` / `max of <column>` / `median of <column>`\n"
            "- `average <metric_column> by <group_column>`\n"
            "- `correlation between <column_a> and <column_b>`\n"
            "- `top 5 <group_column> by <metric_column>`"
        )

    query = st.text_area("Enter your analytical query", placeholder="e.g., average Metric_Value by Category", key="nl_query_input_v2")

    if st.button("🔍 Execute Query", type="primary", key="run_nl_query_v2"):
        kind, payload, caption = parse_and_execute_nl_query(query, df)
        if kind == "metric":
            st.success(f"✅ {caption}")
            st.metric(caption, payload)
        elif kind == "table":
            st.success(f"✅ {caption}")
            st.dataframe(payload, use_container_width=True, hide_index=True)
            render_export_buttons(payload, base_name="nl_query_results")
        elif kind == "error":
            st.error(f"🚫 {payload}")
        else:
            st.warning("⚠️ Pattern not recognized. Review the supported format structure above.")

def render_synth_and_gap(df: pd.DataFrame) -> None:
    section_header("🔬 Research Synthesis & Methodology Checklist", "Data-derived thematic clustering of corpus data with dynamic methodology auditing.")

    tab_synth, tab_gap = st.tabs(["🧩 Research Synthesizer", "💡 Methodology Checklist"])

    with tab_synth:
        st.markdown("#### Data-Derived Thematic Clustering")
        text_cols = list(df.select_dtypes(include=["object", "string"]).columns)
        if text_cols:
            col = st.selectbox("Select Target Text Column", text_cols, key="synth_col_v2")
            n_clusters = st.slider("Number of Themes (Clusters)", 2, 8, 3, key="synth_n_clusters_v2")
            
            if st.button("🧩 Synthesize Corpus Findings", type="primary", key="run_synth_v2"):
                texts = df[col].dropna().astype(str).tolist()
                if len(texts) < 2:
                    st.warning("Cluster analysis requires at least 2 non-empty records.")
                elif SKLEARN_TEXT_AVAILABLE:
                    labels, themes_df = _perform_tfidf_kmeans(texts, n_clusters)
                    st.markdown(f"**Extracted {len(themes_df)} themes via TF-IDF Vectorization & KMeans Clustering:**")
                    st.dataframe(themes_df, use_container_width=True, hide_index=True)
                    
                    selected_cluster = st.selectbox("Inspect cluster sample records", themes_df["Cluster"].tolist(), key="synth_cluster_inspect")
                    samples = [t for t, l in zip(texts, labels) if l == selected_cluster][:5]
                    st.markdown("**Cluster Sample Documents:**")
                    for s in samples:
                        st.markdown(f"> {s}")
                    render_export_buttons(themes_df, base_name="research_clusters")
                else:
                    st.info("Scikit-learn is unavailable; using basic frequency counting.")
                    words = [w.lower().strip(".,!?") for t in texts for w in t.split() if len(w) > 4]
                    top_words = pd.Series(words).value_counts().head(n_clusters).reset_index()
                    top_words.columns = ["Keyword", "Count"]
                    st.dataframe(top_words, use_container_width=True, hide_index=True)
        else:
            st.info("No categorical/string text columns found.")

    with tab_gap:
        st.markdown("#### Dataset-Grounded Methodology Checklist")
        domain = st.selectbox("Research Domain Context", ["Bioinformatics & Genomics", "Clinical Trials & Health", "Agritech & Food Security", "Artificial Intelligence & ML", "Educational Analytics", "General"], key="gap_domain_v2")

        if st.button("💡 Generate Checklist", type="primary", key="run_gap_v2"):
            n = len(df)
            datetime_cols = df.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns.tolist()
            cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
            dup_rate = (df.duplicated().mean() * 100) if n > 0 else 0.0
            missing_rate = (df.isnull().mean().mean() * 100) if n > 0 else 0.0

            findings = []
            if n < 100:
                findings.append(f"**Sample Size Limit:** Small size ($n={n}$). Ensure statistical power calculations are applied.")
            else:
                findings.append(f"**Sample Size:** Sufficient volume ($n={n:,}$) for parametric inference.")

            if not datetime_cols:
                findings.append("**Temporal Dimension:** Lack of time-series indices limits cross-sectional sequence tracking.")
            else:
                findings.append(f"**Temporal Depth:** Detected time tracking column `{datetime_cols[0]}`.")

            if cat_cols:
                max_card = max(df[c].nunique() for c in cat_cols)
                findings.append(f"**Categorical Diversity:** `{len(cat_cols)}` factor variables identified. High cardinality at level `{max_card}`.")

            if dup_rate > 0:
                findings.append(f"**Data Integrity Warning:** `{dup_rate:.1f}%` duplicate records detected.")
            if missing_rate > 0:
                findings.append(f"**Completeness:** Overall missingness metric stands at `{missing_rate:.1f}%`.")

            findings.append(f"**Domain Alignment ({domain}):** Verify compliance with standards applicable to {domain}.")

            for f in findings:
                st.markdown(f"- {f}")
            
            md_export = "\n".join(f"- {f}" for f in findings)
            st.download_button("⬇️ Download Checklist (.md)", data=md_export, file_name="methodology_checklist.md", mime="text/markdown")

def render_audio() -> None:
    section_header("🎙️ Text-to-Speech Narration Engine", "Browser-based speech synthesis using Web Speech API.")
    
    st.info("Utilizes native client-side browser speech engines. Supported voices depend on system runtime platform.")

    text_input = st.text_area("Text to Narrate", value="This is a live test of the narration engine, reading directly from your browser.", height=100, key="tts_input_v2")
    
    c1, c2 = st.columns(2)
    with c1:
        rate = st.slider("Speech Rate", 0.5, 2.0, 1.0, 0.1, key="tts_rate_v2")
    with c2:
        pitch = st.slider("Pitch", 0.0, 2.0, 1.0, 0.1, key="tts_pitch_v2")

    safe_text_json = json.dumps(text_input)

    components.html(
        f"""
        <div style="font-family: system-ui, -apple-system, sans-serif; color: #f8fafc;">
            <button id="speakBtn" style="background:#38BDF8; color:#0b1321; border:none; border-radius:6px; padding:0.6rem 1.2rem; font-weight:700; cursor:pointer;">
                🔊 Speak Text
            </button>
            <button id="stopBtn" style="background:#334155; color:#f8fafc; border:none; border-radius:6px; padding:0.6rem 1.2rem; font-weight:700; cursor:pointer; margin-left:0.5rem;">
                ⏹️ Stop
            </button>
            <p id="ttsStatus" style="margin-top:0.6rem; color:#94a3b8; font-size:0.85rem;"></p>
        </div>
        <script>
            const payloadText = {safe_text_json};
            const rate = {rate};
            const pitch = {pitch};
            const statusEl = document.getElementById('ttsStatus');

            document.getElementById('speakBtn').onclick = function() {{
                if (!('speechSynthesis' in window)) {{
                    statusEl.innerText = 'Speech synthesis is not supported in this browser environment.';
                    return;
                }
                window.speechSynthesis.cancel();
                const utter = new SpeechSynthesisUtterance(payloadText);
                utter.rate = rate;
                utter.pitch = pitch;
                utter.onstart = () => statusEl.innerText = 'Status: Speaking...';
                utter.onend = () => statusEl.innerText = 'Status: Playback complete.';
                utter.onerror = (e) => statusEl.innerText = 'Status: Error - ' + e.error;
                window.speechSynthesis.speak(utter);
            };

            document.getElementById('stopBtn').onclick = function() {{
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    statusEl.innerText = 'Status: Stopped.';
                }
            };
        </script>
        """,
        height=130,
    )

def main() -> None:
    try:
        from modules.subscription import require_active_subscription
        require_active_subscription(hub_id="nlp")
    except ImportError:
        pass

    setup_page("AI & NLP Studio", "💬", initial_sidebar_state="expanded")

    try:
        from modules.user_preferences import render_readability_fix, render_accent_color_css
        render_readability_fix()
        render_accent_color_css()
    except ImportError:
        pass

    hero_card(
        "💬 AI & NLP Studio — Consolidated AI & Text Analytics Hub",
        "Natural language processing studio featuring text mining, sentiment analysis, custom query parsing, data synthesis, methodology auditing, and text-to-speech capabilities.",
        badge_text="AI & NLP STUDIO • ENTERPRISE TIER"
    )

    render_dataset_context_banner()

    df = get_df()

    tabs = st.tabs([
        "💬 Text Mining & Sentiment",
        "🤖 AI Insights & Reports",
        "💬 Natural Language Query",
        "🔬 Research Synthesis & Checklist",
        "🎙️ Voice & Audio Engine",
    ])

    with tabs[0]:
        render_text_analysis(df)
    with tabs[1]:
        render_ai_insights(df)
    with tabs[2]:
        render_nl_query(df)
    with tabs[3]:
        render_synth_and_gap(df)
    with tabs[4]:
        render_audio()

    render_standard_footer("AI & NLP STUDIO")

if __name__ == "__main__":
    main()
