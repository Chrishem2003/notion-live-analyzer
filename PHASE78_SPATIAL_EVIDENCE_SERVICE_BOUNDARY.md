# Phase 78 — Spatial Evidence Service Boundary / API Adapter

Defines the service-facing request/response contract over the Phase 77 spatial evidence query surface. Supported operations are QUERY, GET_BY_ID, LIST_AOI, LIST_SCENES, and LIST_CHANGES.

The adapter is read-only and authorization-aware. It does not create evidence, mutate records, connect directly to a live provider, assert environmental truth, determine regulatory status, identify violations, authorize enforcement, or dispatch emergencies.

The contract is suitable for a future FastAPI/Node gateway while remaining dependency-light for the prototype.
