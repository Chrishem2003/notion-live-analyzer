
"""
═══════════════════════════════════════════════════════════════════════════════
ADVANCED AI INSIGHTS & EXECUTIVE REPORT GENERATOR [ENTERPRISE MODULE v6.3]
Standalone Edition featuring Nordic Cyber-Emerald styling, defensive error
handling, dynamic AI finding cards, and native HTML report generation.
Designed for: Kula Chris (Chrishem)
═══════════════════════════════════════════════════════════════════════════════
"""

import base64
import io
import numpy as np
import pandas as pd
import streamlit as st

# ─── 1. PAGE CONFIGURATION & STYLING ────────────────────────────────────
st.set_page_config(
    page_title="AI Insights & Executive Reporting",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# High-Contrast Cyber-Emerald Dark CSS Engine
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
    .stApp {
        background-color: #060b13 !important;
        color: #ffffff !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #00f2fe !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }
    
    p, span, label, div, .stMarkdown, .stCaption {
        color: #f8fafc !important;
        font-size: 0.95rem;
    }
    
    /* Contrast Containers */
    .contrast-card {
        background: #111c2e !important;
        border: 1px solid #00f2fe44 !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
    .insight-card {
        background: #091a2e !important;
        border-left: 4px solid #00f2fe !important;
        border-top: 1px solid #1e293b !important;
        border-right: 1px solid #1e293b !important;
        border-bottom: 1px solid #1e293b !important;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.85rem;
    }
    
    /* Metrics Highlighting */
    div[data-testid="stMetricValue"] {
        color: #00f2fe !important;
        font-size: 1.8rem !important;
        font-weight: 900 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        font-size: 0.75rem;
    }
    
    /* High-contrast Badges */
    .badge-primary {
        background: #172554;
        color: #93c5fd;
        border: 1px solid #1d4ed8;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-size: 0.7rem;
        font-family: monospace;
        letter-spacing: 0.05em;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── 2. REPORT GENERATION ENGINE ─────────────────────────────────────────
def auto_generate_report(df: pd.DataFrame, source_name: str = "dataset.csv") -> str:
    """Generates an executive HTML report from the active dataset with full defensive error handling."""
    try:
        n_rows, n_cols = df.shape
        missing_count = int(df.isnull().sum().sum())
        memory_usage = round(df.memory_usage(deep=True).sum() / (1024 ** 2), 2)
        
        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        summary_stats = (
            df[numeric_cols].describe().to_html(classes="dataframe table table-striped", border=0)
            if numeric_cols else "<p>No numeric columns available for statistical summary.</p>"
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Executive Data Intelligence Report</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #060b13; color: #f8fafc; padding: 40px; }}
                .container {{ max-width: 1000px; margin: auto; background: #111c2e; border: 1px solid #00f2fe44; border-radius: 12px; padding: 30px; box-shadow: 0 8px 32px rgba(0,0,0,0.5); }}
                h1, h2 {{ color: #00f2fe; border-bottom: 1px solid #1e293b; padding-bottom: 10px; }}
                .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
                .metric-card {{ background: #09101d; border: 1px solid #1e293b; padding: 15px; border-radius: 8px; text-align: center; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #00f2fe; }}
                .metric-label {{ font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-top: 5px; font-weight: 700; }}
                table.dataframe {{ width: 100%; border-collapse: collapse; margin-top: 15px; background: #060b13; color: #f8fafc; border-radius: 6px; overflow: hidden; }}
                table.dataframe th, table.dataframe td {{ padding: 10px; border: 1px solid #1e293b; text-align: left; font-size: 13px; }}
                table.dataframe th {{ background-color: #1a2638; color: #00f2fe; text-transform: uppercase; font-size: 11px; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #1e293b; padding-top: 15px; font-family: monospace; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔍 Executive Data Intelligence Report</h1>
                <p><strong>Source Document:</strong> {source_name}</p>
                
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{n_rows:,}</div>
                        <div class="metric-label">Total Records</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{n_cols:,}</div>
                        <div class="metric-label">Total Features</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{missing_count:,}</div>
                        <div class="metric-label">Missing Cells</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{memory_usage} MB</div>
                        <div class="metric-label">Memory Footprint</div>
                    </div>
                </div>

                <h2>🔍 Statistical Profile Matrix</h2>
                {summary_stats}

                <div class="footer">
                    <p>Generated via CHRISHEM Enterprise Intelligence Engine &bull; Confidential Data Processing</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html_content.strip()
    except Exception as e:
        return f"<html><body><h3>Error generating report:</h3><p>{e}</p></body></html>"


# ─── 3. MAIN PAGE RENDERER ───────────────────────────────────────────────
def render_ai_insights_page():
    """Renders the AI Insights page with full defensive error handling and intelligent diagnostics."""
    
    # ── HERO HEADER ──
    st.markdown(
        """
        <div style='display:flex; justify-content:space-between; align-items:center; background: linear-gradient(135deg, #0b1e36 0%, #061527 100%); border: 2px solid #00f2fe; padding: 1.5rem; border-radius: 14px; margin-bottom: 1.5rem;'>
            <div>
                <span class='badge-primary'>AUTOMATED DIAGNOSTICS & REPORTING</span>
                <h1 style='font-size: 2.2rem; margin: 0.4rem 0 0.2rem 0; color: #00f2fe;'>🔍 AI Intelligence Engine</h1>
                <p style='color: #cbd5e1; margin: 0; font-size: 0.95rem;'>
                    Deep dataset auditing, anomaly detection, automated correlation mapping, and executive HTML report compilation.
                </p>
            </div>
            <div style='text-align: right;'>
                <div style='background: #111c2e; border: 1px solid #10b981; padding: 0.6rem 1.1rem; border-radius: 10px;'>
                    <div style='font-size: 0.65rem; color: #94a3b8; text-transform: uppercase; font-weight: 800;'>Engine Brand</div>
                    <div style='color: #10b981; font-size: 1rem; font-weight: 900;'>🔍 CHRISHEM INSIGHTS</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Dataset Retrieval Logic with Fallback Generator
    df = st.session_state.get("working_df") or st.session_state.get("uploaded_df") or st.session_state.get("active_df")
    source_name = st.session_state.get("source_name", "active_dataset.csv")

    if df is None or df.empty:
        st.markdown(
            """
            <div class='contrast-card'>
                <h3 style='margin-top:0;'>⚠️ No Active Dataset Loaded</h3>
                <p style='color:#cbd5e1;'>Generate a sample clinical/research cohort below to test the AI Intelligence Engine.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("🔍 Load Synthetic Research Dataset", type="primary", use_container_width=True):
            np.random.seed(42)
            demo_data = pd.DataFrame({
                "Patient_ID": [f"PID-{1000 + i}" for i in range(120)],
                "Age": np.random.randint(20, 75, size=120),
                "BMI": np.round(np.random.normal(26.5, 4.5, size=120), 1),
                "Systolic_BP": np.random.randint(110, 160, size=120),
                "Diastolic_BP": np.random.randint(70, 100, size=120),
                "Glucose_Level": np.round(np.random.normal(105.0, 25.0, size=120), 1),
                "Treatment_Group": np.random.choice(["Placebo", "Low Dose", "High Dose"], size=120)
            })
            # Inject artificial missingness & correlation
            demo_data.loc[5:12, "BMI"] = np.nan
            demo_data["Pulse_Pressure"] = demo_data["Systolic_BP"] - demo_data["Diastolic_BP"]
            
            st.session_state["active_df"] = demo_data
            st.rerun()
        return

    # ── 1. Comprehensive Automated Insight Generation ──
    insights = []
    numeric_df = df.select_dtypes(include=np.number)
    
    rows, cols = df.shape
    total_cells = rows * cols if rows and cols else 1
    missing_count = int(df.isnull().sum().sum())
    missing_pct = (missing_count / total_cells) * 100

    insights.append(f"🔍 <b>Structural Scope</b>: Dataset contains <b>{rows:,} rows</b> and <b>{cols} columns</b>, forming a total matrix of <b>{total_cells:,} observations</b>.")

    if missing_count > 0:
        worst_col = df.isnull().sum().idxmax()
        worst_count = df.isnull().sum()[worst_col]
        worst_pct = (worst_count / rows) * 100
        insights.append(f"⚠️ <b>Data Sparsity Alert</b>: Global missing values equal <b>{missing_count:,} ({missing_pct:.2f}%)</b>. Feature <b>'{worst_col}'</b> has the highest missing rate at <b>{worst_pct:.1f}%</b>.")
    else:
        insights.append("✅ <b>Pristine Data Completeness</b>: Zero missing values detected across all variables.")

    # Collinearity Diagnostics
    if not numeric_df.empty and numeric_df.shape[1] >= 2:
        corr_matrix = numeric_df.corr().abs()
        upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        
        high_corrs = []
        for col in upper_tri.columns:
            for row in upper_tri.index:
                val = upper_tri.loc[row, col]
                if pd.notnull(val) and val > 0.80:
                    high_corrs.append((row, col, val))
                    
        if high_corrs:
            c1, c2, val = high_corrs[0]
            insights.append(f"🔍 <b>High Collinearity Detected</b>: Strong linear correlation (r = <b>{val:.2f}</b>) observed between <b>'{c1}'</b> and <b>'{c2}'</b>.")

    # Variance and Skewness Check
    if not numeric_df.empty:
        skew_series = numeric_df.skew()
        highly_skewed = skew_series[abs(skew_series) > 1.5].index.tolist()
        if highly_skewed:
            insights.append(f"🔍 <b>Distribution Skewness</b>: Features <b>{', '.join(highly_skewed[:3])}</b> exhibit significant skewness (|skew| > 1.5), indicating standard normalization or log scaling may be required.")

    # Display Analytical Finding Cards
    st.markdown("### 🔍 Key Analytical Findings")
    for idx, insight in enumerate(insights, 1):
        st.markdown(
            f"""
            <div class='insight-card'>
                <span style='color:#00f2fe; font-weight:800; font-size:0.8rem; text-transform:uppercase;'>Finding #{idx}</span>
                <div style='margin-top:0.2rem;'>{insight}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)

    # ── 2. Executive HTML Report Generator ──
    st.markdown("### 🔍 Executive HTML Report Generator")
    st.caption("Compile dataset metrics, structural profiles, and descriptive statistics into a standalone professional HTML document.")

    col_rep1, col_rep2 = st.columns([2, 1])
    
    with col_rep1:
        st.markdown(
            """
            <div class='contrast-card'>
                <h4 style='margin-top:0; color:#00f2fe;'>Standalone HTML Audit Report</h4>
                <p style='font-size:0.88rem; color:#cbd5e1;'>Generates an offline-ready HTML report containing complete summary statistics, row/column diagnostics, and memory footprint metrics.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col_rep2:
        html_report = auto_generate_report(df, source_name)
        st.download_button(
            label="⚡ Compile & Download HTML Report",
            data=html_report,
            file_name=f"Executive_Report_{source_name}.html",
            mime="text/html",
            type="primary",
            use_container_width=True
        )

# Execute main page renderer when executed directly
if __name__ == "__main__":
    render_ai_insights_page()

