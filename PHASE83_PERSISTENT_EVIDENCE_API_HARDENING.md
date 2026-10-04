# Phase 83 — Persistent Evidence Query API Hardening

Hardens the spatial evidence query surface against invalid limits and unsupported filters and provides persistent SQLite-backed retrieval with deterministic ordering and temporal filtering.

Supported filters: AOI, scene, candidate, review status, observed-from, observed-to. Limit is 1–500. Persistent repository failures fail closed as CONTROL_REQUIRED.

This remains read-only prototype infrastructure. It does not expose public production access, live environmental providers, regulatory conclusions, enforcement, or emergency authority.
