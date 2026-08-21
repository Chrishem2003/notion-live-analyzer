"""
Integration example: Live Agent Workbench â€” the "visual representation of
the agent swarm executing sub-tasks in real-time" from the spec.

Drop this into a hub as a new tab (Collaboration & Portfolio and ML &
Predictive Studio both make sense â€” it uses `get_active_dataframe()` from
whichever hub it's embedded in). Uses agents.build_swarm_graph().stream()
so the UI updates as each real node finishes, not after one blocking call.
"""

import streamlit as st
from agents import build_swarm_graph

st.markdown("### ðŸ¦¾ Live Agent Workbench")
st.caption(
    "Three specialist agents work your problem: a Research agent (live CrossRef search), "
    "a Data Auditor (real pandas/IQR analysis of your active dataset), and a Synthesis "
    "agent that combines only what the other two actually found."
)

problem = st.text_area(
    "Describe the multi-sector challenge",
    placeholder="e.g., water contamination risk in agricultural runoff near urban centers",
    key="swarm_problem",
)
run_swarm_btn = st.button("ðŸš€ Deploy Agent Swarm", type="primary", key="run_swarm_btn")

if run_swarm_btn:
    if not problem.strip():
        st.warning("Describe a problem for the swarm to work on first.")
    else:
        df = get_active_dataframe()  # from the hub this is embedded in
        graph = build_swarm_graph()

        research_box = st.empty()
        audit_box = st.empty()
        synthesis_box = st.empty()
        research_box.info("ðŸ”Ž Research agent: querying CrossRef...")
        audit_box.info("ðŸ“Š Data auditor: profiling active dataset..." if df is not None else "ðŸ“Š Data auditor: no dataset loaded â€” will report that honestly.")
        synthesis_box.info("ðŸ§  Synthesis agent: waiting on both agents above...")

        final_state = {}
        for step in graph.stream({
            "problem": problem,
            "dataset": df,
            "literature_findings": None,
            "audit_findings": None,
            "synthesis": None,
            "errors": [],
        }):
            node_name, node_output = next(iter(step.items()))
            final_state.update(node_output)

            if node_name == "research":
                lit = node_output.get("literature_findings")
                if lit:
                    research_box.success(f"âœ… Research agent: found {lit['n_found']}} papers (top: \"{lit['top_papers'][0]['title'][:70]}...\")" if lit["top_papers"] else f"âœ… Research agent: 0 matches for this query.")
                else:
                    research_box.error(f"âŒ Research agent failed: {node_output.get('errors', ['unknown error'])[-1]}}")

            elif node_name == "audit":
                audit = node_output.get("audit_findings")
                if audit and audit.get("status") == "ok":
                    audit_box.success(f"âœ… Data auditor: {audit['n_rows']}} rows, {audit['missing_cells']}} missing cells, "
                                       f"{len(audit['numeric_columns_with_outliers'])}} column(s) with outliers.")
                elif audit:
                    audit_box.warning(f"âš ï¸ Data auditor: {audit.get('note', audit.get('status'))}}")
                else:
                    audit_box.error(f"âŒ Data auditor failed: {node_output.get('errors', ['unknown error'])[-1]}}")

            elif node_name == "synthesis":
                synthesis_box.success("âœ… Synthesis agent complete.")

        st.markdown("---")
        st.markdown("#### ðŸ“‹ Synthesis Output")
        st.markdown(final_state.get("synthesis", "_No synthesis produced â€” check agent errors above._"))

        if final_state.get("errors"):
            with st.expander("âš ï¸ Agent errors this run"):
                for err in final_state["errors"]:
                    st.code(err)
