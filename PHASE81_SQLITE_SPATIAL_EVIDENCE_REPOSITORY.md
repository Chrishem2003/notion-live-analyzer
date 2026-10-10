# Phase 81 — SQLite Spatial Evidence Repository Adapter

Introduces the concrete SQLite repository behind the Phase 80 repository contract. It delegates persistence and append-only controls to the Phase 68 SpatialEvidenceStore while exposing deterministic read filters for the service layer.

Prototype persistence only; no PostgreSQL/PostGIS availability, live environmental data, public API exposure, or regulatory authority is claimed.

Architecture:
FastAPI → Service Boundary → Repository Contract → SQLite Repository → Append-Only Evidence Store
