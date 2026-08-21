
"""
Export Module  handles exporting charts and data to various formats.
PNG, SVG, PDF for charts. CSV, Excel, JSON, Parquet for data.
"""
from typing import Optional, Any, Dict, List
import io
import base64
import pandas as pd
import streamlit as st
from datetime import datetime

# Plotly for chart exports
try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def export_chart_as_png(fig) -> Optional[bytes]:
    """Export a Plotly figure as PNG bytes."""
    if not HAS_PLOTLY or fig is None:
        return None
    try:
        img_bytes = fig.to_image(format="png", width=1200, height=800, scale=2)
        return img_bytes
    except Exception as e:
        st.warning(f"PNG export failed: {e}}. Install kaleido: pip install -U kaleido")
        return None

def export_chart_as_svg(fig) -> Optional[bytes]:
    """Export a Plotly figure as SVG bytes."""
    if not HAS_PLOTLY or fig is None:
        return None
    try:
        img_bytes = fig.to_image(format="svg", width=1200, height=800)
        return img_bytes
    except Exception as e:
        st.warning(f"SVG export failed: {e}}")
        return None

def get_chart_download_link(fig, filename: str = "chart", format: str = "png") -> Optional[str]:
    """Generate a download link for a chart."""
    if format == "png":
        data = export_chart_as_png(fig)
        mime = "image/png"
    elif format == "svg":
        data = export_chart_as_svg(fig)
        mime = "image/svgxml"
    else:
        return None

    if data is None:
        return None

    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:{mime}};base64,{b64}}" download="{filename}}.{format}}">ðŸ“¥ Download {format.upper()}}</a>'
    return href


def export_data_as_csv(df: pd.DataFrame) -> bytes:
    """Export DataFrame as CSV bytes."""
    return df.to_csv(index=False).encode("utf-8")

def export_data_as_excel(df: pd.DataFrame) -> bytes:
    """Export DataFrame as Excel bytes."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    output.seek(0)
    return output.getvalue()

def export_data_as_json(df: pd.DataFrame) -> bytes:
    """Export DataFrame as JSON bytes."""
    return df.to_json(orient="records", indent=2).encode("utf-8")

def export_data_as_parquet(df: pd.DataFrame) -> bytes:
    """Export DataFrame as Parquet bytes."""
    output = io.BytesIO()
    df.to_parquet(output, index=False)
    output.seek(0)
    return output.getvalue()

def get_data_download_link(df: pd.DataFrame, filename: str = "data", format: str = "csv") -> str:
    """Generate a download link for data export."""
    if df is None or df.empty:
        return ""

    mime_map = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
        "parquet": "application/octet-stream",
    }

    export_funcs = {
        "csv": export_data_as_csv,
        "xlsx": export_data_as_excel,
        "json": export_data_as_json,
        "parquet": export_data_as_parquet,
    }

    func = export_funcs.get(format)
    mime = mime_map.get(format, "text/csv")
    if func is None:
        return ""

    data = func(df)
    b64 = base64.b64encode(data).decode()
    ext = format
    href = f'<a href="data:{mime}};base64,{b64}}" download="{filename}}.{ext}}">ðŸ“¥ Download {format.upper()}}</a>'
    return href


def render_export_buttons(df: pd.DataFrame, fig=None, key_prefix: str = "export"):
    """Render standardized export buttons for data and charts."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        csv_link = get_data_download_link(df, f"data_{datetime.now():%Y%m%d_%H%M%S}}", "csv")
        if csv_link:
            st.markdown(csv_link, unsafe_allow_html=True)

    with col2:
        xlsx_link = get_data_download_link(df, f"data_{datetime.now():%Y%m%d_%H%M%S}}", "xlsx")
        if xlsx_link:
            st.markdown(xlsx_link, unsafe_allow_html=True)

    with col3:
        json_link = get_data_download_link(df, f"data_{datetime.now():%Y%m%d_%H%M%S}}", "json")
        if json_link:
            st.markdown(json_link, unsafe_allow_html=True)

    with col4:
        if fig is not None:
            png_link = get_chart_download_link(fig, f"chart_{datetime.now():%Y%m%d_%H%M%S}}", "png")
            if png_link:
                st.markdown(png_link, unsafe_allow_html=True)


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Report Generation (Simplified) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
def generate_markdown_report(
    title: str,
    sections: Dict[str, str],
    df_summary: pd.DataFrame = None,
) -> str:
    """Generate a markdown report from sections."""
    lines = [f"# {title}}", f"**Generated**: {datetime.now():%Y-%m-%d %H:%M:%S}}", ""]

    if df_summary is not None and not df_summary.empty:
        lines.append("## Dataset Summary")
        lines.append(f"- **Rows**: {len(df_summary)}}")
        lines.append(f"- **Columns**: {len(df_summary.columns)}}")
        lines.append(f"- **Columns**: {', '.join(df_summary.columns[:20])}}")
        lines.append("")

    for section_title, content in sections.items():
        lines.append(f"## {section_title}}")
        lines.append(str(content))
        lines.append("")

    return "\n".join(lines)


