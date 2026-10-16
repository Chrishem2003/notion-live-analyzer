"""Interactive execution console for the persistent local workflow runtime."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import streamlit as st

from modules.workflow_access import (
    WorkflowAccessConfigurationError,
    is_workflow_session_valid,
    load_workflow_password,
    verify_workflow_password,
)
from modules.workflow_handlers import default_handlers
from modules.workflow_runtime import WorkflowRuntime
from modules.notion_workflow_handoff import NotionHandoffError, sync_run_to_notion
from modules.workflow_store import list_run_events

st.set_page_config(page_title="Workflow Execution Center", page_icon="⚙️", layout="wide")
st.title("⚙️ Workflow Execution Center")
st.caption(
    "Execute allow-listed research and data tasks with persistent run records. "
    "This page does not claim to call external AI, literature, or Notion services."
)

# Fail closed: this page can write to local storage and may hold a Notion API token.
# Do not rely on the repository's legacy placeholder authentication gateway.
try:
    try:
        configured_secrets = st.secrets
    except Exception:
        configured_secrets = {}
    operator_password = load_workflow_password(configured_secrets, os.environ)
except WorkflowAccessConfigurationError:
    st.error("Workflow Execution Center is locked because operator access is not configured.")
    st.info(
        "Set a unique WORKFLOW_EXECUTION_PASSWORD with at least 24 characters in "
        "Streamlit secrets or the deployment environment. No default password is provided."
    )
    st.stop()

if st.session_state.get("workflow_execution_authenticated", False):
    if not is_workflow_session_valid(
        True,
        st.session_state.get("workflow_execution_authenticated_at"),
        now=time.time(),
    ):
        st.session_state["workflow_execution_authenticated"] = False
        st.session_state.pop("workflow_execution_authenticated_at", None)
        st.warning("The operator session expired after 15 minutes. Unlock the console again.")

if not st.session_state.get("workflow_execution_authenticated", False):
    with st.form("workflow_execution_unlock_form"):
        candidate_password = st.text_input(
            "Workflow operator password", type="password", autocomplete="current-password"
        )
        unlock_clicked = st.form_submit_button("Unlock execution center", type="primary")
    if unlock_clicked:
        if verify_workflow_password(candidate_password, operator_password):
            st.session_state["workflow_execution_authenticated"] = True
            st.session_state["workflow_execution_authenticated_at"] = time.time()
            st.rerun()
        else:
            st.error("Access denied. The operator password was not accepted.")
    st.stop()

if st.button("Lock execution center"):
    st.session_state["workflow_execution_authenticated"] = False
    st.session_state.pop("workflow_execution_authenticated_at", None)
    st.rerun()

configured_path = os.environ.get("WORKFLOW_RUNTIME_DB", ".streamlit/workflow_runtime.sqlite3")
db_path = Path(configured_path).expanduser()
if not db_path.is_absolute():
    db_path = Path.cwd() / db_path

st.info(
    "Storage boundary: SQLite persists across app reruns on this filesystem. "
    "For hosted or multi-worker deployment, configure WORKFLOW_RUNTIME_DB on durable shared storage "
    "and use a coordinated worker/queue service before relying on production execution."
)

try:
    runtime = WorkflowRuntime(db_path, handlers=default_handlers())
except Exception:
    st.error("The workflow runtime could not initialize its database. No task has been submitted.")
    st.stop()

task_descriptions = {
    "research_problem_triage": "Research problem triage — create an evidence-led work brief",
    "numeric_summary": "Numeric summary — compute descriptive statistics",
    "data_quality_profile": "Data quality profile — inspect rows for missingness and duplicates",
}
task_type = st.selectbox("Task type", list(task_descriptions), format_func=lambda key: task_descriptions[key])
workflow_id = st.text_input("Workflow / project identifier", value="interactive-research")
examples = {
    "research_problem_triage": {
        "problem": "Determine whether the new water measurements indicate a quality concern",
        "context": "Include sampling location, date, methods, units, and applicable threshold sources.",
    },
    "numeric_summary": {"values": [7.1, 7.3, 6.9, 7.2, 7.0]},
    "data_quality_profile": {
        "rows": [
            {"sample_id": "S-01", "ph": 7.1, "site": "A"},
            {"sample_id": "S-02", "ph": 7.3, "site": "B"},
            {"sample_id": "S-02", "ph": 7.3, "site": "B"},
            {"sample_id": "S-04", "ph": None, "site": "A"},
        ]
    },
}
payload_text = st.text_area(
    "Input payload (JSON)",
    value=json.dumps(examples[task_type], indent=2),
    height=220,
    help="Only JSON data is accepted. The selected trusted handler determines how the payload is interpreted.",
)
max_attempts = st.number_input("Maximum attempts", min_value=1, max_value=5, value=2, step=1)

if st.button("Validate, submit and execute", type="primary"):
    try:
        payload = json.loads(payload_text)
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object.")
        run_id = runtime.submit(
            workflow_id=workflow_id,
            task_type=task_type,
            payload=payload,
            max_attempts=int(max_attempts),
        )
        result = runtime.execute_run(run_id)
        st.session_state["workflow_runtime_last_run_id"] = run_id
        st.success(f"Run recorded: {run_id}")
        if result:
            st.write(f"**Status:** {result['status']} · **Attempt:** {result['attempt']}")
            if result.get("result") is not None:
                st.markdown("#### Result")
                st.json(result["result"])
            elif result.get("error_message"):
                st.warning(result["error_message"])
                st.caption("A failed attempt may be queued for another explicit execution.")
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        st.error(f"Input was rejected: {exc}")
    except Exception:
        st.error("The workflow could not complete. Inspect the run record and server logs; do not assume success.")

st.markdown("---")
st.subheader("Recovery controls")
st.caption(
    "Manual recovery only: use when a previous local process stopped while a run was marked running. "
    "Do not use this with concurrent or long-running workers unless real leases/heartbeats are configured."
)
if st.button("Recover interrupted runs older than 10 minutes"):
    try:
        recovered = runtime.recover_stale_runs(older_than_seconds=600)
        if recovered:
            st.success(f"Recovered {len(recovered)} interrupted run(s).")
            st.dataframe(recovered, use_container_width=True, hide_index=True)
            st.rerun()
        else:
            st.info("No stale running jobs met the recovery threshold.")
    except Exception:
        st.error("Recovery did not complete; inspect server logs before retrying.")

st.markdown("---")
st.subheader("Recent persisted runs")
try:
    runs = runtime.list_runs(limit=100)
    if not runs:
        st.info("No workflow runs have been submitted yet.")
    else:
        st.dataframe(
            [
                {
                    "Run ID": run["run_id"],
                    "Workflow": run["workflow_id"],
                    "Task": run["task_type"],
                    "Status": run["status"],
                    "Attempt": f"{run['attempt']}/{run['max_attempts']}",
                    "Created": run["created_at"],
                    "Updated": run["updated_at"],
                    "Error": run["error_message"] or "",
                }
                for run in runs
            ],
            use_container_width=True,
            hide_index=True,
        )
        selected_run_id = st.selectbox(
            "Inspect run history",
            [run["run_id"] for run in runs],
            index=next(
                (i for i, run in enumerate(runs)
                 if run["run_id"] == st.session_state.get("workflow_runtime_last_run_id")),
                0,
            ),
        )
        selected_run = runtime.get_run(selected_run_id)
        if selected_run:
            st.markdown("#### Selected run details")
            st.json({
                "run_id": selected_run["run_id"],
                "workflow_id": selected_run["workflow_id"],
                "task_type": selected_run["task_type"],
                "status": selected_run["status"],
                "input": selected_run["input"],
                "result": selected_run["result"],
                "error_message": selected_run["error_message"],
            })
            if selected_run["status"] == "succeeded":
                st.markdown("#### Notion handoff")
                st.caption(
                    "Sending this execution record does not approve its science: QC remains Pending, "
                    "reproducibility remains Not Checked, and the record is classified Synthetic/Test."
                )
                if st.button("Send execution record to Notion", key="handoff_selected_run"):
                    try:
                        delivery = sync_run_to_notion(selected_run)
                        if delivery.get("created"):
                            st.success("Execution record created in Notion.")
                        else:
                            st.info("A matching execution record already exists in Notion; no duplicate was created.")
                        if delivery.get("url"):
                            st.markdown(f"[Open Notion execution record]({delivery['url']})")
                        st.code(delivery["manifest_hash"], language="text")
                    except NotionHandoffError as exc:
                        st.error(f"Notion handoff not completed: {exc}")
                    except Exception:
                        st.error("Notion handoff failed unexpectedly; no delivery success is claimed.")
            if selected_run["status"] == "queued" and st.button("Execute this queued run", key="execute_selected_run"):
                executed = runtime.execute_run(selected_run_id)
                st.session_state["workflow_runtime_last_run_id"] = selected_run_id
                st.rerun()
            events = list_run_events(str(db_path), selected_run["workflow_id"], selected_run_id)
            st.markdown("#### Append-only event history")
            st.dataframe(
                [
                    {
                        "Sequence": event["sequence"],
                        "Event": event["event_type"],
                        "Stage": event["stage"],
                        "Status": event["status"],
                        "Occurred at": event["occurred_at"],
                    }
                    for event in events
                ],
                use_container_width=True,
                hide_index=True,
            )
except Exception:
    st.warning("Run history could not be loaded. Existing stored records have not been deleted.")

st.caption(
    "Built-in handlers perform deterministic computations only. Results require domain review; "
    "safety, clinical, legal, compliance, and other high-impact decisions require qualified human oversight."
)
