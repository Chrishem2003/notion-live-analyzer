# Phase 68 — Spatial Evidence Storage & Query Layer

Phase 68 adds persistent append-only storage for Phase 67 longitudinal evidence records.

## Controls
Records require stable identifiers and valid SHA-256 fingerprints. A unique case/sequence index prevents duplicate sequence positions. SQLite UPDATE and DELETE triggers make stored history append-only.

## Query boundary
Records can be retrieved by case ID in deterministic chronological order. Storage preserves case, candidate, time, sequence, predecessor fingerprint, spatial identity, review outcome, provenance and record fingerprint.

## Governance
Storage is evidence infrastructure only. It does not create environmental truth, regulatory conclusions, violation findings, enforcement actions or emergency decisions.

## Completion gate
GitHub Actions must verify focused tests, compilation and Streamlit startup before Phase 68 is CI-green.

## Next gate
Phase 69 — AOI Registry & Environmental Asset Catalog.
