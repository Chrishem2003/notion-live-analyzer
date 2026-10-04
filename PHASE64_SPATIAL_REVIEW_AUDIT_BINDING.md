# Phase 64 — Spatial Change Human Review & Audit Binding

Phase 64 creates the human decision boundary after the persistent Phase 63 analytical queue.

## Flow
Phase 62 priority → Phase 63 immutable queue item → explicit authorized human review → append-only audit event.

## Outcomes
- CONFIRMED_CHANGE
- NOT_CONFIRMED
- INSUFFICIENT_EVIDENCE
- ESCALATED

These are review outcomes about the analytical evidence record, not findings of illegality or regulatory violations.

## Controls
- Only reviewer/coordinator/admin roles may record outcomes.
- Queue item must still be QUEUED.
- Candidate and immutable queue fingerprint are bound into the audit event.
- One review outcome per queue item.
- Deterministic review-event ID and event fingerprint.
- SQLite UPDATE/DELETE triggers enforce append-only audit history.
- No autonomous queue-state transition occurs.
- Environmental/regulatory/enforcement fields remain null.

## Governance boundary
Human review is explicit and auditable, but this phase does not authorize NEMA action, enforcement, emergency response, production approval, or autonomous environmental/regulatory decisions.

## Completion gate
GitHub Actions must verify Phase 64 tests, compilation and Streamlit startup before Phase 64 is declared CI-green.

## Next gate
Phase 65 — Spatial Review Reconciliation & Evidence Integrity: reconcile queue items against human-review audit events and detect missing, orphaned, duplicate or fingerprint-mismatched review records.
