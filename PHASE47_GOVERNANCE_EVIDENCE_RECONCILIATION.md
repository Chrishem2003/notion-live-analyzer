# Phase 47 — Governance Evidence Reconciliation

Cross-layer consistency control for Phase 43–46 evidence. It compares attestations, lifecycle states, provenance bindings and the live governance snapshot.

The reconciliation is deterministic and fail-closed. It reports orphan records, duplicate bindings, lifecycle identity mismatches, snapshot mismatches, provenance failures and active attestations without provenance bindings.

RECONCILED means the supplied evidence layers are internally consistent under this policy. CONTROL_REQUIRED means a human must investigate. Neither state is NEMA authorization, regulatory approval, environmental truth, production approval, enforcement authority or emergency authorization.

The reconciler is read-only and cannot create, modify, delete or repair governance records.
