# Batch 37 — Release Readiness and Operational Proof

Status: planned controls; not evidence of production readiness.

## Goal
Move beyond unit-test confidence by producing repeatable, reviewable operational evidence before merging or publishing the Workflow Execution Center.

## Gate A — Non-mutating preflight
- Verify operator password policy without printing secret values.
- Verify Fernet key validity without printing the key.
- Verify configured runtime database path and filesystem read/write expectations.
- Run SQLite integrity checks against a staging copy, not the active production database.
- Confirm required schema and encryption markers on synthetic fixtures.
- Return non-zero when required configuration is absent or invalid.

## Gate B — Storage and recovery
- Create a SQLite-aware backup from a quiesced staging instance.
- Restore into a separate isolated path with restricted filesystem permissions.
- Verify the restored database integrity, run count, ordered event history, and payload readback with the authorized key.
- Prove wrong-key startup fails closed and does not mutate the restored copy.
- Exercise key rotation and confirm both new-key readback and protected old-key backup recovery.

## Gate C — Runtime lifecycle
- Submit a deterministic synthetic run.
- Verify queued, running, and terminal event order and state consistency.
- Restart the app against the same durable staging database and confirm the run is still readable.
- Exercise a handler failure, bounded retry, stale-run recovery, and oversized input/result rejection.
- Verify terminal runs cannot be rewritten and retries create distinct run IDs.

## Gate D — Notion handoff
- Use only a disposable staging Analysis Runs database and least-privileged integration.
- Confirm schema validation fails closed.
- Deliver a completed synthetic run and fetch the created page independently.
- Repeat sequential and same-host concurrent delivery; verify manifest reconciliation and record count.
- Simulate ambiguous create outcomes and transient schema-read failures.
- Record that local SQLite coordination is not a distributed lock and SQLite/Notion cannot share one atomic transaction.

## Gate E — Security and deployment boundaries
- Confirm individual identity, role authorization, MFA, durable global rate limiting, and audit attribution are either implemented or formally accepted as release blockers.
- Confirm durable storage and single-writer/worker topology for the target hosting environment.
- Review plaintext SQLite metadata and event digests; application-level payload encryption is not whole-database encryption.
- Define backup retention, deletion, recovery ownership, and secret rotation procedures.
- Verify no real research, personal, confidential, or regulated data is accepted by the synthetic-only workflow console.

## Evidence record
For each check capture test ID, exact commit SHA, environment, tester role, timestamp, expected and actual outcome, sanitized evidence URL, defect IDs, and retest result. Do not store secrets, real research payloads, or sensitive logs in evidence records.

## Release rule
Keep the release on HOLD until mandatory staging evidence is complete, security ownership accepts the identity/authorization model, and scientific QC/reproducibility are reviewed by a human. Passing CI alone is not release approval.
