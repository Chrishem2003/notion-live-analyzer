# Phase 36 — Automated Audit Evidence Capture

## Purpose
Provide a governed service for recording defined application events in the Phase 34 hash-chained ledger. This phase establishes the capture contract and a controlled authenticated page; it does not claim every existing workflow is automatically instrumented.

## Implemented
- `nema_agora/audit_events.py`: allowlisted event types, stable event IDs, deterministic ledger entry IDs, duplicate suppression, conflict detection, metadata key allowlist, bounded values and numeric count summaries.
- `tests/nema_agora/test_audit_events.py`: tests for successful capture, idempotent retry, rejected event types, rejected unapproved/sensitive fields, conflicting reuse of an event ID, and missing actor identity.
- `pages/44_NEMA_AGORA_AUDIT_EVENT_CAPTURE.py`: authenticated, human-triggered capture page using the authenticated principal as actor.
- `pages/42_NEMA_AGORA_AUDIT_LEDGER.py` now captures a checkpoint-created event after a checkpoint is saved.
- `pages/40_NEMA_AGORA_PUBLICATION_CONTROL.py` now captures a metadata-only publication-gate decision after the gate is evaluated.
- The capture page shows ledger verification after capture and permits downloading a verification report.

## Event contract
Current allowlisted types:
- `EVALUATION_COMPLETED`
- `REVIEW_DECISION_RECORDED`
- `CHECKPOINT_CREATED`
- `PUBLICATION_GATE_DECIDED`
- `MODEL_LIFECYCLE_DECIDED`
- `BACKUP_VERIFICATION_COMPLETED`
- `ACCESS_POLICY_DENIED`

Payloads are metadata-only and use allowlisted fields. Raw observations, free-text narratives, contact details, credentials and personal data must not be recorded. Stable event IDs make retries idempotent; reusing an event ID with changed content or actor is a conflict.

## Integration boundary
The capture page records events when a permitted human submits the form. Two real decision boundaries are instrumented in this phase: checkpoint creation and publication-gate evaluation. Other evaluation, review, model-governance, access-control and backup workflows are not automatically recorded until they call `AuditEventCapture.record` at their actual decision boundaries. Do not represent this as complete system-wide instrumentation.

## Limitations
- The actor comes from the authenticated principal, but authorization still depends on the trusted identity-provider and role-binding configuration.
- SQLite hash chaining and triggers are tamper-evident controls, not tamper-proof storage.
- This is audit traceability, not environmental truth, impact, regulatory status, NEMA authorization or production approval.
