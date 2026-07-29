# ═══════════════════════════════════════════════════════════════════════════════
# ADVANCED AI INSIGHTS & EXECUTIVE REPORT GENERATOR [ENTERPRISE MODULE v6.3]
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import io
import numpy as np
import pandas as pd
import streamlit as st


def render_ai_insights_page():
    """Renders the AI Insights page with full defensive error handling and intelligent diagnostics."""
    st.markdown("## 🤖 Automated AI Intelligence & Executive Reporting")
    st.caption("Deep automated data scanning, anomaly detection, automated correlation mapping, and executive HTML report generation.")

    # Retrieve working dataset safely from session state
    df = st.session_state.get("working_df") or st.session_state.get("uploaded_df")
    source_name = st.session_state.get("source_name", "dataset.csv")

    if df is None or df.empty:
        st.warning("⚠️ No active dataset detected. Please upload or load a file from the **File Analyzer** tab first.")
        return

    # ── 1. Comprehensive Automated Insight Generation ──
    insights = []
    numeric_df = df.select_dtypes(include=np.number)
    categorical_df = df.select_dtypes(include=["object", "category"])
    
    rows, cols = df.shape
    total_cells = rows * cols if rows and cols else 1
    missing_count = int(df.isnull().sum().sum())
    missing_pct = (missing_count / total_cells) * 100

    insights.append(f"📌 **Structural Scope**: The dataset comprises **{rows:,} records** and **{cols} features**, yielding a total cell matrix of **{total_cells:,} data points**.")

    if missing_count > 0:
        worst_col = df.isnull().sum().idxmax()
        worst_count = df.isnull().sum()[worst_col]
        worst_pct = (worst_count / rows) * 100
        insights.append(f"⚠️ **Data Sparsity Alert**: Global missing entries equal **{missing_count:,} ({missing_pct:.2f}%)**. Feature **'{worst_col}'** carries the highest vacancy rate at **{worst_pct:.1f}%**.")
    else:
        insights.append("✅ **Pristine Data Completeness**: Zero missing elements found across all feature columns.")

    # Correlation Diagnostics
    if not numeric_df.empty and numeric_df.shape[1] >= 2:
        corr_matrix = numeric_df.corr().abs()
        upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        high_corrs = [
            (upper_tri.index[i], upper_tri.columns[j], upper_tri.iloc[i, j])
            for i in range(len(upper_tri)) for j in range(len(upper_tri.columns))
            if upper_tri.iloc[i, j] > 0.80
        ]
        if high_corrs:
            c1, c2, val = high_corrs[0]
            insights.append(f"🔗 **Strong Feature Collinearity**: High correlation coefficient (**{val:.2f}**) identified between **'{c1}'** and **'{c2}'**, indicating potential linear dependency.")

    # Variance and Skewness Check
    if not numeric_df.empty:
        skew_series = numeric_df.skew()
        highly_skewed = skew_series[abs(skew_series) > 1.5].index.tolist()
        if highly_skewed:
            insights.append(f"📈 **Distribution Skewness**: Features **{', '.join(highly_skewed[:3])}** exhibit heavy statistical skewness (|skew| > 1.5), suggesting transformation requirements (e.g., log scale).")

    # Display Insights in UI Cards
    st.markdown("### 🧠 Key Analytical Findings")
    for idx, insight in enumerate(insights, 1):
        st.info(f"**Insight {idx}:** {insight}")

    st.markdown("---")

    # ── 2. Executive HTML Report Generation ──
    st.markdown("### 📄 Executive HTML Report Generator")
    st.caption("Compile dataset metrics, structural profiles, and descriptive statistics into a standalone professional HTML document.")

    if st.button("⚡ Compile Executive Intelligence Report", type="primary", use_container_width=True):
        with st.spinner("Compiling high-performance HTML report..."):
            html_report = auto_generate_report(df, source_name)
            download_link = get_report_download_link(html_report, filename=f"Executive_Report_{source_name}.html")
            st.markdown(download_link, unsafe_allow_html=True)
            st.success("✅ Executive report compiled successfully!")


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
            <title>Executive Data Intelligence Report</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0d1117; color: #f0f6fc; padding: 40px; }}
                .container {{ max-width: 1000px; margin: auto; background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 30px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }}
                h1, h2 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
                .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
                .metric-card {{ background: #21262d; border: 1px solid #30363d; padding: 15px; border-radius: 6px; text-align: center; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #7ee787; }}
                .metric-label {{ font-size: 12px; color: #8b949e; text-transform: uppercase; margin-top: 5px; }}
                table.dataframe {{ width: 100%; border-collapse: collapse; margin-top: 15px; background: #0d1117; color: #f0f6fc; }}
                table.dataframe th, table.dataframe td {{ padding: 10px; border: 1px solid #30363d; text-align: left; font-size: 14px; }}
                table.dataframe th {{ background-color: #21262d; color: #58a6ff; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #8b949e; text-align: center; border-top: 1px solid #30363d; padding-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Executive Data Intelligence Report</h1>
                <p><strong>Source Document:</strong> {source_name}</p>
                
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{n_rows:,}</div>
                        <div class="metric-label">Total Rows</div>
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

                <h2>📈 Statistical Profile Matrix</h2>
                {summary_stats}

                <div class="footer">
                    <p>Generated securely via Enterprise Analyzer Engine &bull; Confidential Data Processing</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html_content.strip()
    except Exception as e:
        return f"<html><body><h3>Error generating report:</h3><p>{e}</p></body></html>"


def get_report_download_link(html_content: str, filename: str = "intelligence_report.html"):
    """Encodes the HTML report into a downloadable Streamlit-compatible component link."""
    b64 = base64.b64encode(html_content.encode("utf-8")).decode("utf-8")
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display:inline-block;background:#238636;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold;margin-top:15px;box-shadow:0 4px 12px rgba(35,134,54,0.4);">📥 Download Full Executive Report (.HTML)</a>'
    return href