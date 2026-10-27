# Phase 200 — deployed API entrypoint and write-path release gate

## Confirmed repository wiring

- The Render API container starts `api_server:app` via `scripts/start_research_run_api.sh`.
- `api_server.py` imports `nema_agora.api.router` and mounts it on the deployed FastAPI application.
- `nema_agora.api` is deliberately read-only today. Its route tests assert that no POST, PUT, PATCH, or DELETE route is exposed.
- The proposed measurement adapter in `nema_agora/measurement_api_boundary.py` is not yet connected to an HTTP route or a database call.

## Security decision

Do not add a measurement POST route by simply calling the existing read dependency or by trusting `authenticated=true` in request JSON. The existing case dependency only permits reviewer/coordinator/admin cross-case access; measurement submission has a different role model (submitter/coordinator/admin). A dedicated write dependency must validate the service API key and HMAC identity using the separate portal-signing secret, reject malformed/oversized fields, and produce a trusted principal internally. It must never deserialize principal claims from the measurement body.

## Remaining blockers before a write route

1. Review migration 006 against the actual deployed Postgres schema, function owner, EXECUTE grants, RLS, and the service-role trust boundary.
2. Ensure SQL validates the payload itself and recomputes or otherwise cryptographically binds the digest; do not trust a digest supplied by a caller.
3. Verify the SQL role allow-list and actor identity contract. A request role is not an independently authenticated human identity; it is only trusted if emitted by the authenticated server-side portal binding.
4. Define the evidence upload/reference lifecycle. The current adapter verifies bytes supplied to it but does not persist those bytes or establish their provenance.
5. Add integration tests against a disposable PostgreSQL instance for first insert, idempotent replay, conflicting replay, unauthorized roles, audit failure rollback, and concurrent requests.
6. Only after these gates pass, add the POST route to the existing mounted `nema_agora.api.router`, invoke the RPC using server-only credentials, and add a safe client method for the UI.

## Current safety posture

- No measurement write route is exposed.
- No database migration was applied.
- No production or staging environment variables were changed.
- No deployment was triggered by this work.
- Passing CI means the current source/test suite passed; it does not establish that the proposed write RPC is production-safe or that the current branch is deployed.

## Verified CI

At commit `9fbd01c7fc62aeb67e740187f1d185e983e6e487`, GitHub Actions run `40409353314` completed successfully. See [the run](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/40409353314).
