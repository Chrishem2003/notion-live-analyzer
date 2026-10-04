# Phase 105 — Persistent Governance Drift Review Audit Registry

## Purpose

Persist the human-review audit emitted by Phase 104 in an append-only SQLite
registry so that governance drift review evidence survives process restarts and
can be reconciled in a later phase.

## Contract

- Policy version: `phase105-v1`.
- Only Phase 104 review-audit records are accepted.
- Review IDs, drift IDs, snapshot IDs and audit IDs use the stable-ID contract.
- Drift and audit fingerprints must be valid SHA-256 values.
- The registry recomputes the exact Phase 104 audit fingerprint from the bound
  review, drift, snapshot, reviewer, outcome and timestamp fields.
- The deterministic audit ID must match that fingerprint.
- Duplicate review IDs, audit IDs or fingerprints are rejected.
- SQLite UPDATE and DELETE operations are blocked by database triggers.
- Listing is deterministic and bounded.

## Governance boundary

This registry stores evidence. It does **not**:
- approve or reject environmental activity;
- declare environmental truth or a violation;
- execute enforcement, emergency dispatch or regulatory action;
- change drift, snapshot or governance lifecycle state;
- imply NEMA endorsement, authorization or production readiness.

Human review remains authoritative for any governance decision. Phase 105 only
makes the Phase 104 audit evidence durable.

## Verification

The phase should be considered CI-green only after GitHub Actions visibly
passes the focused NEMA-AGORA tests, compilation and Streamlit smoke checks for
the current head. Source inspection alone is not a green result.

## Next gate

**Phase 106 — Governance Drift Review Audit Reconciliation & Evidence Integrity**

The next phase should reconcile queue items, drift events, Phase 104 human-review
audits and the persistent Phase 105 registry, detecting orphan, duplicate,
identity, snapshot and fingerprint mismatches.
