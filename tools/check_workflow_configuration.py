"""Non-mutating configuration preflight for the workflow execution console."""
from __future__ import annotations
import os
import sys
from modules.workflow_access import WorkflowAccessConfigurationError, load_workflow_password
from modules.workflow_storage import WorkflowStorageConfigurationError, load_workflow_storage_key


def main() -> int:
    failures = 0
    try:
        load_workflow_password()
        print("[PASS] Operator password configured (value hidden).")
    except WorkflowAccessConfigurationError:
        print("[FAIL] Operator password missing or does not meet policy.")
        failures += 1
    try:
        load_workflow_storage_key()
        print("[PASS] Payload encryption key valid (value hidden).")
    except WorkflowStorageConfigurationError:
        print("[FAIL] Payload encryption key missing or invalid.")
        failures += 1
    path = os.environ.get("WORKFLOW_RUNTIME_DB", ".streamlit/workflow_runtime.sqlite3")
    print(f"[INFO] Runtime database path configured: {path}")
    print("[INFO] This preflight does not test staging delivery, identity, authorization, or recovery.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
