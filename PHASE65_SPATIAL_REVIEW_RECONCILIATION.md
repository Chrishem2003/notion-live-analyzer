# Phase 65 — Spatial Review Reconciliation & Evidence Integrity

## Purpose

Phase 65 reconciles the immutable Phase 63 spatial-change review queue with the immutable Phase 64 human-review audit evidence.

Flow:

**Phase 63 Queue ↕ Phase 64 Human Review Audit → Reconciliation Engine → Evidence Integrity State**

## Reconciliation checks

The read-only reconciler detects:

- MISSING_REVIEW — a queued review item has no human-review audit event.
- ORPHAN_REVIEW — an audit event references no queue item.
- DUPLICATE_REVIEW — more than one audit event references the same review item.
- REVIEW_FINGERPRINT_MISMATCH — the audit event does not bind to the exact queue-record fingerprint.
- STALE_REVIEW — the queue record is no longer in the Phase 64 QUEUED state.
- REVIEW_IDENTITY_MISMATCH — candidate identity in the audit event differs from the queue record.

All findings are deterministic and carry their own fingerprints.

## States

- RECONCILED — every queue item has exactly one matching human-review audit event and no integrity finding is present.
- CONTROL_REQUIRED — any missing, orphaned, duplicated, stale or mismatched evidence is present.

The reconciler never repairs source records and never changes queue or audit state.

## Determinism

The complete reconciliation result receives a SHA-256 reconciliation_fingerprint using canonical JSON serialization. Findings are sorted deterministically.

## Governance boundary

This phase is an evidence-integrity control. A reconciled record does not establish environmental truth, wetland loss, deforestation, illegality, regulatory status, NEMA authorization, enforcement action, emergency response or production approval.

Human review outcomes remain human evidence records. This phase does not execute or reinterpret them.

## Completion gate

GitHub Actions must verify Phase 65 focused tests, compilation and Streamlit startup before Phase 65 is declared CI-green. No green status is inferred from source inspection.

## Next gate

Phase 66 — Spatial Review Evidence Casebook & Provenance: package reconciled review evidence with exact queue and audit artifacts for human investigation and downstream evidence tracking.
