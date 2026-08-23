"""
CHRISHEM Shared UI Components - reusable hero cards, section headers, metric
cards, and footers. Used across all 15 consolidated hub pages.

All colors are pulled live from theme.get_theme() so every component here
respects the dark/light toggle - previously hero_card/section_header/
metric_card read a different, unused session-state key and hardcoded
colors, so they silently ignored the theme toggle. Fixed.
"""

import streamlit as st

from modules.theme import get_theme


def hero_card(title, subtitle, badge_text=None):
    t = get_theme()
    badge_html = (
        f'<div style="background:{t["accent_alt"]}22; color:{t["accent_alt"]}; '
        f'padding:0.25rem 0.75rem; border-radius:4px; font-size:0.72rem; font-weight:700; '
        f'font-family:\'IBM Plex Mono\', monospace; letter-spacing:0.04em; display:inline-block; '
        f'margin-bottom:0.75rem; border:1px solid {t["accent_alt"]}55;">{badge_text}</div>'
        if badge_text else ''
    )

    st.markdown(
        f"""
        <div style="position:relative; background:linear-gradient(135deg, {t['gradient_start']} 0%, {t['gradient_end']} 100%);
             border:1px solid {t['border']}; border-radius:8px; padding:2rem; color:{t['text_primary']}; margin-bottom:1.5rem;">
            <div style="position:absolute; top:-1px; left:-1px; width:18px; height:18px;
                 border-color:{t['accent']}; border-style:solid; border-width:2px 0 0 2px; opacity:0.9;"></div>
            <div style="position:absolute; bottom:-1px; right:-1px; width:18px; height:18px;
                 border-color:{t['accent']}; border-style:solid; border-width:0 2px 2px 0; opacity:0.9;"></div>
            {badge_html}
            <div style="font-size:1.7rem; font-weight:700; line-height:1.25; margin-bottom:0.5rem; letter-spacing:-0.01em;">{title}</div>
            <div style="font-size:1rem; color:{t['text_secondary']}; font-weight:400; max-width:90%;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, desc: str = ""):
    """Render a consistent section header with optional caption."""
    t = get_theme()
    st.markdown(
        f"<h3 style='color:{t['text_primary']} !important; margin-top:1.4rem; margin-bottom:0.3rem; "
        f"font-weight:700; border-left:3px solid {t['accent']}; padding-left:0.6rem;'>{title}</h3>",
        unsafe_allow_html=True,
    )
    if desc:
        st.caption(desc)


def metric_card(value: str, label: str, color: str = None):
    """Render a styled metric card."""
    t = get_theme()
    color = color or t["accent"]
    st.markdown(
        f"""
        <div style='background:{t["bg_card"]}; border:1px solid {t["border"]}; border-radius:6px;
             padding:1rem; text-align:center;'>
            <div style="font-family:'IBM Plex Mono', monospace; font-size:1.3rem; font-weight:600; color:{color} !important;">{value}</div>
            <div style='font-size:0.7rem; color:{t["text_muted"]}; text-transform:uppercase; font-weight:600; letter-spacing:0.05em; margin-top:0.3rem;'>{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_card(title: str, body: str, accent: str = None):
    """Render a contextual info card."""
    t = get_theme()
    accent = accent or t["accent_alt"]
    st.markdown(
        f"""
        <div style='background:{t["bg_card"]}; border:1px solid {accent}66; border-radius:6px; padding:1rem 1.25rem; margin-bottom:1rem;'>
            <div style='font-weight:700; color:{accent}; margin-bottom:0.25rem;'>{title}</div>
            <div style='color:{t["text_secondary"]}; font-size:0.9rem;'>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer(module_name: str, version: str = "1.0"):
    """Render the standard page footer."""
    t = get_theme()
    st.markdown('<div class="chris-hr"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; color:{t['text_muted']};
             font-size:0.78rem; font-family:'IBM Plex Mono', monospace; margin-top:2rem;">
            <div>{module_name}</div>
            <div>DEVELOPER: KULA CHRIS (CHRISHEM)</div>
            <div>UNIFIED PLATFORM v{version}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def tab_badge(label: str, active: bool = True):
    """Return an HTML badge for tab labels."""
    t = get_theme()
    color = t["accent"] if active else t["text_muted"]
    return f"<span style='color:{color}; font-weight:700;'>{label}</span>"


def render_dataset_context_banner():
    """Show the active dataset context banner (rows/cols/source) used at top of analytical hubs."""
    from modules.session_manager import dataset_summary

    summary = dataset_summary()
    if summary:
        st.info(
            f"\U0001F4CA **Active Dataset:** `{summary['source']}` \u2014 {summary['rows']:,} rows \u00d7 {summary['cols']} cols "
            f"| {summary['numeric']} numeric | {summary['categorical']} categorical | {summary['missing']:,} missing"
        )
    else:
        st.warning("\u26A0\uFE0F **No active dataset loaded.** Load data in the **Data Studio** hub or generate sample data.")
        col_a, col_b = st.columns([1, 3])
        with col_a:
            if st.button("\U0001F3B2 Load Sample Data", type="primary", use_container_width=True):
                from modules.session_manager import generate_sample_dataset, set_active_dataframe

                set_active_dataframe(generate_sample_dataset(), "sample_research_cohort.csv")
                st.rerun()


def render_export_buttons(df, base_name: str = "export"):
    """Render standard export/download buttons for a dataframe."""
    if df is None or df.empty:
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "\U0001F4E5 Download CSV",
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
                "\U0001F4E5 Download Excel",
                data=excel_buffer.getvalue(),
                file_name=f"{base_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception:
            st.info("openpyxl required for Excel export")
    with col3:
        st.download_button(
            "\U0001F4E5 Download JSON",
            data=df.to_json(orient="records").encode("utf-8"),
            file_name=f"{base_name}.json",
            mime="application/json",
            use_container_width=True,
        )


def empty_state(icon: str, title: str, message: str, action_label: str = None, action_key: str = None):
    """Render a polished empty-state card with optional action button.
    Returns True if the action button was clicked."""
    t = get_theme()
    st.markdown(
        f"""
        <div class="chris-card" style="text-align:center; padding:2rem;">
            <div style="font-size:2.2rem;">{icon}</div>
            <div style="font-size:1.05rem; font-weight:700; color:{t['accent']}; margin:0.6rem 0 0.2rem 0;">{title}</div>
            <div style="color:{t['text_muted']}; font-size:0.9rem;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if action_label:
        return st.button(action_label, type="primary", use_container_width=True, key=action_key)
    return False
