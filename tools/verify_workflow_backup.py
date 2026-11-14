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

from modules.workflow_store import IdempotencyConflict, _decode_stored_event


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
        required_run_columns = {
            "run_id", "status", "input_json", "result_json", "error_message",
            "attempt", "max_attempts", "claimed_at", "synthetic_only_confirmed",
            "result_integrity",
        }
        if not required_run_columns.issubset(run_columns):
            raise BackupVerificationError(
                "workflow_runs schema is incomplete or missing required integrity fields"
            )

        invalid_integrity_count = int(connection.execute(
            """
            SELECT COUNT(*) FROM workflow_runs
            WHERE result_integrity IS NULL
               OR result_integrity NOT IN ('not_applicable', 'verified', 'legacy_unverified')
            """
        ).fetchone()[0])
        if invalid_integrity_count:
            raise BackupVerificationError(
                "backup contains invalid workflow result-integrity markers"
            )
        result_integrity_counts = {
            row["result_integrity"]: int(row["count"])
            for row in connection.execute(
                """
                SELECT result_integrity, COUNT(*) AS count
                FROM workflow_runs GROUP BY result_integrity
                """
            ).fetchall()
        }

        # Mirror the runtime's row-level contract without decrypting payloads.
        # Historical rows retain the additive legacy_unverified marker; it is
        # accepted where the runtime can safely classify the row on read.
        invalid_run_state_count = int(connection.execute(
            """
            SELECT COUNT(*) FROM workflow_runs
            WHERE status NOT IN ('queued', 'running', 'succeeded', 'failed')
               OR input_json IS NULL
               OR typeof(attempt) != 'integer'
               OR typeof(max_attempts) != 'integer'
               OR max_attempts < 1 OR max_attempts > 10
               OR attempt < 0 OR attempt > max_attempts
               OR typeof(synthetic_only_confirmed) != 'integer'
               OR synthetic_only_confirmed NOT IN (0, 1)
               OR (status = 'running' AND (
                    claimed_at IS NULL OR typeof(claimed_at) != 'text' OR TRIM(claimed_at) = ''
               ))
               OR (status != 'running' AND claimed_at IS NOT NULL)
               OR (status = 'succeeded' AND (
                    (result_json IS NULL AND result_integrity != 'legacy_unverified')
                    OR (result_json IS NOT NULL AND result_integrity = 'not_applicable')
                    OR error_message IS NOT NULL
               ))
               OR (status != 'succeeded' AND (
                    result_json IS NOT NULL OR result_integrity = 'verified'
               ))
               OR (status = 'failed' AND error_message IS NULL)
            """
        ).fetchone()[0])
        if invalid_run_state_count:
            raise BackupVerificationError(
                "backup contains inconsistent workflow run state or result-integrity metadata"
            )

        required_event_columns = {
            "sequence", "event_id", "idempotency_key", "workflow_id", "run_id",
            "event_type", "stage", "status", "occurred_at", "payload_digest",
            "event_json", "stored_at",
        }
        if not required_event_columns.issubset(event_columns):
            raise BackupVerificationError("workflow_events schema is incomplete")

        event_rows = connection.execute(
            "SELECT * FROM workflow_events ORDER BY sequence"
        ).fetchall()
        for event_row in event_rows:
            if (
                type(event_row["sequence"]) is not int
                or event_row["sequence"] < 1
                or not isinstance(event_row["stored_at"], str)
                or not event_row["stored_at"].strip()
            ):
                raise BackupVerificationError("backup contains invalid workflow event metadata")
            try:
                decoded_event = _decode_stored_event(event_row)
            except IdempotencyConflict as exc:
                raise BackupVerificationError(
                    "backup contains invalid workflow event records"
                ) from exc
            canonical_event_json = json.dumps(
                decoded_event.to_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            if event_row["event_json"] != canonical_event_json:
                raise BackupVerificationError(
                    "backup contains non-canonical workflow event JSON"
                )

        run_count = int(connection.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0])
        event_count = len(event_rows)
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
            "result_integrity_counts": result_integrity_counts,
            "encrypted_payload_field_counts": encrypted_counts,
            "verification_scope": [
                "read-only SQLite integrity check",
                "required workflow table and column checks",
                "workflow run status, attempt, claim, attestation, and result-integrity consistency",
                "workflow event contract, canonical JSON, and indexed-column consistency",
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
