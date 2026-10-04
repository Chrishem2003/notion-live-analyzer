# Phase 161 — Governed Evidence Case Pipeline

Phase 161 connects the first product primitive into a small end-to-end workflow:
assembly, deterministic validation, human review, and export preparation.

The pipeline deliberately does not invent observations, infer regulatory violations,
submit to NEMA, dispatch emergencies, enforce rules, or make environmental-truth
claims. Export is a packaging state only.

## Contract
1. assemble_case creates a READY_FOR_REVIEW case.
2. validate_evidence_case records deterministic integrity and governance controls.
3. review_case requires an identified human reviewer and permitted decision.
4. export_case requires REVIEWED state and never performs external submission.

## Next
Add adapters to existing observation/quality records only after their real schemas
are inspected. Preserve existing governance boundaries and avoid duplicating
registry-specific lifecycle machinery.
