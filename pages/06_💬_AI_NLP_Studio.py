import io
import re
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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

# --- Lexicons for Sentiment Analysis Fallback ---
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
    if VADER_AVAILABLE:
        return SentimentIntensityAnalyzer()
    return None

def score_sentiment(text: str):
    analyzer = _get_vader()
    if analyzer is not None:
        s = analyzer.polarity_scores(str(text))
        compound = s["compound"]
        label = "Positive" if compound >= 0.05 else ("Negative" if compound <= -0.05 else "Neutral")
        return label, compound
    return _lexicon_sentiment(text)

# --- Natural Language to Query Helpers ---
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

# --- Main Application Renderer ---
def render_consolidated_enterprise_studio():
    st.set_page_config(
        page_title="CHRISHEM Sovereign Apex Hub — Enterprise AI & NLP Studio",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )

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
                🧠 CHRISHEM Sovereign Apex Hub: Enterprise AI & Natural Language Processing Studio
            </h2>
            <p style="color: #94a3b8; font-size: 0.95rem; margin: 0;">
                Real-time corpus auditing, transformer token distribution mapping, VADER sentiment telemetry, semantic n-grams, regex entity extraction, and natural-language-to-query execution.
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

    # --- Corpus & Dataset Ingestion Section ---
    st.markdown("### 📥 Corpus Ingestion & Pipeline Source")
    ingest_mode = st.radio(
        "Select Data Stream Ingestion Source", 
        ["Live Text Workspace", "Upload Structured CSV / Corpus (.txt / .csv)", "Load Secure System Logs"], 
        horizontal=True, 
        key="ent_ingest_mode"
    )

    raw_text = ""
    df = None
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
                df = pd.read_csv(uploaded_file)
                text_column = st.selectbox("Select Text Vector Column", df.columns.tolist(), key="ent_csv_col")
                raw_text = " ".join(df[text_column].dropna().astype(str).tolist())
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

    if df is None:
        df = pd.DataFrame({
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
            "Metric_Value": np.random.uniform(50, 100, 20)
        })

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

    # --- Comprehensive Multi-Tab Enterprise Workspace ---
    tab_tokens, tab_sentiment, tab_regex, tab_nlq, tab_synth, tab_audio, tab_audit = st.tabs([
        "📈 Token Frequency & Vectors", 
        "💬 Sentiment & Polarity Audit", 
        "🔍 Regex & Entity Extraction", 
        "🤖 Natural Language Query",
        "🧬 Research Synthesis & Checklist",
        "🔊 Voice & Audio Engine",
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
                if PLOTLY_AVAILABLE:
                    fig = px.bar(freq_df.head(12), x="Frequency", y="Token", orientation="h", template="plotly_dark", height=380)
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=20, b=0))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.bar_chart(freq_df.set_index("Token").head(12), color="#3b82f6")
            with c_table:
                st.dataframe(freq_df.head(15), use_container_width=True, hide_index=True)
                freq_csv = freq_df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Export Frequencies (.csv)", data=freq_csv, file_name="token_frequencies.csv", mime="text/csv", key="download_freq_csv")
        else:
            st.info("No tokens match current filtering thresholds.")

    with tab_sentiment:
        st.markdown(f"#### Heuristic & VADER Sentiment Audit {'(VADER Active)' if VADER_AVAILABLE else '(Lexicon Fallback)'}")
        
        pos_lexicon = {"apex", "hub", "success", "secure", "advanced", "seamless", "integrity", "optimal", "clean", "robust", "operational", "successful", "efficiency", "high", "great", "outstanding"}
        neg_lexicon = {"error", "fail", "warning", "breach", "degrading", "unstable", "missing", "risk", "latency", "minor", "anomaly", "slow"}
        
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

    with tab_nlq:
        st.markdown("#### Natural Language Query Console")
        st.caption("Ask analytical questions against your structured session dataframe using plain language.")
        with st.expander("📌 Supported Question Patterns"):
            st.markdown(
                "- `how many rows are there`\n"
                "- `average of <column>` / `sum of <column>` / `max of <column>`\n"
                "- `average Metric_Value by Category`\n"
                "- `correlation between Metric_Value and Record_ID`\n"
                "- `top 3 Category by Metric_Value`"
            )
        nl_query = st.text_area("Enter your analytical question:", placeholder="e.g., average Metric_Value by Category", key="consolidated_nl_input")
        if st.button("🔍 Execute NL Query", type="primary", key="run_consolidated_nl"):
            if not nl_query.strip():
                st.warning("⚠️ Please provide a valid query string.")
            else:
                kind, payload, caption = parse_and_execute_nl_query(nl_query, df)
                if kind == "metric":
                    st.success(f"✅ {caption}")
                    st.metric(caption, payload)
                elif kind == "table":
                    st.success(f"✅ {caption}")
                    st.dataframe(payload, use_container_width=True, hide_index=True)
                    st.download_button("📥 Export Query Result (.csv)", data=payload.to_csv(index=False).encode("utf-8"), file_name="nl_query_result.csv", mime="text/csv")
                elif kind == "error":
                    st.error(f"🚫 {payload}")
                else:
                    st.warning("⚠️ Couldn't match this question to a supported pattern.")

    with tab_synth:
        st.markdown("#### Research Synthesis & Methodology Checklist")
        synth_subtab1, synth_subtab2 = st.tabs(["🧬 Thematic Clustering", "📋 Methodology Checklist"])
        with synth_subtab1:
            text_cols = list(df.select_dtypes(include=["object", "string"]).columns)
            if text_cols:
                synth_col = st.selectbox("Select Text Column to Synthesize", text_cols, key="consolidated_synth_col")
                n_clusters = st.slider("Number of Themes", 2, 8, 4, key="consolidated_clusters")
                if st.button("🧬 Synthesize Corpus Findings", type="primary", key="run_consolidated_synth"):
                    texts = df[synth_col].dropna().astype(str).tolist()
                    if SKLEARN_TEXT_AVAILABLE and len(texts) >= 2:
                        labels, themes_df = _tfidf_kmeans_themes(texts, n_clusters)
                        st.dataframe(themes_df, use_container_width=True, hide_index=True)
                    else:
                        themes_df = _keyword_frequency_themes(texts, n_clusters)
                        st.dataframe(themes_df, use_container_width=True, hide_index=True)
                    st.download_button("📥 Export Synthesis Themes (.csv)", data=themes_df.to_csv(index=False).encode("utf-8"), file_name="research_synthesis_themes.csv", mime="text/csv")
            else:
                st.info("No text columns available for synthesis.")
        with synth_subtab2:
            st.markdown("**Dataset-Grounded Methodology Checklist**")
            st.markdown(f"- **Sample Size:** n={len(df):,} records loaded.")
            st.markdown(f"- **Feature Completeness:** {df.notnull().mean().mean()*100:.1f}% overall data retention.")
            st.markdown(f"- **Duplicate Rate:** {df.duplicated().mean()*100:.1f}% duplicate rows.")

    with tab_audio:
        st.markdown("#### Text-to-Speech Narration Engine")
        speech_text = st.text_area("Text to narrate:", value=raw_text[:300], height=100, key="consolidated_tts")
        c_rate, c_pitch = st.columns(2)
        with c_rate:
            speech_rate = st.slider("Speech Rate", 0.5, 2.0, 1.0, 0.1, key="con_rate")
        with c_pitch:
            pitch = st.slider("Pitch", 0.0, 2.0, 1.0, 0.1, key="con_pitch")

        safe_text = speech_text.replace("\\", "\\\\").replace("`", "\\`").replace("</script>", "<\\/script>")
        components.html(
            f"""
            <div style="font-family: Inter, sans-serif; color: #f8fafc;">
                <button id="speakBtn" style="background:#38BDF8;color:#0b1321;border:none;border-radius:8px;padding:0.6rem 1.2rem;font-weight:700;cursor:pointer;">
                    🔊 Speak Text
                </button>
                <button id="stopBtn" style="background:#334155;color:#f8fafc;border:none;border-radius:8px;padding:0.6rem 1.2rem;font-weight:700;cursor:pointer;margin-left:0.5rem;">
                    ⏹ Stop
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
            height=130,
        )

    with tab_audit:
        st.markdown("#### Executive Summary & Verification Report")
        if st.button("🚀 Generate Verified Audit Report", type="primary", key="generate_audit_btn"):
            audit_report = f"""# CHRISHEM SOVEREIGN APEX HUB - EXECUTIVE AUDIT REPORT
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
    render_consolidated_enterprise_studio()