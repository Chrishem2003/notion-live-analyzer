# Phase 106 — Governance Drift Review Audit Reconciliation & Evidence Integrity

## Purpose

Reconcile Phase 101 drift events, Phase 103 review queue items, Phase 104
human-review audits and Phase 105 persistent registry rows as one read-only
evidence chain.

## Checks

- Missing drift events referenced by queued reviews.
- Unqueued drift events.
- Duplicate or invalid record identities.
- Drift fingerprint and baseline/current snapshot mismatches.
- Orphan human-review audits.
- Audit-to-queue binding mismatches.
- Invalid or tampered Phase 104 audit fingerprints and deterministic audit IDs.
- Missing persistent audit rows.
- Orphan persisted audit rows.
- Persisted field/policy mismatches.

Any finding produces `CONTROL_REQUIRED`; a clean chain produces `RECONCILED`.
Findings are deterministic and fingerprinted. The reconciler does not repair,
delete, rewrite, or mutate source records.

## Governance boundary

Reconciliation is evidence integrity control, not environmental truth, legal
status, regulatory approval, NEMA endorsement, enforcement authority, emergency
response, or production authorization. Human review and lifecycle governance
remain separate.

## Verification gate

Only call this phase CI-green after a visible GitHub Actions run passes the
focused tests, Python compilation and Streamlit smoke checks on the current PR
head. Source commits alone do not constitute successful verification.

## Next gate

Phase 107 — Governance Drift Review Reconciliation Snapshot & History.
