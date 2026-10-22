"""ResearchOS automation preview with explicit non-execution semantics.

This screen records an operator's intent to implement/run a workflow. It does not
invoke cross-system jobs. A future execution adapter must own authorization, input
validation, idempotency, retries, durable status and verifiable execution evidence.
"""
from __future__ import annotations

import sqlite3
import uuid

import pandas as pd
import streamlit as st

from modules.schema_engine import DB_FILE, init_db


WORKFLOW_OPTIONS = [
    "Sync Genomics → WHO Pathogen Mesh",
    "Trigger Satellite Telemetry → Agri-Grant Impact Audit",
    "Run Anti-Rot Deterministic Snapshot (SHA-256)",
    "Compile Research Nodes → Policy Brief",
    "Run Multi-System Health & Integrity Sweep",
]


def _ensure_log_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS automated_pipeline_logs (
            trigger_id TEXT PRIMARY KEY,
            source_module TEXT NOT NULL,
            action_executed TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def render_master_automation_control_center() -> None:
    st.subheader("ResearchOS Master Automation — Control Center")
    st.caption(
        "Workflow request registry. Selecting a workflow records a preview request; "
        "it does not synchronize systems, call external services, or execute jobs."
    )

    init_db()
    with sqlite3.connect(DB_FILE) as connection:
        _ensure_log_table(connection)

    left, right = st.columns(2)
    with left:
        st.markdown("### Workflow request")
        selected_pipeline = st.selectbox(
            "Select a workflow capability",
            WORKFLOW_OPTIONS,
            key="master_automation_workflow",
        )
        st.warning(
            "Execution adapter is not connected. Do not treat a recorded request as "
            "a successful run or as evidence that an external system changed."
        )
        if st.button("Record preview request", type="primary", key="record_automation_preview"):
            trigger_id = f"PREVIEW-{uuid.uuid4().hex[:12].upper()}"
            with sqlite3.connect(DB_FILE) as connection:
                _ensure_log_table(connection)
                connection.execute(
                    """
                    INSERT INTO automated_pipeline_logs
                    (trigger_id, source_module, action_executed, status)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        trigger_id,
                        "ResearchOS",
                        selected_pipeline,
                        "PREVIEW_ONLY_NOT_EXECUTED",
                    ),
                )
            st.info(
                f"Preview request recorded as {trigger_id}. No workflow was executed."
            )

    with right:
        st.markdown("### Request and execution evidence")
        with sqlite3.connect(DB_FILE) as connection:
            _ensure_log_table(connection)
            log_df = pd.read_sql_query(
                """
                SELECT trigger_id, source_module, action_executed, status, timestamp
                FROM automated_pipeline_logs
                ORDER BY timestamp DESC
                LIMIT 100
                """,
                connection,
            )
        if log_df.empty:
            st.info("No workflow requests recorded yet.")
        else:
            st.dataframe(log_df, width="stretch", hide_index=True)
            st.caption(
                "PREVIEW_ONLY_NOT_EXECUTED means exactly that: it is not a completed "
                "job, successful sync, or external side effect."
            )
