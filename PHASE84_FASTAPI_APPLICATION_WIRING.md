# Phase 84 — FastAPI Application Wiring & HTTP Contract Surface

Wires the governed persistent spatial evidence query layer into an actual FastAPI application when FastAPI is installed.

Endpoints:
- GET /api/v1/spatial-evidence/health
- GET /api/v1/spatial-evidence/query

The query endpoint delegates to Phase 83 and preserves fail-closed behavior. The application is read-only and authorization-aware.

FastAPI remains an optional dependency for compatibility with the repository's lightweight test environment. No public deployment, live provider, regulatory conclusion, enforcement authority, or emergency dispatch is claimed.
