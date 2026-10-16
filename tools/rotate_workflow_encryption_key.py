"""CLI for safe workflow payload key rotation.

Set WORKFLOW_RUNTIME_ENCRYPTION_KEY_OLD and WORKFLOW_RUNTIME_ENCRYPTION_KEY_NEW
in the trusted shell environment. Never pass secrets as command-line arguments.
"""
from __future__ import annotations

import argparse
import os
import sys

from modules.workflow_key_rotation import (
    WorkflowKeyRotationError,
    rotate_workflow_encryption_key,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Back up and rotate workflow payload encryption.")
    parser.add_argument(
        "--database",
        default=os.environ.get("WORKFLOW_RUNTIME_DB"),
        help="SQLite workflow database path (defaults to WORKFLOW_RUNTIME_DB).",
    )
    parser.add_argument(
        "--backup",
        required=True,
        help="New backup path. Existing files are never overwritten.",
    )
    args = parser.parse_args()

    old_key = os.environ.get("WORKFLOW_RUNTIME_ENCRYPTION_KEY_OLD")
    new_key = os.environ.get("WORKFLOW_RUNTIME_ENCRYPTION_KEY_NEW")
    if not args.database:
        parser.error("--database or WORKFLOW_RUNTIME_DB is required")
    if not old_key or not new_key:
        parser.error(
            "Set WORKFLOW_RUNTIME_ENCRYPTION_KEY_OLD and WORKFLOW_RUNTIME_ENCRYPTION_KEY_NEW "
            "in the trusted environment; never pass key values on the command line."
        )

    try:
        result = rotate_workflow_encryption_key(
            args.database, args.backup, old_key, new_key
        )
    except WorkflowKeyRotationError as exc:
        print(f"Key rotation failed safely: {exc}", file=sys.stderr)
        return 2

    print("Workflow encryption key rotation completed.")
    print(f"Rows updated: {result['rows_updated']}")
    print(f"Payload fields updated: {result['fields_updated']}")
    print(f"Backup created: {result['backup_path']}")
    print("Update WORKFLOW_RUNTIME_ENCRYPTION_KEY to the new key before restarting the app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
