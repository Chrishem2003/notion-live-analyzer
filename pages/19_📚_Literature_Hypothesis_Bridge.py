"""
Literature-Hypothesis Bridge — Connect literature findings to hypothesis generation.
End-to-end pipeline: harvest papers → extract effect sizes → compare with data patterns → identify gaps.
"""

import streamlit as st

st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
st.set_page_config(page_title="Literature-Hypothesis Bridge", page_icon="🔗", layout="wide")

from modules.literature_engine import (
    LiteratureDatabase, PaperHarvester, EffectSizeExtractor,
    ReferenceFormatter
)
from modules.hypothesis_generator import HypothesisGenerator
import pandas as pd
from datetime import datetime

# ─── Init ─────────────────────────────────────────────────────────────
db = LiteratureDatabase()
hg = HypothesisGenerator()
extractor = EffectSizeExtractor(db)
formatter = ReferenceFormatter()

st.markdown("## 🔗 Literature-Hypothesis Bridge")
st.markdown("*Connect published literature findings to your data analysis — discover gaps, replications, and novel patterns*")

# ─── Project Selection ─────────────────────────────────────────────
projects = db.get_projects()
project_options = {p["id"]: p["name"] for p in projects}
if not project_options:
    st.info("No research projects found. Create one in the **📚 Literature Engine** page first.")
    st.stop()

selected_project_id = st.selectbox(
    "Research Project",
    options=list(project_options.keys()),
    format_func=lambda x: project_options[x],
    key="lh_bridge_project",
)

# ─── Main Tabs ─────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📥 1. Harvest Papers & Extract Effects",
    "🔬 2. Compare with Data Patterns",
    "💡 3. Gap Analysis Results",
    "📋 4. Bridge Report",
])

# ═══════════════════════════════════════════════════════════════════
# TAB 1: HARVEST & EXTRACT
# ═══════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("📥 Step 1: Harvest Papers & Extract Effect Sizes")

    # Search for papers
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("Search query", placeholder="e.g., cognitive behavioral therapy depression effect size", key="lh_search")
    with col2:
        max_papers = st.number_input("Max papers", min_value=5, max_value=200, value=30, step=5, key="lh_max")

    if st.button("🔍 Harvest Papers", type="primary", use_container_width=True) and search_query.strip():
        harvester = PaperHarvester()
        with st.spinner(f"Harvesting up to {max_papers} papers from Semantic Scholar..."):
            papers = harvester.search_combined(search_query.strip(), limit=max_papers)

        if papers:
            saved = db.save_papers(selected_project_id, papers)
            st.success(f"✅ Saved {saved} new papers (total in project: {len(papers)})")

            # Auto-extract effect sizes
            extracted_count = 0
            for paper in papers:
                paper_id = db.get_papers(selected_project_id, page=0, per_page=1000)[0]
                # Find the paper in DB
                all_papers, _ = db.get_papers(selected_project_id, page=0, per_page=1000)
                for p in all_papers:
                    if p["title"] == paper.get("title"):
                        effects = extractor.extract_from_paper(p)
                        for eff in effects:
                            extractor.save_effect_size(
                                paper_id=p["id"],
                                project_id=selected_project_id,
                                variable_pair=f"{search_query}__{eff.get('effect_type', 'unknown')}",
                                effect_type=eff.get("effect_type", "cohens_d"),
                                effect_size=abs(eff.get("effect_size", 0)),
                                source=paper.get("title", ""),
                                extracted_by="auto",
                            )
                            extracted_count += 1
                        break

            if extracted_count > 0:
                st.info(f"📊 Auto-extracted {extracted_count} effect sizes from paper abstracts")
        else:
            st.warning("No papers found. Try a different query.")

    # Show extracted effect sizes
    st.markdown("---")
    st.subheader("📊 Extracted Effect Sizes from Literature")

    effects = extractor.get_project_effect_sizes(selected_project_id)
    if effects:
        effects_df = pd.DataFrame(effects)
        st.dataframe(effects_df, use_container_width=True, hide_index=True)

        if st.button("🗑️ Clear All Extracted Effects"):
            for e in effects:
                extractor.delete_effect_size(e["id"])
            st.rerun()
    else:
        st.info("No effect sizes extracted yet. Harvest papers above to auto-extract, or add manually.")

        # Manual entry form
        with st.expander("✏️ Add Effect Size Manually"):
            papers_list, _ = db.get_papers(selected_project_id, per_page=500)
            if papers_list:
                paper_options = {p["id"]: p["title"][:80] for p in papers_list}
                paper_id = st.selectbox("Paper", options=list(paper_options.keys()), format_func=lambda x: paper_options[x], key="lh_manual_paper")
                var_pair = st.text_input("Variable pair", placeholder="e.g., treatment__depression", key="lh_manual_var")
                eff_type = st.selectbox("Effect type", options=["cohens_d", "r", "or", "eta_squared"], key="lh_manual_type")
                eff_val = st.number_input("Effect size", value=0.0, step=0.01, key="lh_manual_es")
                ci_low = st.number_input("CI lower (optional)", value=0.0, step=0.01, key="lh_manual_ci_low")
                ci_up = st.number_input("CI upper (optional)", value=0.0, step=0.01, key="lh_manual_ci_up")
                n_sample = st.number_input("Sample size (optional)", value=0, step=1, key="lh_manual_n")

                if st.button("💾 Save Effect Size", type="primary"):
                    extractor.save_effect_size(
                        paper_id=paper_id,
                        project_id=selected_project_id,
                        variable_pair=var_pair,
                        effect_type=eff_type,
                        effect_size=eff_val,
                        ci_lower=ci_low if ci_low != 0 else None,
                        ci_upper=ci_up if ci_up != 0 else None,
                        sample_size=n_sample if n_sample > 0 else None,
                        source="manual",
                    )
                    st.success("✅ Effect size saved!")
                    st.rerun()

# ═══════════════════════════════════════════════════════════════════
# TAB 2: COMPARE WITH DATA
# ═══════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("🔬 Step 2: Compare Data Patterns Against Literature")

    df = st.session_state.get("active_df")
    if df is None or df.empty:
        st.warning("No data loaded. Upload a file or connect a data source first.")
        st.stop()

    st.info(f"📊 Dataset: {len(df)} rows × {len(df.columns)} columns")

    # Run hypothesis discovery on the data
    if st.button("🔍 Discover Patterns in Data", type="primary", use_container_width=True):
        with st.spinner("Discovering statistical patterns in your data..."):
            hg_results = hg.discover_hypotheses(df)

        if "error" not in hg_results:
            hypotheses = hg_results.get("hypotheses", [])
            st.session_state["lh_bridge_hypotheses"] = hypotheses
            st.success(f"✅ Discovered {len(hypotheses)} patterns in your data")
            st.rerun()
        else:
            st.error(hg_results["error"])

    # Run literature gap analysis
    hypotheses = st.session_state.get("lh_bridge_hypotheses", [])
    effects = extractor.export_for_hypothesis_generator(selected_project_id)

    if hypotheses:
        st.markdown("### 🔍 Literature Gap Analysis")

        discipline = st.selectbox(
            "Academic discipline",
            options=["psychology", "education", "medicine", "neuroscience", "social_science", "business", "biology", "default"],
            key="lh_discipline",
        )

        if st.button("🔬 Run Gap Analysis Against Literature", type="primary", use_container_width=True):
            with st.spinner("Comparing data patterns against literature..."):
                enriched = hg.compare_against_literature(hypotheses, effects, discipline)

            st.session_state["lh_bridge_enriched"] = enriched
            st.success(f"✅ Analyzed {len(enriched)} hypotheses against literature")
            st.rerun()

        # Show raw discovered hypotheses
        with st.expander(f"📋 Discovered Hypotheses ({len(hypotheses)})"):
            for h in hypotheses:
                st.markdown(f"- **{h.get('id', 'H?')}** ({h.get('priority_label', '')}): {h.get('narrative', '')[:150]}...")
    else:
        st.info("Click 'Discover Patterns in Data' to find statistical patterns in your dataset.")

# ═══════════════════════════════════════════════════════════════════
# TAB 3: GAP ANALYSIS RESULTS
# ═══════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("💡 Step 3: Gap Analysis Results")

    enriched = st.session_state.get("lh_bridge_enriched", [])
    if not enriched:
        st.info("Run the gap analysis in Step 2 first.")
        st.stop()

    # Summary stats
    replication_count = sum(1 for h in enriched if h.get("gap_analysis", {}).get("literature_comparison", {}).get("type") == "replication")
    novel_count = sum(1 for h in enriched if h.get("gap_analysis", {}).get("literature_comparison", {}).get("type", "").startswith("novel"))
    knowledge_gap_count = sum(1 for h in enriched if h.get("gap_analysis", {}).get("literature_comparison", {}).get("type") == "knowledge_gap")
    inconsistent_count = sum(1 for h in enriched if h.get("gap_analysis", {}).get("literature_comparison", {}).get("type") == "inconsistent")

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("✅ Replications", replication_count)
    with col2: st.metric("🔬 Novel Findings", novel_count)
    with col3: st.metric("💡 Knowledge Gaps", knowledge_gap_count)
    with col4: st.metric("⚠️ Inconsistent", inconsistent_count)

    # Filter
    gap_type_filter = st.selectbox(
        "Filter by gap type",
        options=["All", "replication", "novel_larger", "novel_smaller", "knowledge_gap", "inconsistent"],
        key="lh_gap_filter",
    )

    for h in enriched:
        gap = h.get("gap_analysis", {}).get("literature_comparison", {})
        gap_type = gap.get("type", "")

        if gap_type_filter != "All" and gap_type != gap_type_filter:
            continue

        novelty_score = gap.get("novelty_score", 0)
        gap_label = gap.get("label", "Unknown")

        # Color coding
        if gap_type == "replication":
            color = "#2ecc71"
        elif gap_type.startswith("novel"):
            color = "#3498db"
        elif gap_type == "knowledge_gap":
            color = "#f39c12"
        else:
            color = "#e74c3c"

        st.markdown(f"""
        <div style="padding:0.8rem;margin:0.5rem 0;border-radius:12px;border-left:4px solid {color};
                    background:{color}08;border:1px solid {color}20;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-weight:700;font-size:0.9rem;">{h.get('id', 'H?')}</span>
                <span style="font-size:0.7rem;padding:0.2rem 0.5rem;border-radius:999px;
                          background:{color}20;color:{color};">{gap_label}</span>
            </div>
            <div style="margin-top:0.3rem;font-size:0.85rem;">{h.get('narrative', '')}</div>
            <div style="margin-top:0.2rem;font-size:0.75rem;color:#64748b;">
                Novelty: {novelty_score}/100 | Effect: {h.get('effect_size', h.get('r', 0)):.3f} | {h.get('test', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# TAB 4: BRIDGE REPORT
# ═══════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("📋 Step 4: Generate Bridge Report")

    enriched = st.session_state.get("lh_bridge_enriched", [])
    effects = extractor.export_for_hypothesis_generator(selected_project_id)

    if not enriched:
        st.info("Complete Steps 1-3 first.")
        st.stop()

    if st.button("📄 Generate Full Bridge Report", type="primary", use_container_width=True):
        report_lines = [
            "# Literature-Hypothesis Bridge Report",
            f"**Generated:** {datetime.now():%Y-%m-%d %H:%M:%S}",
            f"**Project:** {project_options.get(selected_project_id, 'Unknown')}",
            f"**Dataset:** {len(st.session_state.get('active_df', pd.DataFrame()))} rows",
            f"**Literature Effects:** {len(effects)} extracted from literature",
            f"**Discovered Patterns:** {len(enriched)}",
            "",
            "---",
            "## Gap Analysis Summary",
            "",
            f"- ✅ **Replications (consistent with literature):** {replication_count}",
            f"- 🔬 **Novel findings (diverge from literature):** {novel_count}",
            f"- 💡 **Knowledge gaps (no literature found):** {knowledge_gap_count}",
            f"- ⚠️ **Inconsistent with literature:** {inconsistent_count}",
            "",
            "---",
            "## Detailed Findings",
            "",
        ]

        for h in enriched:
            gap = h.get("gap_analysis", {}).get("literature_comparison", {})
            report_lines.append(f"### {h.get('id', 'H?')}: {gap.get('label', 'Unknown')}")
            report_lines.append(f"**Narrative:** {h.get('narrative', '')}")
            report_lines.append(f"**Effect Size:** {h.get('effect_size', h.get('r', 0)):.3f}")
            report_lines.append(f"**Novelty Score:** {gap.get('novelty_score', 0)}/100")
            report_lines.append(f"**Test:** {h.get('test', '')}")
            if gap.get("literature_effect"):
                report_lines.append(f"**Literature Effect:** {gap['literature_effect']:.3f}")
            if gap.get("source"):
                report_lines.append(f"**Source:** {gap['source']}")
            report_lines.append("")

        report = "\n".join(report_lines)
        st.session_state["lh_bridge_report"] = report
        st.success("✅ Report generated!")

    if st.session_state.get("lh_bridge_report"):
        st.markdown(st.session_state["lh_bridge_report"])
        if st.button("📋 Copy Report"):
            # Simple copy via code block
            st.code(st.session_state["lh_bridge_report"], language="markdown")

# ─── Sidebar ────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **How it works:**\n"
    "1. **Harvest** papers & extract effect sizes\n"
    "2. **Discover** patterns in your data\n"
    "3. **Compare** data patterns against literature\n"
    "4. **Identify** replications, novel findings, gaps"
)
