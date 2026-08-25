
"""
Presentation Deck Builder  allows users to select generated charts and
compile them into an interactive presentation deck view with export options.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import streamlit as st
import base64
import io

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


class DeckBuilder:
    """
    Interactive presentation deck builder for research findings.
    Compiles selected charts, insights, and data tables into slide format.
    Supports export to HTML and PDF.
    """

    def __init__(self):
        self.slides = []
        self.current_slide_idx = 0

    def add_slide(self, title: str, content: str, chart_fig=None, slide_type: str = "content"):
        """Add a slide to the deck."""
        slide = {
            "id": len(self.slides) + 1,
            "type": slide_type,
            "title": title,
            "content": content,
            "chart": chart_fig,
            "chart_spec": None,  # Store chart params for rebuild
            "created_at": datetime.now().strftime("%H:%M:%S"),
        }
        self.slides.append(slide)
        return slide

    def add_chart_slide(self, title: str, chart_fig, annotation: str = ""):
        """Add a chart-focused slide."""
        return self.add_slide(title, annotation, chart_fig, "chart")

    def add_data_slide(self, title: str, df: pd.DataFrame, description: str = ""):
        """Add a data table slide."""
        return self.add_slide(title, description, df, "data")

    def add_section_slide(self, title: str, subtitle: str = ""):
        """Add a section divider slide."""
        return self.add_slide(title, subtitle, None, "section")

    def remove_slide(self, slide_id: int):
        """Remove a slide by ID."""
        self.slides = [s for s in self.slides if s["id"] != slide_id]

    def reorder_slides(self, new_order: List[int]):
        """Reorder slides by list of IDs."""
        slide_map = {s["id"]: s for s in self.slides}
        self.slides = [slide_map[sid] for sid in new_order if sid in slide_map]

    def clear_deck(self):
        """Clear all slides."""
        self.slides = []
        self.current_slide_idx = 0

    def generate_html_deck(self, title: str = "Research Presentation") -> str:
        """Generate a standalone HTML presentation."""
        html_parts = [f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #262B33 !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #EDEFF2 !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #EDEFF2 !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #262B33 !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #b5790e !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #4fb8a6 !important;
        font-weight: 700 !important;
    }
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Inter', -apple-system, sans-serif; background: #EDEFF2; color: #0B0E11; }}
    .slide {{ min-height: 100vh; padding: 3rem 4rem; display: flex; flex-direction: column; justify-content: center; border-bottom: 1px solid #e2e8f0; }}
    .slide-section {{ background: linear-gradient(135deg, #1e3a5f, #1d4ed8); color: white; text-align: center; }}
    .slide-section h1 {{ font-size: 3rem; margin-bottom: 1rem; }}
    .slide-section p {{ font-size: 1.3rem; opacity: 0.9; }}
    .slide-title {{ font-size: 2rem; font-weight: 700; margin-bottom: 1rem; color: #1d4ed8; }}
    .slide-content {{ font-size: 1.1rem; line-height: 1.7; color: #3A4048; }}
    .slide-data {{ overflow-x: auto; }}
    .slide-data table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    .slide-data th {{ background: #1d4ed8; color: white; padding: 0.6rem; text-align: left; }}
    .slide-data td {{ padding: 0.5rem; border-bottom: 1px solid #e2e8f0; }}
    .chart-container {{ width: 100%; height: 60vh; }}
    .footer {{ margin-top: auto; font-size: 0.8rem; color: #6B7280; text-align: center; padding: 1rem; }}
    @media print {{ .slide {{ page-break-after: always; min-height: 100vh; }} }}
</style>
</head>
<body>
"""]

        for slide in self.slides:
            stype = slide.get("type", "content")
            if stype == "section":
                html_parts.append(f"""
<div class="slide slide-section">
    <h1>{slide['title']}</h1>
    <p>{slide['content']}</p>
    <div class="footer">CHRISHEM Research Suite</div>
</div>
""")
            elif stype == "chart":
                html_parts.append(f"""
<div class="slide">
    <div class="slide-title">{slide['title']}</div>
    <div class="slide-content">{slide['content']}</div>
    <div class="chart-container">
        <img src="data:image/png;base64,{{chart_placeholder}}" style="width:100%;height:100%;object-fit:contain;" />
    </div>
    <div class="footer">CHRISHEM Research Suite</div>
</div>
""")
            elif stype == "data":
                df = slide.get("chart")  # Reusing chart slot for DataFrame
                if isinstance(df, pd.DataFrame) and not df.empty:
                    table_html = df.to_html(classes="data-table", index=False, max_cols=10, max_rows=20)
                    html_parts.append(f"""
<div class="slide">
    <div class="slide-title">{slide['title']}</div>
    <div class="slide-content">{slide['content']}</div>
    <div class="slide-data">{table_html}</div>
    <div class="footer">CHRISHEM Research Suite</div>
</div>
""")
            else:
                html_parts.append(f"""
<div class="slide">
    <div class="slide-title">{slide['title']}</div>
    <div class="slide-content">{slide['content']}</div>
    <div class="footer">CHRISHEM Research Suite</div>
</div>
""")

        html_parts.append("</body></html>")
        return "\n".join(html_parts)

    def export_html(self, title: str = "Research Presentation") -> str:
        """Get HTML export string."""
        return self.generate_html_deck(title)

    def export_pdf(self, title: str = "Research Presentation") -> Optional[bytes]:
        """Export as PDF using fpdf2 (basic text/chart descriptions)."""
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 20)
            pdf.cell(0, 15, title, ln=True, align="C")
            pdf.ln(5)

            for slide in self.slides:
                pdf.add_page()
                stype = slide.get("type", "content")

                if stype == "section":
                    pdf.set_font("Arial", "B", 18)
                    pdf.cell(0, 10, slide["title"], ln=True, align="C")
                    pdf.set_font("Arial", "", 12)
                    pdf.multi_cell(0, 8, slide["content"])
                else:
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(0, 10, slide["title"], ln=True)
                    pdf.set_font("Arial", "", 11)
                    pdf.multi_cell(0, 6, slide.get("content", ""))

                    if stype == "data":
                        df = slide.get("chart")
                        if isinstance(df, pd.DataFrame):
                            pdf.ln(3)
                            # Simple table
                            cols = df.columns.tolist()[:6]
                            pdf.set_font("Courier", "", 7)
                            for _, row in df.head(15).iterrows():
                                row_text = " | ".join([str(row.get(c, ""))[:15] for c in cols])
                                pdf.cell(0, 4, row_text, ln=True)

            return pdf.output(dest="S").encode("latin-1")
        except Exception as e:
            st.warning(f"PDF export failed: {e}")
            return None

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of the current deck."""
        type_counts = {}
        for s in self.slides:
            stype = s.get("type", "content")
            type_counts[stype] = type_counts.get(stype, 0) + 1

        return {
            "total_slides": len(self.slides),
            "type_counts": type_counts,
            "title": st.session_state.get("deck_title", "Untitled"),
        }


# ─── UI ──────────────────────────────────────────────────────────────

def render_deck_builder_ui():
    """Render the presentation deck builder UI."""
    st.markdown("##  Presentation Deck Builder")
    st.markdown("*Compile charts, insights, and data into an interactive presentation*")

    # Initialize deck builder
    if "deck_builder" not in st.session_state:
        st.session_state["deck_builder"] = DeckBuilder()
    deck = st.session_state["deck_builder"]

    # ─── Deck Title ────────────────────────────────────────────────
    col1, col2 = st.columns([3, 1])
    with col1:
        deck_title = st.text_input("Presentation Title", value=st.session_state.get("deck_title", "Untitled Presentation"))
        st.session_state["deck_title"] = deck_title
    with col2:
        if st.button("🗑️ Clear Deck", type="secondary", use_container_width=True):
            deck.clear_deck()
            st.session_state["deck_slides"] = []
            st.rerun()

    # ─── Add Content ──────────────────────────────────────────────
    st.markdown("### ➕ Add Slides")
    add_method = st.radio("Add from:", ["Current Data/Charts", "AI Insights", "Statistical Results", "Custom Content"], horizontal=True)

    if add_method == "Current Data/Charts":
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(" Add Data Table Slide", use_container_width=True):
                df = st.session_state.get("active_df")
                if df is not None and not df.empty:
                    deck.add_data_slide(
                        f"Data Overview  {df.shape[0]} rows × {df.shape[1]} cols",
                        df.head(50),
                        f"First {min(50, len(df))} rows of the dataset"
                    )
                    st.rerun()
        with col2:
            if st.button("📈 Add Chart Slides", use_container_width=True):
                charts_in_session = st.session_state.get("deck_charts", [])
                if charts_in_session:
                    for i, chart_info in enumerate(charts_in_session):
                        deck.add_chart_slide(
                            chart_info.get("title", f"Chart {i1}"),
                            chart_info.get("figure"),
                            chart_info.get("description", ""),
                        )
                    st.rerun()
                else:
                    st.warning("No charts selected. Run visualizations and use 'Add to Deck' buttons.")
        with col3:
            if st.button("📋 Add Dataset Profile", use_container_width=True):
                df = st.session_state.get("active_df")
                if df is not None:
                    from modules.data_processor import profile_dataset
                    profile = profile_dataset(df)
                    profile_text = (
                        f"**Dataset Profile**\n\n"
                        f"- **Rows**: {profile['rows']:,}\n"
                        f"- **Columns**: {profile['columns']}\n"
                        f"- **Numeric**: {len(profile.get('numeric_columns', []))}\n"
                        f"- **Categorical**: {len(profile.get('categorical_columns', []))}\n"
                        f"- **Missing**: {profile['missing_pct']}%\n"
                        f"- **Duplicates**: {profile['duplicate_rows']:,}"
                    )
                    deck.add_slide("Dataset Profile", profile_text)
                    st.rerun()

    elif add_method == "AI Insights":
        insights = st.session_state.get("generated_hypotheses", [])
        if insights:
            for h in insights[:5]:
                if st.button(f"➕ Add: {h.get('id', 'Hypothesis')}  {h.get('narrative', '')[:60]}...", key=f"add_hyp_{h.get('id', '')}"):
                    deck.add_slide(
                        f"Finding {h.get('id', '')}: {h.get('type', '').replace('_', ' ').title()}",
                        h.get('narrative', ''),
                        slide_type="content"
                    )
                    st.rerun()
        else:
            st.info("No AI insights generated yet. Run Hypothesis Discovery first.")

    elif add_method == "Statistical Results":
        results = st.session_state.get("statistical_results", [])
        if results:
            for r in results[-5:]:
                test_name = r.get("test", r.get("test_name", "Statistical Test"))
                p = r.get("p_value", 1)
                sig_text = "✅ Significant" if r.get("significant") else "❌ Not significant"
                if st.button(f"➕ Add: {test_name} ({sig_text}, p={p:.4f})", key=f"add_stat_{test_name}"):
                    content_lines = [f"**Test**: {test_name}"]
                    for k, v in r.items():
                        if k not in ("error", "test") and not isinstance(v, pd.DataFrame):
                            content_lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")
                    deck.add_slide(f"Statistical Result: {test_name}", "\n".join(content_lines))
                    st.rerun()
        else:
            st.info("No statistical results yet. Run analyses on the Statistical Tests page.")

    elif add_method == "Custom Content":
        with st.form("custom_slide_form"):
            slide_title = st.text_input("Slide title", placeholder="Enter slide title")
            slide_content = st.text_area("Content (Markdown supported)", placeholder="Enter slide content...", height=150)
            slide_type = st.selectbox("Slide type", options=["content", "section"])
            submitted = st.form_submit_button("➕ Add Custom Slide", use_container_width=True)
            if submitted and slide_title:
                deck.add_slide(slide_title, slide_content, slide_type=slide_type)
                st.rerun()

    # ─── Deck Preview ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"## 🎬 Deck Preview ({len(deck.slides)} slides)")

    if not deck.slides:
        st.info("👆 Add slides from the options above to build your presentation.")
        return

    # Slide navigation
    col_prev, col_counter, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("⬅️ Previous", use_container_width=True, disabled=deck.current_slide_idx <= 0):
            deck.current_slide_idx = max(0, deck.current_slide_idx - 1)
            st.rerun()
    with col_counter:
        total = len(deck.slides)
        current = deck.current_slide_idx + 1
        slide_idx = st.select_slider(
            "Slide navigation",
            options=list(range(1, total + 1)),
            value=min(current, total),
            key="slide_nav",
            label_visibility="collapsed",
        )
        if slide_idx != current:
            deck.current_slide_idx = slide_idx - 1
            st.rerun()
    with col_next:
        if st.button("Next ➡️", use_container_width=True, disabled=deck.current_slide_idx >= len(deck.slides) - 1):
            deck.current_slide_idx = min(len(deck.slides) - 1, deck.current_slide_idx + 1)
            st.rerun()

    # Current slide display
    slide = deck.slides[deck.current_slide_idx]
    stype = slide.get("type", "content")

    if stype == "section":
        st.markdown(f"""
        <div style="text-align:center;padding:3rem;border-radius:18px;
                    background:linear-gradient(135deg, #1e3a5f, #1d4ed8);color:white;margin:1rem 0;">
            <h1 style="color:white;font-size:2.2rem;">{slide['title']}</h1>
            <p style="font-size:1.2rem;opacity:0.9;">{slide['content']}</p>
        </div>
        """, unsafe_allow_html=True)

    elif stype == "chart":
        st.subheader(slide["title"])
        if slide.get("content"):
            st.markdown(slide["content"])
        chart = slide.get("chart")
        if chart is not None:
            if isinstance(chart, go.Figure):
                st.plotly_chart(chart, use_container_width=True)
            else:
                st.write(chart)

    elif stype == "data":
        st.subheader(slide["title"])
        if slide.get("content"):
            st.caption(slide["content"])
        df = slide.get("chart")
        if isinstance(df, pd.DataFrame) and not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)

    else:
        st.subheader(slide["title"])
        st.markdown(slide["content"], unsafe_allow_html=True)

    # Slide controls
    col_edit1, col_edit2, col_edit3 = st.columns([1, 1, 1])
    with col_edit1:
        if st.button("⬆️ Move Up", use_container_width=True, disabled=deck.current_slide_idx == 0):
            idx = deck.current_slide_idx
            deck.slides[idx], deck.slides[idx - 1] = deck.slides[idx - 1], deck.slides[idx]
            deck.current_slide_idx = max(0, idx - 1)
            st.rerun()
    with col_edit2:
        if st.button("⬇️ Move Down", use_container_width=True, disabled=deck.current_slide_idx >= len(deck.slides) - 1):
            idx = deck.current_slide_idx
            deck.slides[idx], deck.slides[idx + 1] = deck.slides[idx + 1], deck.slides[idx]
            deck.current_slide_idx = min(len(deck.slides) - 1, idx + 1)
            st.rerun()
    with col_edit3:
        if st.button("🗑️ Remove Slide", use_container_width=True, type="secondary"):
            deck.remove_slide(slide["id"])
            deck.current_slide_idx = min(deck.current_slide_idx, len(deck.slides) - 1)
            st.rerun()

    # ─── Export ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 Export Presentation")

    col_exp1, col_exp2, col_exp3 = st.columns(3)
    with col_exp1:
        if st.button("🌐 Export as HTML", use_container_width=True):
            html = deck.export_html(st.session_state.get("deck_title", "Presentation"))
            b64 = base64.b64encode(html.encode()).decode()
            st.markdown(
                f'<a href="data:text/html;base64,{b64}" download="presentation_{datetime.now():%Y%m%d}.html">'
                f'📥 Click to Download HTML</a>',
                unsafe_allow_html=True,
            )
    with col_exp2:
        if st.button("📄 Export as PDF", use_container_width=True):
            pdf_bytes = deck.export_pdf(st.session_state.get("deck_title", "Presentation"))
            if pdf_bytes:
                b64 = base64.b64encode(pdf_bytes).decode()
                st.markdown(
                    f'<a href="data:application/pdf;base64,{b64}" download="presentation_{datetime.now():%Y%m%d}.pdf">'
                    f'📥 Click to Download PDF</a>',
                    unsafe_allow_html=True,
                )
    with col_exp3:
        if st.button("📋 Copy Deck Summary", use_container_width=True):
            summary = deck.get_summary()
            st.code(
                f"Presentation: {st.session_state.get('deck_title', 'Untitled')}\n"
                f"Total Slides: {summary['total_slides']}\n"
                f"Types: {summary['type_counts']}",
                language="text",
            )



