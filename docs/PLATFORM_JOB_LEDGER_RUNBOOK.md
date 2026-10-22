# Durable Platform Job Ledger — gated rollout runbook

## Current scope

The ledger adds durable, idempotent job storage with lease-based claiming, attempt history, and append-only audit events. The API currently accepts only `platform.synthetic.validate`; it does not authorize real Notion writes or research actions. Do not add a job type until its handler, authorization, idempotency, and recovery behavior have tests.

## Required server-side environment

Configure these only on the private API and Celery worker services:

- `SUPABASE_URL`: HTTPS URL for the intended Supabase project.
- `SUPABASE_SERVICE_ROLE_KEY`: service-role secret. Never expose to Streamlit/browser, commit it, or include it in logs/task payloads.
- `PLATFORM_API_KEY`: existing API service-to-service key; the API rejects calls when absent.
- `PLATFORM_JOB_ACTOR_SCOPE`: fixed trusted scope such as `service:platform-api`. It is deliberately not accepted from the request body.
- `PLATFORM_JOB_LEDGER_ENABLED`: keep `false` until the migration is applied to a disposable/development database, grants are verified, and the worker is deployed and smoke-tested.

The API also needs its existing Celery/Redis configuration. The worker service must run Celery with the module registered by `celery_app.py`.

## Safe rollout sequence

1. Review `supabase/migrations/20261022210000_platform_job_ledger.sql` and run it only on a disposable Supabase branch or local database first.
2. Validate the RPC grants, RLS flags, idempotency conflict behavior, stale lease rejection, and append-only audit trigger. Do not apply to production as a substitute for these tests.
3. Deploy the API and worker with `PLATFORM_JOB_LEDGER_ENABLED=false`.
4. Verify the API health route and worker startup. Confirm the service-role key is available only to server services.
5. In a non-production environment, apply the migration, run the unit suite, and exercise one synthetic job twice with the same `Idempotency-Key`. It must create one row and return the same job ID on retry.
6. Verify the status endpoint never returns the request payload or lease token, and verify a different request with the same idempotency key returns HTTP 409.
7. Only then set `PLATFORM_JOB_LEDGER_ENABLED=true` in the non-production environment and smoke-test:
   - `POST /api/v1/platform-jobs` with `{"job_type":"platform.synthetic.validate","payload":{"test":true}}` and an `Idempotency-Key` header.
   - `GET /api/v1/platform-jobs/{job_id}` until it reaches `succeeded`.
8. Production enablement requires a separate approval after the same checks against the production release candidate. Never use real research records for the first test.

## API behavior

- Missing API key: rejected by the existing service-to-service authentication dependency.
- Disabled ledger or missing trusted actor scope: returns service unavailable; no job write is attempted when disabled.
- Missing/oversized idempotency key or invalid request: rejected before dispatch.
- Redis dispatch failure after enqueue: API returns a retry-safe service-unavailable response. Retry with the *same* idempotency key; the durable row remains available for dispatch.
- Only the synthetic handler is registered. Unsupported job types are moved to `needs_review` and do not run arbitrary code.

## Operational limitations still to resolve

- SQL migration must pass isolated PostgreSQL/Supabase validation; mocked Python tests do not prove the database contract.
- The current actor scope is service-wide because the API uses the existing shared API key. Do not expose this endpoint to end-user clients until per-user/tenant identity is derived from trusted authentication and authorization is enforced.
- Add metrics and alerts for queued age, expired leases, failed jobs, and `needs_review` before production use.
- Add reviewed handlers for real workflows one at a time; keep Notion write-back disabled until durable recovery and read-after-write verification pass.
