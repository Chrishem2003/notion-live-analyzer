import base64
import io
import pandas as pd
import streamlit as st

def auto_generate_report(df: pd.DataFrame, source_name: str = "dataset.csv") -> str:
    """Generates an executive HTML report from the active dataset with full defensive error handling."""
    try:
        n_rows, n_cols = df.shape
        missing_count = int(df.isnull().sum().sum())
        memory_usage = round(df.memory_usage(deep=True).sum() / (1024 ** 2), 2)
        
        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        summary_stats = df[numeric_cols].describe().to_html(classes="dataframe table table-striped", border=0) if numeric_cols else "<p>No numeric columns available for statistical summary.</p>"

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
                .footer {{ margin-top: 30px; font-size: 12px; color: #8b949e; text-align: center; border-top: 1px solid #30363d; pt: 15px; }}
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
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display:inline-block;background:#238636;color:white;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:bold;margin-top:10px;">📥 Download Full Executive Report (.HTML)</a>'
    return href