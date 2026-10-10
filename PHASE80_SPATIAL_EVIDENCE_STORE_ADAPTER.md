# Phase 80 — Spatial Evidence API Integration & Persistent Store Adapter

Connects the Phase 79 service boundary to a repository abstraction. The adapter accepts a repository implementing a small read-only list contract, allowing the current SQLite-backed evidence store and a future PostgreSQL/PostGIS repository to sit behind the same API boundary.

No database migration or live provider connection is claimed in this phase. The adapter does not mutate evidence, bypass append-only controls, or make environmental/regulatory conclusions.

Target production path:
FastAPI → Service Boundary → Repository Adapter → PostgreSQL/PostGIS
Prototype path:
FastAPI → Service Boundary → Repository Adapter → SQLite/In-memory test repository
