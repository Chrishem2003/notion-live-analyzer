"""
CHRISHEM Shared UI Components — reusable hero cards, section headers, metric cards, and footers.
Used across all 11 consolidated hub pages.
"""

import streamlit as st

from modules.theme import get_theme


def hero_card(title: str, subtitle: str, badge_text: str = "", watermark: str = "CHRISHEM"):
    """
    Render the standard hero card banner used across all hub pages.
    """
    t = get_theme()
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; 
             background: linear-gradient(135deg, {t['gradient_start']} 0%, {t['gradient_end']} 100%); 
             border: 2px solid {t['accent']}; padding: 1.5rem; border-radius: 14px; 
             margin-bottom: 1.5rem; box-shadow: 0 8px 32px rgba(0,0,0,0.4);">
            <div>
                <span class='badge-primary'>{badge_text}</span>
                <h1 style='font-size: 2.2rem; margin: 0.4rem 0 0.2rem 0; color: {t['accent']} !important;'>{title}</h1>
                <p style='color: {t['text_secondary']}; margin: 0; font-size: 0.95rem; line-height:1.5;'>{subtitle}</p>
            </div>
            <div style="text-align: right;">
                <div style='background: #111c2e; border: 1px solid #34c787; padding: 0.6rem 1.1rem; border-radius: 10px;'>
                    <div style='font-size: 0.65rem; color: #6B7280; text-transform: uppercase; font-weight: 800;'>Engine</div>
                    <div style='color: #34c787; font-size: 0.95rem; font-weight: 900;'>{watermark}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, desc: str = ""):
    """
    Render a consistent section header with optional caption.
    """
    st.markdown(
        f"<h3 style='color:#e8a33d !important; margin-top:1.4rem; margin-bottom:0.3rem; font-weight:800;'>{title}</h3>",
        unsafe_allow_html=True,
    )
    if desc:
        st.caption(desc)


def metric_card(value: str, label: str, color: str = "#e8a33d"):
    """Render a styled metric card."""
    st.markdown(
        f"""
        <div style='background:#171B23; border:1px solid #262B33; border-radius:12px; padding:1rem; text-align:center; box-shadow:0 6px 20px rgba(0,0,0,0.3);'>
            <div style='font-size:1.35rem; font-weight:800; color:{color} !important;'>{value}</div>
            <div style='font-size:0.72rem; color:#6B7280; text-transform:uppercase; font-weight:700; letter-spacing:0.05em; margin-top:0.3rem;'>{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_card(title: str, body: str, accent: str = "#e8a33d"):
    """Render a contextual info card."""
    st.markdown(
        f"""
        <div style='background:#171B23; border:1px solid {accent}88; border-radius:12px; padding:1rem 1.25rem; margin-bottom:1rem;'>
            <div style='font-weight:800; color:{accent}; margin-bottom:0.25rem;'>{title}</div>
            <div style='color:#A8B0BC; font-size:0.9rem;'>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer(module_name: str, version: str = "1.0"):
    """Render the standard page footer."""
    st.markdown('<div class="chris-hr"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style='display: flex; justify-content: space-between; align-items: center; color: #64748b; font-size: 0.8rem; font-family: monospace; margin-top:2rem;'>
            <div>{module_name}</div>
            <div>DEVELOPER: KULA CHRIS (CHRISHEM)</div>
            <div>UNIFIED PLATFORM v{version}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def tab_badge(label: str, active: bool = True):
    """Return an HTML badge for tab labels."""
    color = "#e8a33d" if active else "#6B7280"
    return f"<span style='color:{color}; font-weight:800;'>{label}</span>"


def render_dataset_context_banner():
    """
    Show the active dataset context banner (rows/cols/source) used at top of analytical hubs.
    """
    from modules.session_manager import get_active_dataframe, dataset_summary

    summary = dataset_summary()
    if summary:
        st.info(
            f"📊 **Active Dataset:** `{summary['source']}` — {summary['rows']:,} rows × {summary['cols']} cols "
            f"| {summary['numeric']} numeric | {summary['categorical']} categorical | {summary['missing']:,} missing"
        )
    else:
        st.warning("⚠️ **No active dataset loaded.** Load data in the **Data Studio** hub or generate sample data.")
        col_a, col_b = st.columns([1, 3])
        with col_a:
            if st.button("🎲 Load Sample Data", type="primary", use_container_width=True):
                from modules.session_manager import generate_sample_dataset, set_active_dataframe

                set_active_dataframe(generate_sample_dataset(), "sample_research_cohort.csv")
                st.rerun()


def render_export_buttons(df, base_name: str = "export"):
    """
    Render standard export/download buttons for a dataframe.
    """
    if df is None or df.empty:
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download CSV",
            data=csv_data,
            file_name=f"{base_name}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        try:
            excel_buffer = __import__("io").BytesIO()
            df.to_excel(excel_buffer, index=False)
            st.download_button(
                "📥 Download Excel",
                data=excel_buffer.getvalue(),
                file_name=f"{base_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception:
            st.info("openpyxl required for Excel export")
    with col3:
        st.download_button(
            "📥 Download JSON",
            data=df.to_json(orient="records").encode("utf-8"),
            file_name=f"{base_name}.json",
            mime="application/json",
            use_container_width=True,
        )


def empty_state(icon: str, title: str, message: str, action_label: str = None, action_key: str = None):
    """
    Render a polished empty-state card with optional action button.
    Returns True if the action button was clicked.
    """
    st.markdown(
        f"""
        <div class="chris-card" style="text-align:center; padding:2rem;">
            <div style="font-size:2.5rem;">{icon}</div>
            <div style="font-size:1.1rem; font-weight:800; color:#e8a33d; margin:0.6rem 0 0.2rem 0;">{title}</div>
            <div style="color:#6B7280; font-size:0.9rem;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if action_label:
        return st.button(action_label, type="primary", use_container_width=True, key=action_key)
    return False

