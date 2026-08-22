"""
Integration example: drop this into 7___Literature_Publishing_Hub.py's
render_literature_search(), inside the `tab_search` block, right after the
existing instant-search UI (the one calling search_crossref() synchronously).

It doesn't replace the existing instant search — that's genuinely fine for
20-100 results, no need to queue it. This adds a second option for the case
the current code can't really handle well: harvesting hundreds of papers,
which today would mean a single 100-row CrossRef call the code doesn't even
attempt (n_results is capped at 100 in the existing slider) and which would
block the Streamlit request for however long that takes.
"""

import streamlit as st
import pandas as pd
from modules.task_client import submit_task, render_task_progress, cancel_task

st.markdown("---")
st.markdown("#### 📦 Background Bulk Harvest (background job, 100–2000 papers)")
st.caption(
    "For a systematic review or meta-analysis where you need hundreds of records: "
    "this runs as a background job so it survives you navigating to another tab, "
    "and reports real per-page progress instead of freezing the UI."
)

col_b1, col_b2, col_b3 = st.columns([2, 1, 1])
with col_b1:
    bulk_query = st.text_input("Bulk search query", key="bulk_lit_query")
with col_b2:
    bulk_target = st.number_input("Target paper count", min_value=100, max_value=2000, value=300, step=50, key="bulk_lit_target")
with col_b3:
    st.markdown("<br>", unsafe_allow_html=True)
    launch = st.button("🚀 Start Background Harvest", key="bulk_lit_launch", use_container_width=True)

if launch:
    if not bulk_query.strip():
        st.warning("Enter a query first.")
    else:
        submit_task(
            "lit_bulk_harvest",
            "tasks.harvest_literature_task",
            args=(bulk_query, int(bulk_target), "researcher@university.edu", "Relevance"),
        )
        st.rerun()

# This call self-drives reruns via st.rerun() internally while the job is in
# flight — you don't need a while-loop or a separate polling mechanism.
bulk_result = render_task_progress("lit_bulk_harvest")

if bulk_result is not None:
    df_bulk = pd.DataFrame(bulk_result["records"])
    st.success(
        f"Harvested {bulk_result['returned']} / {bulk_result['requested']} requested records"
        + (" (stopped early — CrossRef had no more matches or the time limit was reached)."
           if bulk_result.get("truncated") else ".")
    )
    st.dataframe(df_bulk, use_container_width=True, hide_index=True)
    render_export_buttons(df_bulk, base_name="bulk_literature_harvest")

    if st.button("Clear this job", key="bulk_lit_clear"):
        cancel_task("lit_bulk_harvest")
        st.rerun()
