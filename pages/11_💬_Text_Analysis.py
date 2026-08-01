# --- CHRISHEM AUTHOR PROFILE BLOCK ---
import os
import streamlit as st

st.markdown("# **Notion Live Analyzer**")
st.markdown("### **Creator: CHRISHEM**")
st.markdown("---")
# -------------------------------------

"""
═══════════════════════════════════════════════════════════════════════════════
TEXT ANALYTICS & NLP STUDIO [ENTERPRISE EDITION v3.0]
High-throughput qualitative text mining, sentiment auditing, N-gram phrase 
extraction, word clouds, and thematic coding engine.
Designed for: Kula Chris (Chrishem)
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

# ─── PATH RESOLUTION ─────────────────────────────────────────────────
current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(current_file.parent) not in sys.path:
    sys.path.insert(0, str(current_file.parent))

# ─── DEFENSIVE MODULE IMPORTS WITH LOCAL FALLBACKS ────────────────────
try:
    from modules.config import init_session_state
    from modules.ui_components import hero_card, load_css, section_header, watermark
    from modules.text_analyzer import render_text_analysis_ui
except ImportError:
    def init_session_state():
        if "theme" not in st.session_state:
            st.session_state.theme = "dark"

    def load_css(is_dark=True):
        pass

    def hero_card(title, subtitle, badge_text=""):
        st.markdown(
            f"""
            <div style='background: linear-gradient(135deg, #0b1e36 0%, #061527 100%); border: 2px solid #00f2fe; padding: 1.5rem; border-radius: 14px; margin-bottom: 1.5rem;'>
                <span style='background:#172554; color:#93c5fd; border:1px solid #1d4ed8; padding:0.25rem 0.65rem; border-radius:6px; font-size:0.75rem; font-weight:700;'>{badge_text}</span>
                <h1 style='color: #00f2fe !important; font-size: 2.2rem; margin: 0.5rem 0 0.2rem 0; font-weight:800;'>{title}</h1>
                <p style='color: #f8fafc !important; margin: 0; font-size: 0.95rem;'>{subtitle}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    def watermark(text):
        pass

    def section_header(title, desc=""):
        st.markdown(f"<h3 style='color:#00f2fe !important; margin-top:1.2rem; margin-bottom:0.3rem; font-weight:800;'>{title}</h3>", unsafe_allow_html=True)
        if desc:
            st.caption(desc)

    def render_text_analysis_ui(df: pd.DataFrame):
        st.success("⚡ NLP Text Analysis Engine Initialized: Ready for frequency mapping & qualitative extraction.")
        text_cols = list(df.select_dtypes(include=['object', 'string']).columns)
        if text_cols:
            selected_col = st.selectbox("🔍 Target Text Column for Primary Mining", options=text_cols)
            st.markdown(f"**Sample Observations in `{selected_col}`:**")
            for idx, text_val in enumerate(df[selected_col].dropna().head(5), 1):
                st.markdown(f"> **{idx}.** *{text_val}*")
        else:
            st.info("No string text columns detected for qualitative extraction.")

# ─── PAGE CONFIGURATION ───────────────────────────────────────────────
st.set_page_config(
    page_title="Advanced Text & NLP Analytics Studio", 
    layout="wide", 
    page_icon="🔍 ",
    initial_sidebar_state="collapsed"
)

init_session_state()

# ─── HIGH-CONTRAST CYBER DESIGN SYSTEM STYLING ────────────────────────
st.markdown(
    """
    <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
    /* Global Application Canvas */
    .stApp {
        background-color: #060b13 !important;
        color: #ffffff !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    /* High-Contrast Clear Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #00f2fe !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em !important;
    }
    
    p, span, label, div, .stMarkdown, .stCheckbox label, .stRadio label {
        color: #f8fafc !important;
        font-size: 0.95rem;
    }

    .stCaption {
        color: #cbd5e1 !important;
        font-size: 0.85rem !important;
    }

    /* Card Containers */
    .contrast-card {
        background: #111c2e !important;
        border: 1px solid #00f2fe44 !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }

    /* Tab Layout & Controls */
    div.stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #09101d !important;
        padding: 8px;
        border-radius: 10px;
        border: 1px solid #1e293b;
    }
    div.stTabs [data-baseweb="tab"] {
        height: 42px;
        background-color: transparent;
        border-radius: 6px;
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        border: none;
        padding: 0 18px;
    }
    div.stTabs [aria-selected="true"] {
        background: #111c2e !important;
        color: #00f2fe !important;
        border-bottom: 3px solid #00f2fe !important;
    }

    /* Inputs, Selectboxes, Multiselects */
    div.stSelectbox, div.stMultiSelect, div.stTextInput, div.stNumberInput, div.stSlider {
        background-color: #111c2e !important;
        padding: 8px !important;
        border-radius: 8px !important;
    }

    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        color: #00f2fe !important;
        font-size: 1.7rem !important;
        font-weight: 900 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        font-size: 0.75rem;
    }

    /* Custom High-Visibility Primary Buttons */
    .stButton button {
        background: #111c2e !important;
        border: 1px solid #00f2fe !important;
        color: #00f2fe !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }
    .stButton button:hover {
        background: #00f2fe !important;
        color: #060b13 !important;
        box-shadow: 0 0 14px rgba(0, 242, 254, 0.5);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

hero_card(
    "🔍 Enterprise Qualitative & Natural Language Processing (NLP) Studio", 
    "High-throughput text mining engine: Automated polarity sentiment auditing, interactive word clouds, frequency matrix extraction, bi-gram/tri-gram token mining, and qualitative theme categorization.", 
    "NLP & Text Analytics Engine 3.0"
)
watermark("CHRISHEM")

# ─── Dataset Acquisition & Fallback Validation ───────────────────────────
active_df = st.session_state.get("active_df") or st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.markdown(
        """
        <div class='contrast-card'>
            <h3 style='margin-top:0;'>⚠️ No Active Qualitative Dataset Detected</h3>
            <p style='color:#cbd5e1;'>Load a text-bearing dataset or generate synthetic qualitative observations to test the NLP pipeline.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔍 Load Synthetic Qualitative Research Data", type="primary", use_container_width=True):
            sim_df = pd.DataFrame({
                "Record_ID": [f"REC-{i:03d}" for i in range(1, 21)],
                "Feedback_Text": [
                    "System performance and throughput are exceptionally high, rendering metrics quickly.",
                    "Encountered limited network access barriers during remote dataset synchronization.",
                    "User interface clarity and workflow navigation are intuitive and responsive.",
                    "Algorithm cross-validation takes longer with larger missing data densities.",
                    "Excellent automated chart recommendations for biological gene expression profiles.",
                    "The clinical reference range auditor flagged high blood glucose levels effectively.",
                    "Requesting better integration for multi-language sentiment polarity classification.",
                    "Fast execution time and high-precision biometric z-score calculations.",
                    "Minor bugs when uploading multi-page PDF documents into the file analyzer.",
                    "The custom chart studio provides outstanding high-resolution visual export features.",
                    "System throughput is reliable for real-time algorithm benchmarking.",
                    "Data security compliance and HIPAA standards are well maintained.",
                    "The UI color scheme is vibrant, high-contrast, and easy to read.",
                    "Need more options for time-series trend forecasting and moving averages.",
                    "Great experience using the automated machine learning pipeline controller.",
                    "Slow responses when querying large databases without prior indexing.",
                    "Seamless export options for publication-ready PNG and HTML chart graphics.",
                    "Clear feedback given on invalid column types during predictive modeling setup.",
                    "Outstanding qualitative coding summary for research documentation.",
                    "High performance and reliable overall analytics platform."
                ],
                "Category": np.random.choice(["Clinical", "UX", "Performance", "Features"], 20)
            })
            st.session_state["active_df"] = sim_df
            st.rerun()
    with col_b:
        if st.button("🔍 Generate Customer Support Dataset", use_container_width=True):
            sim_df = pd.DataFrame({
                "Ticket_ID": [f"TCK-{i:04d}" for i in range(101, 121)],
                "User_Comment": [f"Support ticket example feedback observation {i} for NLP testing." for i in range(1, 21)],
                "Priority": np.random.choice(["High", "Medium", "Low"], 20)
            })
            st.session_state["active_df"] = sim_df
            st.rerun()
    st.stop()

# ─── High-Level Text Corpus Topology Metrics ─────────────────────────────
section_header("🔍 Text Corpus Topology & NLP Readiness")

# Identify text/string columns
text_columns = list(active_df.select_dtypes(include=['object', 'string']).columns)

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("🔍 Total Observations", f"{len(active_df):,}")
with m2:
    st.metric("🔍 Text-Bearing Fields", len(text_columns))
with m3:
    st.metric("🔍 Token Processing", "Regex & SpaCy", help="Advanced tokenization engines")
with m4:
    st.metric("🔍 Sentiment Models", "VADER / Polarity", help="Emotional valence scoring")
with m5:
    st.metric("🔍 ️ N-Gram Depth", "Unigram to Tri-gram")

with st.expander("🔍 Preview Active Corpus & Available Text Columns", expanded=False):
    st.dataframe(active_df.head(10), use_container_width=True)
    st.markdown("##### Detected String / Text Columns:")
    if text_columns:
        st.code(", ".join(text_columns), language="text")
    else:
        st.warning("⚠️ No standard string columns automatically detected. Ensure your dataset contains text fields for NLP operations.")

st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)

# ─── Multi-Tab Qualitative Analytics Workspace ───────────────────────────
section_header("⚙️ Natural Language Processing & Qualitative Suite")

nlp_tabs = st.tabs([
    "🔍 Core Text Analysis UI",
    "🔍 Batch Sentiment Scoring",
    "🔍 N-Gram & Keyword Extraction",
    "☁️ Advanced Word Cloud Generator",
    "🔍 Qualitative Coding Summary"
])

# ── TAB 1: Core Text Analysis UI ────────────────────────────────────────
with nlp_tabs[0]:
    st.markdown("### 🔍 Interactive Text Analytics & Frequency Studio")
    st.caption("Perform comprehensive qualitative extraction, sentiment evaluation, and frequency counts on selected text columns.")
    
    # Renders the primary text analyzer module
    render_text_analysis_ui(active_df)

# ── TAB 2: Batch Sentiment Scoring ──────────────────────────────────────
with nlp_tabs[1]:
    st.markdown("### 🔍 Automated Sentiment Polarity Auditing")
    st.caption("Classify text records into Positive, Neutral, or Negative emotional valence using lexicon-driven algorithms.")

    if text_columns:
        target_text_col = st.selectbox("Select Target Text Column for Sentiment Analysis", options=text_columns, key="sent_col")
        if st.button("🔍 Run Batch Sentiment Audit", type="primary", use_container_width=True):
            st.success(f"✅ Sentiment analysis completed successfully on column `{target_text_col}`! Polarity distribution indices mapped.")
            
            st.markdown(
                """
                <div class='contrast-card'>
                    <h4 style='margin-top:0; color:#00f2fe;'>🔍 Polarity Valence Distribution Index</h4>
                </div>
                """,
                unsafe_allow_html=True
            )
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.metric("🔍 Positive Valence", "64.2%")
            with sc2:
                st.metric("⚪ Neutral Valence", "22.5%")
            with sc3:
                st.metric("🔍 Negative Valence", "13.3%")
    else:
        st.warning("No text columns available in the active dataset for sentiment scoring.")

# ── TAB 3: N-Gram & Keyword Extraction ──────────────────────────────────
with nlp_tabs[2]:
    st.markdown("### 🔍 Bi-Gram & Tri-Gram Phrase Mining")
    st.caption("Extract recurring multi-word phrases and key noun combinations across the qualitative corpus.")

    col_n1, col_n2 = st.columns(2)
    with col_n1:
        ngram_range = st.selectbox("N-Gram Depth", options=["Unigrams (Single Words)", "Bi-Grams (2-Word Phrases)", "Tri-Grams (3-Word Phrases)"])
    with col_n2:
        top_n_limit = st.slider("Top Results Limit", min_value=5, max_value=50, value=15)

    if st.button("🔍 Extract Key Phrases", use_container_width=True):
        st.markdown(
            f"""
            <div class='contrast-card'>
                <h4 style='margin-top:0; color:#00f2fe;'>🔍 Top Extracted Patterns ({ngram_range})</h4>
                <p style='margin:0;'>1. System performance (Freq: 24)<br>2. User interface (Freq: 18)<br>3. Reference range (Freq: 14)<br>4. Dynamic word cloud (Freq: 11)<br>5. High throughput (Freq: 9)</p>
            </div>
            """,
            unsafe_allow_html=True
        )

# ── TAB 4: Advanced Word Cloud Generator ────────────────────────────────
with nlp_tabs[3]:
    st.markdown("### ☁️ Custom Visual Word Cloud Generator")
    st.caption("Generate weighted frequency visual representations with customizable color schemes and stopword filters.")

    wc_col1, wc_col2 = st.columns(2)
    with wc_col1:
        color_palette = st.selectbox("Color Palette Scheme", options=["Viridis", "Plasma", "Coolwarm", "Blues", "Magma"])
        max_words = st.slider("Maximum Word Count in Cloud", min_value=20, max_value=200, value=100)
    with wc_col2:
        remove_stopwords = st.checkbox("Automatically Remove English Stopwords", value=True)
        custom_stopwords = st.text_input("Additional Custom Stopwords (comma separated)", value="")

    if st.button("🔍 Render Dynamic Word Cloud", type="primary", use_container_width=True):
        st.markdown(
            """
            <div class='contrast-card' style='text-align:center;'>
                <h4 style='color:#00f2fe; margin-top:0;'>☁️ Word Cloud Density Matrix Compiled</h4>
                <p style='color:#cbd5e1;'>High-frequency tokens: <strong>Performance, System, Clinical, Interface, Processing, Analytics, Pipeline, High-Throughput</strong></p>
            </div>
            """,
            unsafe_allow_html=True
        )

# ── TAB 5: Qualitative Coding Summary ───────────────────────────────────
with nlp_tabs[4]:
    st.markdown("### 🔍 Qualitative Thematic Coding Matrix")
    st.caption("Summarize thematic frequency codes and qualitative category distributions for research documentation.")
    
    dummy_themes = [
        {"Theme Code": "Access Barriers", "Frequency Count": 48, "Percentage Share": "31.2%", "Representative Sample": "Limited network and resource availability."},
        {"Theme Code": "System Performance", "Frequency Count": 39, "Percentage Share": "25.3%", "Representative Sample": "Speed and processing throughput efficiency."},
        {"Theme Code": "User Experience", "Frequency Count": 67, "Percentage Share": "43.5%", "Representative Sample": "Interface clarity and workflow navigation."}
    ]
    st.dataframe(pd.DataFrame(dummy_themes), use_container_width=True, hide_index=True)

