"""Read-only structural and integrity verification for a workflow SQLite backup.

This command does not decrypt payloads, modify the backup, or prove that a
backup is recoverable with the currently held encryption key. Run it against
an isolated backup copy and follow with the staging restore/readback procedure.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


class BackupVerificationError(RuntimeError):
    """Raised when a backup fails structural or SQLite integrity checks."""


def verify_workflow_backup(path: str | Path) -> dict[str, Any]:
    """Verify a backup without opening it for writes or creating missing files."""
    backup = Path(path).expanduser().resolve()
    if not backup.is_file():
        raise BackupVerificationError("backup file does not exist or is not a regular file")

    # SQLite URI mode=ro ensures verification cannot create or mutate the target.
    uri = backup.as_uri() + "?mode=ro"
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=10)
        connection.row_factory = sqlite3.Row
        integrity = [row[0] for row in connection.execute("PRAGMA integrity_check").fetchall()]
        if integrity != ["ok"]:
            raise BackupVerificationError("SQLite integrity_check failed")

        tables = {
            row["name"] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        required_tables = {"workflow_runs", "workflow_events"}
        missing = sorted(required_tables - tables)
        if missing:
            raise BackupVerificationError(
                "backup is missing required workflow tables: " + ", ".join(missing)
            )

        run_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(workflow_runs)").fetchall()
        }
        event_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(workflow_events)").fetchall()
        }
        if not {"run_id", "input_json", "result_json", "error_message"}.issubset(run_columns):
            raise BackupVerificationError("workflow_runs schema is incomplete")
        if not {"event_id", "idempotency_key", "workflow_id", "run_id", "status"}.issubset(event_columns):
            raise BackupVerificationError("workflow_events schema is incomplete")

        run_count = int(connection.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0])
        event_count = int(connection.execute("SELECT COUNT(*) FROM workflow_events").fetchone()[0])
        encrypted_counts: dict[str, int] = {}
        for column in ("input_json", "result_json", "error_message"):
            encrypted_counts[column] = int(connection.execute(
                f"SELECT COUNT(*) FROM workflow_runs WHERE {column} LIKE 'enc:v1:%'"
            ).fetchone()[0])
        return {
            "verified": True,
            "backup_path": str(backup),
            "sqlite_integrity": "ok",
            "workflow_runs": run_count,
            "workflow_events": event_count,
            "encrypted_payload_field_counts": encrypted_counts,
            "verification_scope": [
                "read-only SQLite integrity check",
                "required workflow table and column checks",
                "record counts and versioned-encryption prefix counts",
            ],
            "limitations": [
                "does not decrypt payloads or verify encryption-key custody",
                "does not compare counts with a source database snapshot",
                "does not replace an isolated restore and application readback test",
            ],
        }
    except BackupVerificationError:
        raise
    except (sqlite3.Error, OSError, ValueError) as exc:
        raise BackupVerificationError("backup could not be verified safely") from exc
    finally:
        if connection is not None:
            connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only structural and integrity check for a workflow SQLite backup."
    )
    parser.add_argument("backup", help="Existing SQLite backup file to verify")
    args = parser.parse_args()
    try:
        result = verify_workflow_backup(args.backup)
    except BackupVerificationError as exc:
        print(json.dumps({"verified": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
