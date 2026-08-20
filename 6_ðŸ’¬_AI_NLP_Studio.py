import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
"""
ðŸ’¬ AI & NLP Studio — Consolidated AI & Text Analytics Hub (Premium)
Text mining, real sentiment analysis, a genuine natural-language-to-query engine, data-grounded
research synthesis (TF-IDF + KMeans clustering, not canned text), a dataset-grounded methodology
checklist, and real browser-based text-to-speech.

Changelog vs prior version:
- FIXED (ValueError shape mismatch): Fixed the fallback dataset generator in `get_df()` where
  "Record_ID" (20 items) and "Category" (20 items) mismatched the length of "Feedback_Text" (18 items).
  All arrays are now synchronized to 20 elements.
"""

import re

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


def get_df():
    df = get_active_dataframe()
    if df is None:
        return pd.DataFrame({
            "Record_ID": [f"REC-{i:03d}" for i in range(1, 21)],
            "Feedback_Text": [
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
            ],
            "Category": np.random.choice(["Clinical", "UX", "Performance", "Features"], 20),
        })
    return df


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Text mining & real sentiment
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
_POSITIVE_WORDS = set("great excellent outstanding good fast high reliable seamless clear impressive robust "
                       "exceptional optimal love best amazing wonderful helpful efficient smooth intuitive "
                       "responsive stable accurate easy simple flexible powerful strong".split())
_NEGATIVE_WORDS = set("slow bad error bug limited issue minor problems need missing failed delay poor terrible "
                       "awful confusing broken crash fail difficult hard weak inconsistent frustrating buggy "
                       "unstable lacking disappointing".split())


def _lexicon_sentiment(text: str):
    tokens = re.findall(r"[a-zA-Z']+", str(text).lower())
    pos = sum(1 for t in tokens if t in _POSITIVE_WORDS)
    neg = sum(1 for t in tokens if t in _NEGATIVE_WORDS)
    compound = (pos - neg) / (pos + neg + 1)
    label = "Positive" if compound > 0.05 else ("Negative" if compound < -0.05 else "Neutral")
    return label, compound


@st.cache_resource
def _get_vader():
    return SentimentIntensityAnalyzer()


def score_sentiment(text: str):
    if VADER_AVAILABLE:
        analyzer = _get_vader()
        s = analyzer.polarity_scores(str(text))
        compound = s["compound"]
        label = "Positive" if compound >= 0.05 else ("Negative" if compound <= -0.05 else "Neutral")
        return label, compound
    return _lexicon_sentiment(text)


def render_text_analysis(df):
    section_header("ðŸ’¬ Advanced Text Mining & Sentiment Intelligence", "Extract keyword frequencies, sentiment polarities, and semantic n-gram phrase structures.")
    if not VADER_AVAILABLE:
        st.caption("â„¹ï¸ Using a built-in word-boundary-safe lexicon for sentiment — the more accurate compound-score engine will activate automatically once available in this deployment.")

    text_cols = list(df.select_dtypes(include=["object", "string"]).columns)
    if not text_cols:
        st.warning("âš ï¸ No text columns detected in the active dataset.")
        return

    col = st.selectbox("Select Text Corpus Column", text_cols, key="nlp_text_col_upg")

    tab_freq, tab_sent, tab_ngram = st.tabs(["ðŸ”¤ Keyword Frequency", "ðŸ˜Š Sentiment Engine", "ðŸ”— N-Gram Phrase Mining"])

    with tab_freq:
        st.markdown("#### High-Frequency Token Analysis")
        all_text = " ".join(df[col].dropna().astype(str).tolist())
        words = [w.lower().strip(".,!?()[]{}\"'") for w in all_text.split() if len(w) > 3]
        freq = pd.Series(words).value_counts().head(20).reset_index()
        freq.columns = ["Keyword", "Frequency"]

        col1, col2 = st.columns([1, 1])
        with col1:
            st.dataframe(freq, use_container_width=True, hide_index=True)
        with col2:
            if PLOTLY_AVAILABLE:
                fig = px.bar(freq.head(10), x="Frequency", y="Keyword", orientation="h", template="plotly_dark", height=380)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.bar_chart(freq.set_index("Keyword").head(10))

    with tab_sent:
        st.markdown("#### Sentiment Polarity Audit" + (" (VADER)" if VADER_AVAILABLE else " (Lexicon Fallback)"))

        if st.button("ðŸ˜Š Run Sentiment Audit", type="primary", key="run_sentiment_upg"):
            scored = df[col].dropna().astype(str).apply(score_sentiment)
            df.loc[scored.index, "_sentiment_label"] = scored.apply(lambda t: t[0])
            df.loc[scored.index, "_sentiment_score"] = scored.apply(lambda t: t[1])

            counts = df["_sentiment_label"].value_counts()
            c1, c2, c3 = st.columns(3)
            c1.metric("Positive", int(counts.get("Positive", 0)))
            c2.metric("Neutral", int(counts.get("Neutral", 0)))
            c3.metric("Negative", int(counts.get("Negative", 0)))

            if PLOTLY_AVAILABLE:
                fig = px.pie(names=counts.index, values=counts.values, hole=0.4, template="plotly_dark", height=300)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig, use_container_width=True)

                fig2 = px.histogram(df.dropna(subset=["_sentiment_score"]), x="_sentiment_score", nbins=20, template="plotly_dark", height=280, title="Compound Sentiment Score Distribution")
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig2, use_container_width=True)

            result_view = df[[col, "_sentiment_label", "_sentiment_score"]].dropna(subset=["_sentiment_label"])
            st.dataframe(result_view, use_container_width=True, hide_index=True)
            render_export_buttons(result_view, base_name="sentiment_scored_records")

    with tab_ngram:
        st.markdown("#### N-Gram Phrase Collocation Mining")
        n_gram = st.selectbox("N-Gram Depth", ["Bi-grams (2-word)", "Tri-grams (3-word)"], key="ngram_depth_upg")
        all_text = " ".join(df[col].dropna().astype(str).tolist())
        words = [w.lower().strip(".,!?") for w in all_text.split() if len(w) > 2]
        n = 2 if "Bi-grams" in n_gram else 3
        phrases = [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]
        freq = pd.Series(phrases).value_counts().head(12).reset_index()
        freq.columns = ["Phrase", "Frequency Count"]
        st.dataframe(freq, use_container_width=True, hide_index=True)


def render_ai_insights(df):
    section_header("ðŸ¤– AI Insights & Executive Intelligence Reporting", "Automated exploratory data profiling, collinearity detection, and executive brief compilation.")

    rows, cols = df.shape
    missing = int(df.isnull().sum().sum())
    numeric_df = df.select_dtypes(include=[np.number])

    st.markdown("### ðŸ“Š Automated Structural Findings")
    insights = []
    insights.append(f"**Dataset Architecture:** Dimensions of `{rows:,}` rows by `{cols}` features.")
    if missing > 0:
        insights.append(f"**Data Completeness Warning:** Detected `{missing:,}` missing cells requiring imputation.")
    else:
        insights.append("**Data Completeness Optimal:** Zero missing values detected across active records.")

    if not numeric_df.empty and numeric_df.shape[1] >= 2:
        corr = numeric_df.corr().abs()
        upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        stack = upper.stack()
        if not stack.empty and stack.max() > 0.75:
            pair = stack.idxmax()
            insights.append(f"**Multivariate Collinearity:** Strong correlation identified between `{pair[0]}` and `{pair[1]}` at $r = {stack.max():.2f}$.")

    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        insights.append(f"**Duplicate Records:** `{dup_count:,}` exact duplicate rows detected ({dup_count/rows*100:.1f}% of dataset).")

    for ins in insights:
        st.markdown(f"""<div style="background:#0b1321; border-left:4px solid #00f2fe; border-radius:8px; padding:0.9rem 1.1rem; margin-bottom:0.6rem; color:#f8fafc;">{ins}</div>""", unsafe_allow_html=True)

    st.markdown("### ðŸ“„ Executive Report Generation")
    report = f"""# EXECUTIVE DATA INTELLIGENCE REPORT
**Generated timestamp:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
**Active Source:** {st.session_state.get('source_name', 'active_dataset.csv')}

## Core Metrics
- Total Record Count: {rows:,}
- Total Feature Count: {cols}
- Missing Cell Count: {missing:,}
- Duplicate Rows: {dup_count:,}

## Key Analytical Insights
"""
    for i in insights:
        report += f"- {i}\n"

    st.download_button("â¬‡ï¸ Download Enterprise Markdown Report", data=report, file_name="executive_intelligence_report.md", mime="text/markdown", use_container_width=True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Real NL-to-query engine (rule-based, no LLM)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
_AGG_WORDS = {
    "average": "mean", "avg": "mean", "mean": "mean",
    "sum": "sum", "total": "sum",
    "count": "count",
    "max": "max", "maximum": "max", "highest": "max",
    "min": "min", "minimum": "min", "lowest": "min",
    "median": "median",
    "std": "std", "standard deviation": "std",
}


def _find_column(text: str, columns) -> str:
    text = text.strip()
    candidates = sorted(columns, key=lambda c: -len(c))
    for c in candidates:
        if c.lower() in text.lower():
            return c
    text_tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    best, best_overlap = None, 0
    for c in columns:
        col_tokens = set(re.findall(r"[a-z0-9]+", c.lower()))
        overlap = len(text_tokens & col_tokens)
        if overlap > best_overlap:
            best, best_overlap = c, overlap
    return best


def parse_and_execute_nl_query(query: str, df: pd.DataFrame):
    q = query.lower().strip()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    all_cols = df.columns.tolist()

    if re.search(r"how many rows|row count|number of records|dataset size", q):
        return "metric", f"{len(df):,} rows", "Row count"

    m = re.search(r"correlation between (.+?) and (.+)", q)
    if m:
        c1, c2 = _find_column(m.group(1), all_cols), _find_column(m.group(2), all_cols)
        if c1 and c2 and c1 in numeric_cols and c2 in numeric_cols:
            r = df[c1].corr(df[c2])
            return "metric", f"r = {r:.4f}", f"Correlation between {c1} and {c2}"
        return "error", "Could not identify two numeric columns for a correlation.", None

    m = re.search(r"top (\d+)\s+(.+?)\s+by\s+(.+)", q)
    if m:
        n, dim_text, metric_text = m.groups()
        dim_col, metric_col = _find_column(dim_text, all_cols), _find_column(metric_text, all_cols)
        if dim_col and metric_col and metric_col in numeric_cols:
            result = df.groupby(dim_col)[metric_col].mean().reset_index().sort_values(metric_col, ascending=False).head(int(n))
            return "table", result, f"Top {n} {dim_col} by mean {metric_col}"
        return "error", f"Could not resolve columns from '{dim_text}' / '{metric_text}'.", None

    m = re.search(r"(average|avg|mean|sum|total|count|max|maximum|highest|min|minimum|lowest|median|std|standard deviation)\s+(?:of\s+)?(.+?)\s+by\s+(.+)", q)
    if m:
        func_word, metric_text, group_text = m.groups()
        func = _AGG_WORDS.get(func_word, "mean")
        metric_col, group_col = _find_column(metric_text, all_cols), _find_column(group_text, all_cols)
        if metric_col and group_col:
            if func == "count":
                result = df.groupby(group_col)[metric_col].count().reset_index()
            else:
                result = df.groupby(group_col)[metric_col].agg(func).reset_index()
            result = result.sort_values(metric_col, ascending=False)
            return "table", result, f"{func.title()} of {metric_col}, grouped by {group_col}"
        return "error", f"Could not resolve columns from '{metric_text}' / '{group_text}'.", None

    m = re.search(r"(average|avg|mean|sum|total|count|max|maximum|highest|min|minimum|lowest|median|std|standard deviation)\s+(?:of\s+)?(.+)", q)
    if m:
        func_word, metric_text = m.groups()
        func = _AGG_WORDS.get(func_word)
        metric_col = _find_column(metric_text, all_cols)
        if func and metric_col and metric_col in numeric_cols:
            val = getattr(df[metric_col], func)()
            return "metric", f"{val:,.4f}", f"{func_word.title()} of {metric_col}"
        if func_word == "count" and metric_col:
            return "metric", f"{df[metric_col].count():,}", f"Non-null count of {metric_col}"

    return "unrecognized", None, None


def render_nl_query(df):
    section_header("ðŸ’¬ Natural Language Query Console", "A rule-based NL-to-pandas engine — it recognizes common analytical question patterns and computes the real answer from the active dataset.")

    with st.expander("â„¹ï¸ Supported question patterns"):
        st.markdown(
            "- `how many rows are there`\n"
            "- `average of <column>` / `sum of <column>` / `max of <column>` / `median of <column>`\n"
            "- `average <column> by <column>` (grouped aggregation)\n"
            "- `correlation between <column> and <column>`\n"
            "- `top 5 <column> by <column>`"
        )

    query = st.text_area("Enter your analytical question", placeholder="e.g., average Metric_Value by Category", key="nl_query_input_upg")

    if st.button("ðŸ” Execute Query", type="primary", key="run_nl_query_upg"):
        if not query.strip():
            st.warning("âš ï¸ Please provide a valid query string.")
        else:
            kind, payload, caption = parse_and_execute_nl_query(query, df)
            if kind == "metric":
                st.success(f"✅ {caption}")
                st.metric(caption, payload)
            elif kind == "table":
                st.success(f"✅ {caption}")
                st.dataframe(payload, use_container_width=True, hide_index=True)
                render_export_buttons(payload, base_name="nl_query_result")
            elif kind == "error":
                st.error(f"ðŸš« {payload}")
            else:
                st.warning("âš ï¸ Couldn't match this question to a supported pattern — see the examples above.")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Real thematic synthesis (TF-IDF + KMeans) & data-grounded checklist
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def _tfidf_kmeans_themes(texts: list, n_clusters: int):
    n_clusters = max(1, min(n_clusters, len(texts)))
    vectorizer = TfidfVectorizer(stop_words="english", max_features=300, min_df=1)
    X = vectorizer.fit_transform(texts)
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(X)
    terms = vectorizer.get_feature_names_out()
    order_centroids = km.cluster_centers_.argsort()[:, ::-1]
    themes = []
    for i in range(n_clusters):
        top_terms = [terms[ind] for ind in order_centroids[i, :6] if ind < len(terms)]
        themes.append({"Cluster": i, "Top Terms": ", ".join(top_terms), "Document Count": int((labels == i).sum())})
    return labels, pd.DataFrame(themes)


def _keyword_frequency_themes(texts: list, top_n: int = 4):
    all_text = " ".join(texts).lower()
    words = [w.strip(".,!?()[]{}\"'") for w in all_text.split() if len(w) > 4]
    freq = pd.Series(words).value_counts().head(top_n)
    return pd.DataFrame({"Cluster": range(len(freq)), "Top Terms": freq.index, "Frequency": freq.values})


def render_synth_and_gap(df):
    section_header("ðŸ”¬ Research Synthesis & Methodology Checklist", "Data-derived thematic clustering of your text corpus, and a dataset-grounded methodology checklist.")

    tab_synth, tab_gap = st.tabs(["ðŸ§© Research Synthesizer", "ðŸ’¡ Methodology Checklist"])

    with tab_synth:
        st.markdown("#### Data-Derived Thematic Clustering")
        if not SKLEARN_TEXT_AVAILABLE:
            st.caption("â„¹ï¸ `scikit-learn` not available — using keyword-frequency grouping as a fallback.")
        text_cols = list(df.select_dtypes(include=["object", "string"]).columns)
        if text_cols:
            col = st.selectbox("Select Text Column to Synthesize", text_cols, key="synth_col_upg")
            n_clusters = st.slider("Number of Themes", 2, 8, 4, key="synth_n_clusters")
            if st.button("ðŸ§© Synthesize Corpus Findings", type="primary", key="run_synth_upg"):
                texts = df[col].dropna().astype(str).tolist()
                if len(texts) < 2:
                    st.warning("Need at least 2 non-empty text records to cluster.")
                else:
                    if SKLEARN_TEXT_AVAILABLE:
                        labels, themes_df = _tfidf_kmeans_themes(texts, n_clusters)
                        st.markdown(f"**Derived {len(themes_df)} theme cluster(s) from {len(texts)} records via TF-IDF + KMeans:**")
                        st.dataframe(themes_df, use_container_width=True, hide_index=True)
                        cluster_choice = st.selectbox("View example records from cluster", themes_df["Cluster"].tolist(), key="synth_cluster_view")
                        examples = [t for t, l in zip(texts, labels) if l == cluster_choice][:5]
                        for ex in examples:
                            st.markdown(f"> {ex}")
                    else:
                        themes_df = _keyword_frequency_themes(texts, n_clusters)
                        st.dataframe(themes_df, use_container_width=True, hide_index=True)
                    render_export_buttons(themes_df, base_name="research_synthesis_themes")
        else:
            st.info("âš ï¸ Requires a text column in the dataset.")

    with tab_gap:
        st.markdown("#### Dataset-Grounded Methodology Checklist")
        st.caption("This is a heuristic checklist derived from properties of your *actual loaded dataset*.")
        domain = st.selectbox("Research Domain Context (for labeling only)", ["Bioinformatics & Genomics", "Clinical Trials & Health", "Agritech & Food Security", "Artificial Intelligence & ML", "Educational Analytics", "General"], key="gap_domain_upg")

        if st.button("ðŸ’¡ Generate Checklist", type="primary", key="run_gap_upg"):
            n = len(df)
            datetime_cols = df.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns.tolist()
            cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
            dup_rate = df.duplicated().mean() * 100 if n else 0
            missing_rate = df.isnull().mean().mean() * 100 if n else 0

            findings = []
            if n < 100:
                findings.append(f"**Sample Size:** n={n} is small — statistical power for detecting moderate effects will be limited.")
            else:
                findings.append(f"**Sample Size:** n={n:,} — adequate for standard inferential tests.")

            if not datetime_cols:
                findings.append("**Temporal Coverage:** No datetime column detected — this dataset appears to be a single time-point snapshot.")
            else:
                span = (df[datetime_cols[0]].max() - df[datetime_cols[0]].min())
                findings.append(f"**Temporal Coverage:** Datetime column `{datetime_cols[0]}` detected, spanning {span}.")

            if cat_cols:
                max_card = max(df[c].nunique() for c in cat_cols)
                findings.append(f"**Demographic/Categorical Diversity:** {len(cat_cols)} categorical column(s); largest has {max_card} distinct levels.")
            else:
                findings.append("**Demographic/Categorical Diversity:** No categorical grouping columns detected.")

            if dup_rate > 1:
                findings.append(f"**Data Validation:** {dup_rate:.1f}% of rows are exact duplicates.")
            if missing_rate > 5:
                findings.append(f"**Data Completeness:** Average missingness across columns is {missing_rate:.1f}%.")

            findings.append(f"**Domain Context ({domain}):** Cross-check these dataset-level findings against domain validation standards.")

            for f in findings:
                st.markdown(f"- {f}")
            st.success("✅ Checklist generated from the properties of your active dataset.")
            st.download_button("â¬‡ï¸ Download Checklist (.md)", data="\n".join(f"- {f}" for f in findings), file_name="methodology_checklist.md", mime="text/markdown", key="dl_checklist")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Real browser-based text-to-speech (Web Speech API)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def render_audio():
    section_header("ðŸŽ™ï¸ Text-to-Speech Narration Engine", "Real browser-based speech synthesis via the Web Speech API.")

    st.info("This uses your browser's built-in speech synthesis (Web Speech API). Availability and voice selection depend on your browser.")

    default_text = "This is a live test of the narration engine, reading directly from your browser."
    text_to_speak = st.text_area("Text to narrate", value=default_text, height=100, key="tts_text_input")
    col1, col2 = st.columns(2)
    with col1:
        speech_rate = st.slider("Speech Rate", 0.5, 2.0, 1.0, 0.1, key="audio_rate_upg")
    with col2:
        pitch = st.slider("Pitch", 0.0, 2.0, 1.0, 0.1, key="audio_pitch_upg")

    safe_text = text_to_speak.replace("\\", "\\\\").replace("`", "\\`").replace("</script>", "<\\/script>")

    components.html(
        f"""
        <div style="font-family: Inter, sans-serif; color: #f8fafc;">
            <button id="speakBtn" style="background:#38BDF8;color:#0b1321;border:none;border-radius:8px;padding:0.6rem 1.2rem;font-weight:700;cursor:pointer;">
                ðŸ”Š Speak Text
            </button>
            <button id="stopBtn" style="background:#334155;color:#f8fafc;border:none;border-radius:8px;padding:0.6rem 1.2rem;font-weight:700;cursor:pointer;margin-left:0.5rem;">
                â¹ Stop
            </button>
            <p id="ttsStatus" style="margin-top:0.6rem;color:#94a3b8;font-size:0.85rem;"></p>
        </div>
        <script>
            const text = `{safe_text}`;
            const rate = {speech_rate};
            const pitch = {pitch};
            const statusEl = document.getElementById('ttsStatus');

            document.getElementById('speakBtn').onclick = function() {{
                if (!('speechSynthesis' in window)) {{
                    statusEl.innerText = 'Speech synthesis is not supported in this browser.';
                    return;
                }}
                window.speechSynthesis.cancel();
                const utter = new SpeechSynthesisUtterance(text);
                utter.rate = rate;
                utter.pitch = pitch;
                utter.onstart = () => statusEl.innerText = 'Speaking...';
                utter.onend = () => statusEl.innerText = 'Finished.';
                utter.onerror = (e) => statusEl.innerText = 'Error: ' + e.error;
                window.speechSynthesis.speak(utter);
            }};
            document.getElementById('stopBtn').onclick = function() {{
                window.speechSynthesis.cancel();
                statusEl.innerText = 'Stopped.';
            }};
        </script>
        """,
        height=140,
    )


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription(hub_id="nlp")

    setup_page("AI & NLP Studio", "ðŸ’¬", initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "ðŸ’¬ AI & NLP Studio — Consolidated AI & Text Analytics Hub (Premium)",
        "Enterprise-grade natural language processing studio featuring text mining, real sentiment analysis, a genuine natural-language-to-query engine, data-derived research synthesis, a dataset-grounded methodology checklist, and real browser-based speech synthesis.",
        badge_text="AI & NLP STUDIO â€¢ PREMIUM TIER",
    )

    render_dataset_context_banner()

    df = get_df()

    tabs = st.tabs([
        "ðŸ’¬ Text Mining & Sentiment",
        "ðŸ¤– AI Insights & Reports",
        "ðŸ’¬ Natural Language Query",
        "ðŸ”¬ Research Synthesis & Checklist",
        "ðŸŽ™ï¸ Voice & Audio Engine",
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
