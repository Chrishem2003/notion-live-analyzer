# Phase 87 — FastAPI Route Authentication Wiring & End-to-End HTTP Authorization Tests

Connects the Phase 85/86 authorization and query execution directly to FastAPI routes. The query route requires an Authorization header, then applies role/permission checks before persistent evidence access.

HTTP behavior:
- missing Authorization header → 401
- authenticated but unauthorized role/permission → 403
- authorized query → governed 200 response

The bearer value is only a presence signal in this prototype; no real credential verification or identity provider is claimed. Production authentication remains a future integration boundary.
