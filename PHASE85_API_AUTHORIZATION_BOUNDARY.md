# Phase 85 — API Authentication & Authorization Boundary

Adds a deterministic, fail-closed authorization contract for the spatial evidence API.

Roles:
- reviewer: spatial:evidence:read
- coordinator: spatial:evidence:read, spatial:evidence:query
- admin: spatial:evidence:read, spatial:evidence:query, spatial:evidence:admin

Missing authentication returns 401. Invalid identity, role, permission, or request ID returns 403. Successful authorization emits an immutable authorization fingerprint and request context.

This is a prototype authorization policy, not a production identity provider or NEMA credential system. No credentials are stored. The API remains read-only and makes no environmental or regulatory conclusions.
