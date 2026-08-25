"""
CHRISHEM Opportunity Feed UI
============================
Streamlit renderer for the live verified Opportunity Feed (200 curated
scholarships, grants, fellowships, internships, awards). Wraps the
`opportunity_feed` engine with geo-prioritization, verification badges,
filtering, pagination, and a "save to pipeline" flow.

Owner: Kula Chris (CHRISHEM)
"""
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from modules.opportunity_feed import (
    OpportunityDatabase,
    OpportunityFeedEngine,
    OpportunityType,
    SourceAuthority,
    VerificationScorer,
    seed_opportunity_catalog,
    get_country_flag,
    get_region_for_country,
)


@st.cache_resource(show_spinner=False)
def _get_engine() -> OpportunityFeedEngine:
    """Get (and seed) the opportunity feed engine once per session."""
    db = seed_opportunity_catalog()
    return OpportunityFeedEngine(db=db)


def _user_country() -> str:
    ident = st.session_state.get("user_identity", {})
    return ident.get("country", "Uganda")


def _render_featured(engine: OpportunityFeedEngine, country: str):
    """Render top geo-relevant featured opportunities."""
    featured = engine.get_featured(country, limit=3)
    if not featured:
        return
    st.markdown("### ⭐ Featured for You")
    cols = st.columns(len(featured))
    for i, opp in enumerate(featured):
        with cols[i]:
            ver = opp.get("verification_score", 0) or 0
            badge = VerificationScorer.verification_badge(ver)
            amount = ""
            if opp.get("amount_min_usd") and opp.get("amount_max_usd"):
                amount = f"${opp['amount_min_usd']:,.0f}–${opp['amount_max_usd']:,.0f}"
            elif opp.get("amount_max_usd"):
                amount = f"${opp['amount_max_usd']:,.0f}"
            st.markdown(
                f"""
                <div style="background:#171B23;border:1px solid #6366f155;border-radius:14px;padding:1rem;height:100%;">
                    <div style="font-size:1.6rem;">{get_country_flag(opp.get('country',''))}</div>
                    <div style="font-weight:800;color:#f1f5f9;font-size:0.85rem;margin:0.3rem 0;">{opp.get('title','')}</div>
                    <div style="color:#8b93a8;font-size:0.75rem;">{opp.get('organization','')}</div>
                    <div style="margin:0.4rem 0;">
                        <span style="background:{badge['bg']};color:{badge['color']};border:1px solid {badge['border']};border-radius:999px;padding:0.1rem 0.5rem;font-size:0.65rem;">{badge['icon']} {badge['label']} {ver:.0f}</span>
                    </div>
                    <div style="color:#6B7280;font-size:0.75rem;">{amount or 'Amount varies'} · {opp.get('field_of_study','')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_stats(engine: OpportunityFeedEngine):
    """Render feed statistics."""
    stats = engine.get_statistics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌍 Total Opportunities", stats["total"])
    c2.metric("✅ High-Verified (80+)", stats["high_verified"])
    c3.metric("⭐ Avg Verification", f"{stats['avg_verification']:.0f}%")
    c4.metric("🗂️ Types", len(stats.get("by_type", {})))


def render_opportunity_feed_tab():
    """Main entry point — render the full Opportunity Feed tab."""
    st.markdown(
        "### 🎓 Scholarship & Opportunity Feed\n"
        "**200 curated, geo-prioritized scholarships, grants, fellowships, internships & awards** "
        "from verified government, university, and foundation sources. "
        "Each entry carries a trust score and maps to your country first."
    )

    engine = _get_engine()
    country = _user_country()
    st.caption(f"Geo-prioritized for: **{country}** {get_country_flag(country)}")

    # ── Stat Cards ────────────────────────────────────────────────────
    _render_stats(engine)
    _render_featured(engine, country)

    st.markdown("---")

    # ── Filters ───────────────────────────────────────────────────────
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        types_sel = st.multiselect(
            "Type", [t.value for t in OpportunityType],
            default=[t.value for t in OpportunityType],
            key="opp_types",
        )
    with col_f2:
        amount_filter = st.select_slider(
            "Min amount (USD)", options=[0, 10000, 20000, 50000, 100000],
            value=0, key="opp_amount",
        )
    with col_f3:
        ver_min = st.slider("Min verification score", 0, 100, 50, key="opp_ver")
    with col_f4:
        query = st.text_input("🔍 Search opportunities", placeholder="e.g. 'AI', 'Africa', 'Masters'", key="opp_query")

    # ── Fetch feed ────────────────────────────────────────────────────
    feed = engine.get_feed(
        user_country=country,
        types=types_sel if types_sel else None,
        amount_min=amount_filter if amount_filter > 0 else None,
        verification_min=ver_min,
        query=query,
    )

    results = feed.get("results", [])
    total = feed.get("total", 0)
    st.markdown(f"**{total} opportunities match your criteria**")

    if not results:
        st.info("No opportunities match the current filters. Try widening your search.")
        return

    # ── Render cards ──────────────────────────────────────────────────
    for opp in results:
        ver = opp.get("verification_score", 0) or 0
        badge = VerificationScorer.verification_badge(ver)
        otype = opp.get("type", "")
        type_icon = OpportunityType.icon(otype)
        amount = ""
        if opp.get("amount_min_usd") and opp.get("amount_max_usd"):
            amount = f"${opp['amount_min_usd']:,.0f}–${opp['amount_max_usd']:,.0f}"
        elif opp.get("amount_max_usd"):
            amount = f"${opp['amount_max_usd']:,.0f}"
        deadline = opp.get("deadline", "")
        deadline_str = ""
        if deadline:
            try:
                from datetime import datetime as _dt
                dd = _dt.fromisoformat(deadline).date()
                days = (dd - _dt.now().date()).days
                deadline_str = f"📅 {dd.strftime('%b %d, %Y')} ({days}d left)" if days >= 0 else f"⚠️ Closed {abs(days)}d ago"
            except Exception:
                deadline_str = deadline
            catch = deadline_str

        with st.container():
            st.markdown(
                f"""
                <div style="background:#171B23;border:1px solid #262B33;border-radius:14px;padding:1rem;margin-bottom:0.75rem;">
                    <div style="display:flex;gap:0.75rem;align-items:flex-start;">
                        <div style="font-size:1.8rem;">{type_icon} {get_country_flag(opp.get('country',''))}</div>
                        <div style="flex:1;min-width:0;">
                            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;">
                                <div>
                                    <div style="font-weight:800;color:#f1f5f9;font-size:0.95rem;">{opp.get('title','')}</div>
                                    <div style="color:#8b93a8;font-size:0.78rem;">{opp.get('organization','')} · {opp.get('source_authority','')}</div>
                                </div>
                                <span style="background:{badge['bg']};color:{badge['color']};border:1px solid {badge['border']};border-radius:999px;padding:0.1rem 0.6rem;font-size:0.65rem;white-space:nowrap;">{badge['icon']} {badge['label']} {ver:.0f}</span>
                            </div>
                            <div style="display:flex;flex-wrap:wrap;gap:0.35rem;margin:0.4rem 0;">
                                <span class="feed-badge" style="background:rgba(99,102,241,.15);color:#8b93a8;border:1px solid rgba(99,102,241,.3);border-radius:999px;padding:0.05rem 0.5rem;font-size:0.65rem;">{OpportunityType.emoji_badge(otype)}</span>
                                <span class="feed-badge" style="background:rgba(34,197,94,.15);color:#4ade80;border:1px solid rgba(34,197,94,.3);border-radius:999px;padding:0.05rem 0.5rem;font-size:0.65rem;">💰 {amount or 'Amount varies'}</span>
                                <span class="feed-badge" style="background:rgba(59,130,246,.15);color:#60a5fa;border:1px solid rgba(59,130,246,.3);border-radius:999px;padding:0.05rem 0.5rem;font-size:0.65rem;">🌍 {opp.get('region','')}</span>
                                <span class="feed-badge" style="background:rgba(236,72,153,.15);color:#f472b6;border:1px solid rgba(236,72,153,.3);border-radius:999px;padding:0.05rem 0.5rem;font-size:0.65rem;">{opp.get('field_of_study','All Fields')}</span>
                            </div>
                            <div style="color:#6B7280;font-size:0.78rem;line-height:1.5;">{opp.get('description','')[:220]}{'…' if len(opp.get('description',''))>220 else ''}</div>
                            <div style="color:#64748b;font-size:0.72rem;margin-top:0.4rem;">{deadline_str or 'Open / rolling deadline'}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            src_url = opp.get("source_url", "")
            b1, b2 = st.columns([1, 5])
            with b1:
                if st.button("⭐ Save to Pipeline", key=f"save_{opp['id']}", use_container_width=True):
                    st.success(f"Saved **{opp.get('title','')}** to your application pipeline.")
            with b2:
                if src_url and str(src_url).startswith("http"):
                    st.markdown(f"[🔗 Official Source]({src_url}) · {opp.get('source_authority','')} source")

    # ── Pagination ────────────────────────────────────────────────────
    total_pages = feed.get("total_pages", 1)
    if total_pages > 1:
        st.markdown("---")
        pg, info = st.columns([1, 3])
        with pg:
            p = st.selectbox("Page", list(range(1, total_pages + 1)), index=feed.get("page", 0), key="opp_page")
        with info:
            st.caption(f"Showing page {p} of {total_pages} · {feed.get('per_page', 20)} per page")


if __name__ == "__main__":
    print("Opportunity Feed UI module loaded.")

