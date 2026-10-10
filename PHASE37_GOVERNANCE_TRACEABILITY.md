# Phase 37 — End-to-End Governance Traceability

## Purpose

Phase 37 verifies that a governed activity can be followed through explicit identifiers from an originating event, through provenance and evidence lineage, into a research report, a human publication decision, and the corresponding governed audit record.

This is an artifact/workflow integrity control. It does **not** establish environmental truth, environmental impact, regulatory status, NEMA authorization, production approval, enforcement authority, emergency-response authority, or autonomous decision authority.

## Implemented

- `nema_agora/governance_traceability.py`
- `tests/nema_agora/test_governance_traceability.py`
- `pages/45_NEMA_AGORA_GOVERNANCE_TRACEABILITY.py`
- Explicit origin-event, provenance, graph, report, publication-decision and audit-entry bindings.
- Duplicate and ambiguous identifier detection.
- Graph edge and orphan/missing-parent checks.
- Report-to-graph binding checks.
- Claim-to-provenance and claim-to-graph-node checks.
- Human publication decision binding and sign-off checks.
- Audit-ledger verification as a fail-closed prerequisite.
- Required publication-gate audit-event coverage.
- Deterministic trace fingerprint and structured error codes.
- Read-only JSON bundle inspection page.

## Traceability rule

The validator does not infer relationships from filenames, labels, timestamps, ordering, or approximate text. Each relationship must be represented by an explicit identifier or exact structured field.

A valid result is `TRACEABLE`. Any broken required reference results in `CONTROL_REQUIRED`.

## Audit coverage boundary

Phase 36 currently connects actual capture hooks at checkpoint creation and publication-gate evaluation. It does not yet automatically instrument every origin/evaluation/review workflow. Phase 37 therefore reports missing origin audit coverage as a warning rather than claiming that Phase 36 captures it automatically. A required publication-gate audit event remains mandatory.

## Expected bundle

A trace bundle contains:

- `origin_event`
- `provenance_records`
- `graph`
- `report`
- `publication_decision`
- `audit_entries`
- `ledger_verification`

The page does not mutate these artifacts.

## Failure semantics

The validator fails closed for:

- invalid or ambiguous origin identifiers;
- duplicate provenance or graph identifiers;
- broken graph edges or incomplete lineage;
- report/graph binding mismatch;
- missing or unresolved claim sources;
- missing claim graph nodes or limitations;
- publication-decision/report mismatch;
- approval with failed gates or without human sign-off;
- failed audit-ledger verification;
- missing or ambiguous publication-gate audit event;
- publication audit status/decision mismatch.

## Limitations

Traceability is only as strong as the supplied artifacts and the protection of the audit ledger/checkpoints. It is not a cryptographic signature system, and it does not make the local ledger tamper-proof against a privileged database/file operator.
