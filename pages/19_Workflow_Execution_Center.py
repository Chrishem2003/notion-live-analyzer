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
from modules.workflow_storage import (
    WorkflowStorageConfigurationError,
    load_workflow_storage_key,
)

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

try:
    runtime_encryption_key = load_workflow_storage_key(configured_secrets, os.environ)
except WorkflowStorageConfigurationError:
    st.error("Workflow Execution Center is locked because payload encryption is not configured.")
    st.info(
        "Set WORKFLOW_RUNTIME_ENCRYPTION_KEY in Streamlit secrets or the deployment environment. "
        "Generate a Fernet key in a trusted environment with: "
        "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\". "
        "Store it only in the approved secret store and keep a protected recovery copy."
    )
    st.stop()

runtime_db_override = os.environ.get("WORKFLOW_RUNTIME_DB", "").strip()
configured_path = runtime_db_override or ".streamlit/workflow_runtime.sqlite3"
db_path = Path(configured_path).expanduser()
if not db_path.is_absolute():
    db_path = Path.cwd() / db_path

st.caption(
    f"Runtime database path: `{db_path}` · "
    + ("explicitly configured with WORKFLOW_RUNTIME_DB" if runtime_db_override else "using the local default path")
)
if not runtime_db_override:
    st.warning(
        "WORKFLOW_RUNTIME_DB is not explicitly configured. The console is using a local path that may be "
        "ephemeral on hosted deployments. Do not assume run history survives restarts or redeployments; "
        "configure and verify durable storage before relying on persistent execution."
    )
st.info(
    "Storage boundary: SQLite persists across app reruns on this filesystem. "
    "For hosted or multi-worker deployment, configure WORKFLOW_RUNTIME_DB on durable shared storage "
    "and use a coordinated worker/queue service before relying on production execution."
)
st.warning(
    "SYNTHETIC / TEST DATA ONLY. Input, result, and error payload fields are application-encrypted with the required Fernet key, but SQLite itself is not database-encrypted and workflow metadata/event digests remain plaintext. "
    "Do not enter personal, identifiable, confidential, regulated, or real research data until key recovery/rotation, filesystem access, backup, retention, and authorization have been reviewed."
)

try:
    runtime = WorkflowRuntime(db_path, handlers=default_handlers(), encryption_key=runtime_encryption_key)
except Exception:
    st.error("The workflow runtime could not initialize its database. No task has been submitted.")
    st.stop()

task_descriptions = {
    "research_problem_triage": "Research problem triage — create an evidence-led work brief",
    "numeric_summary": "Numeric summary — compute descriptive statistics",
    "data_quality_profile": "Data quality profile — inspect rows for missingness and duplicates",
    "fasta_validate": "FASTA validation — syntax, alphabet, length, and basic GC screening",
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
    "fasta_validate": {
        "fasta_text": ">DEMO-SEQ-001 synthetic training sequence\nACGTACGTNN\n>DEMO-PROTEIN-001 synthetic training sequence\nMKWVTFISLL\n"
    },
}
payload_text = st.text_area(
    "Input payload (JSON)",
    value=json.dumps(examples[task_type], indent=2),
    height=220,
    help="Only JSON data is accepted. The selected trusted handler determines how the payload is interpreted.",
)
synthetic_only_confirmed = st.checkbox(
    "I confirm this payload contains only synthetic/demo test data and no real or confidential research content."
)
max_attempts = st.number_input("Maximum attempts", min_value=1, max_value=5, value=2, step=1)

if st.button("Validate, submit and execute", type="primary"):
    try:
        if not synthetic_only_confirmed:
            raise ValueError("Confirm synthetic/demo-only input before submitting a workflow.")
        if len(payload_text.encode("utf-8")) > 1_000_000:
            raise ValueError("Input JSON exceeds the 1,000,000-byte interface limit.")
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
        if result:
            run_status = result.get("status", "unknown")
            run_result = result.get("result") or {}
            if run_status == "succeeded" and run_result.get("decision") == "READY_FOR_HUMAN_REVIEW":
                st.info(f"Validation completed; human QC review is still required: {run_id}")
            elif run_status == "succeeded":
                st.success(f"Run completed: {run_id}")
            elif run_status == "blocked":
                st.warning("Run blocked by a research QC/provenance gate. No scientific approval or downstream release is implied.")
            elif run_status == "failed":
                st.error(f"Run failed: {run_id}")
            elif run_status == "queued":
                st.info(f"Run queued for an explicit retry: {run_id}")
            elif run_status == "running":
                st.info(f"Run is still running: {run_id}")
            else:
                st.info(f"Run recorded with status {run_status}: {run_id}")
            st.write(f"**Status:** {run_status} · **Attempt:** {result['attempt']}")
            if result.get("result") is not None:
                st.markdown("#### Result")
                st.json(result["result"])
                if run_status == "blocked":
                    blockers = result["result"].get("blockers", [])
                    if blockers:
                        st.markdown("#### Why this run was blocked")
                        for blocker in blockers:
                            st.write(f"- {blocker}")
            elif result.get("error_message"):
                st.warning(result["error_message"])
                st.caption("A failed attempt may be queued for another explicit execution.")
        else:
            st.info(f"Run {run_id} was submitted, but no final result was returned.")
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        st.error(f"Input was rejected: {exc}")
    except Exception:
        st.error("The workflow could not complete. Inspect the run record and server logs; do not assume success.")

st.markdown("---")
st.subheader("Recovery controls")
st.caption(
    "Manual recovery only: use when a previous local process stopped while a run was marked running. "
    "Recovery can re-queue work, so first inspect whether the interrupted handler may already have produced "
    "side effects. Do not use this with concurrent or long-running workers unless real leases/heartbeats are configured."
)
if st.button("Inspect and recover interrupted runs older than 10 minutes"):
    try:
        recovered = runtime.recover_stale_runs(older_than_seconds=600)
        unresolved = [item for item in recovered if item.get("status") == "manual_review_required"]
        recovered_count = len(recovered) - len(unresolved)
        if recovered_count:
            st.success(f"Recovered {recovered_count} stale run(s).")
        if unresolved:
            st.warning(f"{len(unresolved)} run(s) require manual review; they were not changed or retried.")
        if recovered:
            st.dataframe(recovered, use_container_width=True, hide_index=True)
            if recovered_count:
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
            if selected_run["status"] == "blocked":
                st.warning("Blocked means the requested research action failed its domain gate; it is not a technical execution failure and cannot be treated as QC approval.")
                stored_result = selected_run.get("result") or {}
                for blocker in stored_result.get("blockers", []):
                    st.write(f"- {blocker}")
            elif selected_run["status"] == "failed":
                st.error("Technical execution failed. Inspect the recorded error and event history before retrying.")
            elif selected_run["status"] == "succeeded":
                selected_result = selected_run.get("result") or {}
                if selected_result.get("decision") == "READY_FOR_HUMAN_REVIEW":
                    st.info("Validation passed, but QC approval has NOT been granted. A qualified human reviewer must inspect the evidence and record the decision.")
                else:
                    st.success("Execution completed. This status alone does not certify scientific validity or QC approval.")
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
                if not synthetic_only_confirmed:
                    st.info("Confirm synthetic/demo-only data above to enable Notion handoff.")
                elif st.button("Send execution record to Notion", key="handoff_selected_run"):
                    try:
                        delivery = sync_run_to_notion(selected_run, ledger_database=str(db_path))
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
