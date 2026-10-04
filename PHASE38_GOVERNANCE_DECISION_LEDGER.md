# Phase 38 — Governance Decision Ledger Integration

## Purpose

Phase 38 connects important application decision boundaries to the Phase 36 governed audit-event capture layer. The objective is to ensure that an already-made evaluation, review or lifecycle decision can be independently represented in the append-only audit ledger.

The ledger is an accountability record. It is not a decision-maker and does not establish environmental truth, environmental impact, regulatory status, NEMA authorization, production approval, enforcement authority or emergency-response authority.

## Implemented

- `nema_agora/governance_decision_ledger.py`: reusable, metadata-only decision-boundary adapter.
- `tests/nema_agora/test_governance_decision_ledger.py`: idempotency, allowlist, conflict and privacy-boundary tests.
- `nema_agora/service.py`: actual capture hooks after persisted Phase 13 evaluation, Phase 19 human review, and Phase 19 human lifecycle decisions.
- `pages/46_NEMA_AGORA_GOVERNANCE_DECISION_LEDGER.py`: authenticated read-only ledger view.
- Phase 36 checkpoint and publication-gate hooks remain active.
- Backup-verification and access-denial event types remain available through the same adapter for explicit workflow integration.

## Decision mappings

| Workflow | Event | Decision mapping |
|---|---|---|
| Evaluation completed | EVALUATION_COMPLETED | HUMAN_REVIEW_REQUIRED |
| Human review | REVIEW_DECISION_RECORDED | CONFIRMED_USEFUL→APPROVE; UNSAFE→REJECT; NEEDS_CORRECTION→HUMAN_REVIEW_REQUIRED; NOT_APPLICABLE→DEFER |
| Human lifecycle decision | MODEL_LIFECYCLE_DECIDED | RETAIN→APPROVE; SUSPEND→REJECT; REVIEW/RE_ADMIT_REQUIRED→DEFER |
| Backup verification | BACKUP_VERIFICATION_COMPLETED | Available for explicit recovery-workflow hook |
| Access denial | ACCESS_POLICY_DENIED | Available for explicit access-boundary hook |

The mappings normalize domain-specific decisions into the constrained Phase 36 audit vocabulary. The original workflow decision remains in its source record; the audit event is a governed summary, not a replacement.

## Integrity and failure behavior

- Stable event identity is deterministic from decision kind and explicit artifact/decision metadata.
- Repeated identical capture is idempotent.
- Reuse with changed content fails with `EVENT_ID_CONFLICT`.
- Payloads remain metadata-only and inherit Phase 36 privacy/key/type restrictions.
- Ledger verification remains fail-closed.
- The adapter never changes source decision state.

## Current integration boundary

Actual application hooks are connected for evaluation completion, human shadow review, and human lifecycle decisions. Phase 36 already captures checkpoint creation and publication-gate evaluation. Backup verification and access denial are supported event types but are not claimed as automatically captured until their concrete workflow boundaries are explicitly wired.

## Important limitation

The source decision store and audit ledger are separate SQLite write operations. The current implementation does not provide a distributed transaction across both stores. A failure after source persistence can therefore require controlled reconciliation; this is intentionally not hidden or silently repaired.

The audit ledger itself remains tamper-evident rather than tamper-proof against privileged database/file access. Independent checkpoint preservation remains necessary.

## Next gate

**Phase 39 — Governance Reconciliation & Exception Handling**: detect decisions that exist in authoritative application stores but lack corresponding governed audit events, and surface them as reconciliation exceptions requiring human review rather than silently repairing history.
