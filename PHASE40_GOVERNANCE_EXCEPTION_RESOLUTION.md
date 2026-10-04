# NEMA-AGORA Phase 40 — Controlled Governance Exception Resolution

## Purpose
Phase 40 adds an explicit human workflow for resolving Phase 39 reconciliation exceptions without rewriting history.

## Resolution model
A resolution is an append-only GOVERNANCE_EXCEPTION_RESOLVED audit event containing controlled metadata: exception code, decision kind, artifact ID, outcome, reason code, reconciliation fingerprint, status, source module, actor role and policy version.

## Allowed outcomes
ACKNOWLEDGED; CORRECTED_AT_SOURCE; DUPLICATE_CONFIRMED; FALSE_POSITIVE; ESCALATED.

CORRECTED_AT_SOURCE records a human assertion about correction at the authoritative source; this page does not mutate that source.

## Safety
Historical audit events are never edited or deleted. Resolution is human-governed and authenticated. This is an audit-control mechanism, not regulatory approval, NEMA authorization, environmental truth, enforcement authority, emergency response, or production approval.

## Next gate
Phase 41 should reconcile resolution events back to open exceptions and introduce explicit closure rules and evidence requirements, without allowing silent history repair.
