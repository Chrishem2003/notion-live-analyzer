# Phase 92 — API Audit Lifecycle Decision Ledger

Adds a separate human-governed, append-only lifecycle decision ledger.

Supported decisions: RECONCILE, REQUEST_REVIEW, RETAIN, EXPIRE. Decisions require coordinator/admin identity and an exact binding to the reconciled API audit snapshot and lifecycle snapshot.

Evaluation remains distinct from authority: Phase 91 evaluates retention state; Phase 92 records an authorized human lifecycle decision. The ledger is immutable and evidence-only; it does not establish environmental truth, regulatory status, enforcement authority, or NEMA authorization.
