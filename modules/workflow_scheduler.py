"""Truthful workflow scheduler status panel.

No durable scheduler adapter is configured in this repository yet. This module
must not present illustrative jobs, invented execution counts, or success
messages as real execution evidence. Replace the empty registry with a real
scheduler adapter before reporting live jobs.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.database import log_backend_event

WORKFLOW_COLUMNS = [
    "Workflow_Name",
    "Schedule",
    "Target_Module",
    "Last_Run",
    "Status",
]


def get_scheduled_workflows() -> pd.DataFrame:
    """Return actual registered workflows; empty until a scheduler is wired.

    This intentionally returns no sample rows. A future adapter must source
    records from the real scheduler and include actual run timestamps/statuses.
    """
    return pd.DataFrame(columns=WORKFLOW_COLUMNS)


def render_workflow_scheduler_panel() -> None:
    """Render scheduler availability without claiming unperformed work."""
    st.subheader("Autonomous Workflow & Task Scheduler")
    st.caption(
        "Inspect configured jobs and execution evidence. A visible workflow "
        "record is not proof that a job has run."
    )

    st.info(
        "Scheduler backend is not connected. No recurring jobs or execution "
        "history are currently registered in this panel."
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(label="Registered Schedules", value="0")
    with c2:
        st.metric(label="Executions Today", value="Unavailable")
    with c3:
        st.metric(label="Next Scheduled Run", value="Not configured")
    with c4:
        st.metric(label="Scheduler Health", value="Not connected")

    st.markdown("---")
    st.markdown("### Registered Workflow Execution Queue")
    st.dataframe(get_scheduled_workflows(), width="stretch")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Trigger Immediate Workflow Sweep", disabled=True):
            # Intentionally disabled until a real executor and run-ID contract
            # are implemented; never report a simulated sweep as successful.
            pass
    with col_b:
        if st.button("Register New Scheduled Task", disabled=True):
            # Registration requires durable storage, validation, and a scheduler.
            pass

    st.caption(
        "Controls remain disabled until a durable scheduler adapter supports "
        "validated registration, actual execution, run IDs, retries, and logs."
    )
