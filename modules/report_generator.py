"""
Report Generator — creates automated narrative reports combining data, charts, and statistical findings.
"""
from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

import io
import base64
import streamlit as st


class ResearchReport:
    """Generate professional research reports with findings, charts, and statistics."""

    def __init__(self, title: str = "Research Analysis Report"):
        self.title = title
        self.sections = []

    def add_section(self, heading: str, content: str):
        """Add a text section to the report."""
        self.sections.append({
            "type": "text",
            "heading": heading,
            "content": content,
        })

    def add_table(self, heading: str, df: pd.DataFrame):
        """Add a data table section."""
        self.sections.append({
            "type": "table",
            "heading": heading,
            "dataframe": df,
        })

    def add_chart_description(self, heading: str, description: str, chart_type: str = None):
        """Add a chart description (actual chart embedding via HTML export)."""
        self.sections.append({
            "type": "chart",
            "heading": heading,
            "content": description,
            "chart_type": chart_type,
        })

    def add_statistical_finding(self, heading: str, test_name: str, result: Dict[str, Any]):
        """Add a statistical test result."""
        content_lines = [f"**Test**: {test_name}"]
        if isinstance(result, dict):
            for k, v in result.items():
                if k != "error" and not isinstance(v, pd.DataFrame):
                    content_lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")
            content_lines.append("---")
        self.sections.append({
            "type": "statistical",
            "heading": heading,
            "content": "\n".join(content_lines),
            "result": result,
        })

    def generate_markdown(self) -> str:
        """Generate the complete report in Markdown format."""
        lines = [
            f"# {self.title}",
            f"**Generated**: {datetime.now():%Y-%m-%d %H:%M:%S}",
            "",
            "---",
            "",
        ]
        for section in self.sections:
            lines.append(f"## {section['heading']}")
            lines.append("")
            if section["type"] == "text":
                lines.append(section["content"])
            elif section["type"] == "table":
                df = section.get("dataframe")
                if df is not None and not df.empty:
                    lines.append(df.to_markdown(index=False))
            elif section["type"] == "chart":
                lines.append(section.get("content", ""))
            elif section["type"] == "statistical":
                lines.append(section.get("content", ""))
            lines.append("")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)

    def generate_html(self) -> str:
        """Generate a basic HTML report."""
        html_parts = [f"<html><head><title>{self.title}</title></head><body>"]
        html_parts.append(f"<h1>{self.title}</h1>")
        html_parts.append(f"<p><em>Generated: {datetime.now():%Y-%m-%d %H:%M:%S}</em></p><hr>")
        for section in self.sections:
            html_parts.append(f"<h2>{section['heading']}</h2>")
            if section["type"] == "text":
                html_parts.append(f"<p>{section['content']}</p>")
            elif section["type"] == "table":
                df = section.get("dataframe")
                if df is not None and not df.empty:
                    html_parts.append(df.to_html(classes="table table-striped"))
            elif section["type"] == "chart":
                html_parts.append(f"<p>{section.get('content', '')}</p>")
            elif section["type"] == "statistical":
                html_parts.append(f"<pre>{section.get('content', '')}</pre>")
            html_parts.append("<hr>")
        html_parts.append("</body></html>")
        return "\n".join(html_parts)

    def generate_pdf(self) -> Optional[bytes]:
        """Generate a PDF report (requires fpdf2)."""
        if not HAS_FPDF:
            st.warning("PDF generation requires fpdf2. Install: pip install fpdf2")
            return None
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, self.title, ln=True, align="C")
            pdf.set_font("Arial", "I", 10)
            pdf.cell(0, 10, f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}", ln=True, align="C")
            pdf.ln(5)
            for section in self.sections:
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, section["heading"], ln=True)
                if section["type"] == "text":
                    pdf.set_font("Arial", "", 10)
                    pdf.multi_cell(0, 5, section["content"])
                elif section["type"] == "statistical":
                    pdf.set_font("Courier", "", 8)
                    pdf.multi_cell(0, 4, section.get("content", ""))
                pdf.ln(3)
            return pdf.output(dest="S").encode("latin-1")
        except Exception as e:
            st.warning(f"PDF generation error: {e}")
            return None


def auto_generate_report(
    df: pd.DataFrame,
    profile: Dict[str, Any],
    statistical_results: List[Dict[str, Any]] = None,
    insights: List[str] = None,
) -> ResearchReport:
    """Auto-generate a comprehensive research report from analysis results."""
    report = ResearchReport("Automated Research Analysis Report")

    # Dataset Overview
    overview = (
        f"This report analyzes a dataset with **{profile.get('rows', 0):,}** observations "
        f"and **{profile.get('columns', 0)}** variables. "
        f"The dataset contains {profile.get('missing_pct', 0)}% missing values and "
        f"{profile.get('duplicate_rows', 0)} duplicate rows."
    )
    report.add_section("Dataset Overview", overview)

    # Column Types
    type_summary = profile.get("type_distribution", {})
    if type_summary:
        type_lines = [f"- **{k}**: {v}" for k, v in type_summary.items()]
        report.add_section("Variable Types", "\n".join(type_lines))

    # Insights
    if insights:
        report.add_section("Key Insights", "\n".join([f"- {i}" for i in insights]))

    # Statistical Results
    if statistical_results:
        for i, result in enumerate(statistical_results):
            if isinstance(result, dict):
                test_name = result.get("test", f"Test {i+1}")
                report.add_statistical_finding(f"Statistical Analysis {i+1}", test_name, result)

    # Summary
    report.add_section("Conclusion", "Analysis complete. See individual sections for detailed findings.")

    return report


def get_report_download_link(report: ResearchReport, format: str = "md") -> str:
    """Generate download link for a report."""
    if format == "md":
        content = report.generate_markdown()
        mime = "text/markdown"
        ext = "md"
    elif format == "html":
        content = report.generate_html()
        mime = "text/html"
        ext = "html"
    elif format == "pdf":
        pdf_bytes = report.generate_pdf()
        if pdf_bytes:
            b64 = base64.b64encode(pdf_bytes).decode()
            return f'<a href="data:application/pdf;base64,{b64}" download="report_{datetime.now():%Y%m%d}.pdf">📥 Download PDF Report</a>'
        return ""
    else:
        return ""

    b64 = base64.b64encode(content.encode()).decode()
    return f'<a href="data:{mime};base64,{b64}" download="report_{datetime.now():%Y%m%d}.{ext}">📥 Download {format.upper()} Report</a>'

