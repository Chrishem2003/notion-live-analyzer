# NEMA-AGORA Phase 39 — Governance Reconciliation & Exception Handling

## Purpose
Phase 39 detects divergence between authoritative application decision stores and the governed audit ledger. It converts the Phase 38 separate-write limitation into an explicit reconciliation control.

## Compared decision boundaries
- Evaluation completion -> EVALUATION_COMPLETED
- Human shadow review -> REVIEW_DECISION_RECORDED
- Model lifecycle decision -> MODEL_LIFECYCLE_DECIDED

## Exceptions
The engine detects missing audit events, orphan audit events, duplicate source decisions, ambiguous audit coverage, actor mismatch, decision/status mismatch, source-module mismatch, invalid source records, and invalid ledger verification.

## Safety and governance
Reconciliation is read-only. It never silently creates, edits, deletes, or rewrites historical audit events. Critical discrepancies return CONTROL_REQUIRED and require human investigation.

This is an audit-integrity control, not NEMA authorization, regulatory approval, environmental truth, enforcement authority, emergency response, or production approval.

## Determinism
The result is represented by a deterministic reconciliation fingerprint derived from policy version, counts, status, and normalized exception records.

## Current boundary
Phase 39 reconciles the authoritative evaluation, human-review, and lifecycle stores. Publication-gate and checkpoint events remain covered by earlier phases and can be added to later reconciliation scopes once their authoritative stores are formally bound.

## Limitation
The reconciliation engine reads bounded store lists and the audit ledger verifier is bounded to 5,000 entries. Above those limits the existing ledger verifier fails closed rather than claiming partial integrity.
