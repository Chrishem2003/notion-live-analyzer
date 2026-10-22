"""Truthful status panel for scheduled automation capabilities.

This module intentionally reports configured/implemented status rather than inventing
run history. A schedule is not considered active until a real scheduler backend records
its execution evidence.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.database import log_backend_event


def get_scheduled_workflows() -> pd.DataFrame:
    """Return the current capability inventory, not simulated execution telemetry."""
    workflows = [
        {
            "Workflow_Name": "Autonomous Sequence Pipeline Sync",
            "Schedule": "Not configured",
            "Target_Module": "Biodefense Core",
            "Last_Run": "No execution evidence",
            "Status": "PLANNED — NOT RUNNING",
        },
        {
            "Workflow_Name": "Billing Ledger Auto-Reconciliation",
            "Schedule": "Not configured",
            "Target_Module": "Admin Billing",
            "Last_Run": "No execution evidence",
            "Status": "PLANNED — NOT RUNNING",
        },
        {
            "Workflow_Name": "Quantum Vault Key Rotation",
            "Schedule": "Not configured",
            "Target_Module": "Quantum Vault",
            "Last_Run": "No execution evidence",
            "Status": "PLANNED — NOT RUNNING",
        },
        {
            "Workflow_Name": "Telemetry Health Snapshot",
            "Schedule": "Not configured",
            "Target_Module": "Telemetry Alerting",
            "Last_Run": "No execution evidence",
            "Status": "PLANNED — NOT RUNNING",
        },
    ]
    return pd.DataFrame(workflows)


def render_workflow_scheduler_panel() -> None:
    """Render a capability inventory without implying that jobs execute."""
    st.subheader("Autonomous Workflow & Task Scheduler")
    st.caption(
        "Capability inventory only. No recurring scheduler is connected here yet; "
        "displayed workflows are plans, not active background jobs."
    )
    df_workflows = get_scheduled_workflows()
    st.dataframe(df_workflows, width="stretch", hide_index=True)
    st.warning(
        "Execution remains disabled until a real scheduler, durable job state, "
        "retry policy, and run evidence are connected and tested."
    )
    if st.button("Record scheduler implementation request", key="scheduler_request"):
        log_backend_event(
            "INFO",
            "Scheduler implementation requested; no workflow was executed.",
        )
        st.info("Request recorded. No background task was started.")
