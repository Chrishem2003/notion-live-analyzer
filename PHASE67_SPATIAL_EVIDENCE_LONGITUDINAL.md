# Phase 67 — Spatial Evidence Longitudinal Tracking

Preserves spatial evidence history across repeated observations and reviews without mutating historical records.

Each history record binds a case fingerprint, candidate identity, AOI/grid identity, observation time, sequence number, review outcome and Phase 66 provenance. A previous-record fingerprint creates an explicit append-only chain.

Invalid case identity, fingerprints, spatial identity, timestamps or sequence values fail closed. Timeline construction detects duplicate records and broken predecessor links.

This is evidence history, not environmental truth. It does not infer legality, regulatory status, NEMA authorization, enforcement or emergency action.

Completion gate: GitHub Actions must verify focused tests, compilation and Streamlit startup before Phase 67 is CI-green.

Next gate: Phase 68 — Spatial Evidence Storage & Query Layer.
