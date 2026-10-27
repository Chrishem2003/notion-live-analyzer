# Phase 202 — trusted portal-to-API identity binding

## Implemented

Added `nema_agora/measurement_portal_binding.py` and focused tests. The adapter accepts only the immutable `Principal` type produced by the NEMA authentication layer, requires an explicitly provisioned role in the measurement-submit allow-list, validates that the API key and signing secret are separate, rejects actor newline injection, and signs the exact actor/role pair expected by the API dependency.

The helper returns headers only. It does not send a request and cannot create a measurement. This keeps the trusted identity binding testable before any write route exists.

## Security boundary

The intended path is:

1. Streamlit OIDC session is authenticated.
2. `resolve_principal(st)` maps issuer+subject to a server-side role binding.
3. This adapter signs the resulting Principal for the API service.
4. The API verifies the service key and HMAC and creates an internal trusted principal.
5. A future guarded route validates the measurement contract and invokes the reviewed database RPC.

No step may take role/actor claims from user-submitted JSON. The current workspace's general case API client remains read-only and is not modified to permit measurement writes.

## Status

- Adapter and tests committed.
- No measurement POST route exposed.
- No database migration or live write executed.
- CI for the newest commits must pass before treating the adapter as validated.
