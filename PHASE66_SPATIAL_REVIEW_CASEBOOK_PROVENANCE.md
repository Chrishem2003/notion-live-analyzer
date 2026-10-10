# Phase 66 — Spatial Review Evidence Casebook & Provenance

Phase 66 packages exact Phase 63 queue artifacts and Phase 64 human-review audit evidence into deterministic case records bound to the Phase 65 reconciliation snapshot.

## Controls
Each case binds the queue fingerprint, source candidate fingerprint, human-review event fingerprint, queue fingerprint carried by the review event, reviewer identity/role, human outcome and exact Phase 65 reconciliation fingerprint.

The Phase 64 audit-event fingerprint is recomputed. Tampering, identity mismatch, queue-binding mismatch and non-unique review evidence fail closed.

## States
CASEBOOK_READY means valid evidence cases were packaged.
NO_CASES means no case was produced without an integrity finding.
CONTROL_REQUIRED means evidence integrity or provenance checks failed.

The casebook is deterministic and read-only.

## Governance boundary
A casebook is evidence packaging. A CONFIRMED_CHANGE human-review outcome remains a human evidence record and is not converted into environmental truth or a regulatory finding. No NEMA authorization, official reporting, enforcement, emergency response or production approval is created.

## Completion gate
GitHub Actions must verify Phase 66 focused tests, compilation and Streamlit startup before Phase 66 is declared CI-green. No green status is inferred from source inspection.

## Next gate
Phase 67 — Spatial Evidence Longitudinal Tracking: preserve case history across repeated observations and reviews without mutating historical evidence.
