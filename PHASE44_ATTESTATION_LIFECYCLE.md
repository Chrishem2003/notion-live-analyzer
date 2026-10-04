# Phase 44 — Attestation Lifecycle Governance

## Purpose

Phase 44 introduces an explicit human decision lifecycle over immutable Phase
43 governance attestations. The system derives current lifecycle state from
the exact current integrity snapshot and an append-only decision ledger.

## Lifecycle

- PENDING_REVIEW — an exact attestation exists but no lifecycle decision has been recorded.
- ACTIVE — a second authorized human approved the exact current attestation and it has not expired.
- REJECTED — a second authorized human explicitly rejected it.
- REVOKED — an authorized human explicitly revoked it.
- EXPIRED — an approval passed its explicit expiry timestamp.
- SUPERSEDED — an authorized human recorded a replacement attestation.
- STALE — the attestation no longer matches the current integrity snapshot.
- CONTROL_REQUIRED — current integrity/provenance failed or active-attestation conflict exists.

## Separation of duties

Approval and rejection require the lifecycle reviewer to be different from
the original attester. This is enforced in the lifecycle registry, not merely
in the UI.

## Immutability

Phase 43 attestation rows are never updated or deleted. Phase 44 lifecycle
decisions are stored in a separate append-only SQLite table with UPDATE and
DELETE triggers that fail closed.

## Evidence binding

A lifecycle evaluation requires exact equality for:
1. reconciliation fingerprint;
2. evidence registry fingerprint;
3. provenance fingerprint;
4. effective Phase 43 attestation state.

A changed evidence/provenance snapshot therefore makes the historical
attestation stale for current lifecycle purposes.

## Expiration

Approval expiry is explicit and ISO-8601. Evaluation accepts an explicit
now value so expiration tests are deterministic and reproducible.

## Conflict control

Two or more ACTIVE attestations bound to the same exact snapshot produce
CONTROL_REQUIRED. No automatic selection or winner is inferred.

## Governance boundary

Phase 44 is an engineering/research governance control. It does not confer
NEMA endorsement, regulatory authority, enforcement authority, emergency
response authority, official reporting permission, production approval, or
environmental truth.

## Verification

The CI workflow runs the complete tests/nema_agora suite, compiles the
NEMA-AGORA modules/pages, and smoke-tests Streamlit startup.
