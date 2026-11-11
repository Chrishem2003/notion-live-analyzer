# Durable Platform Job Ledger — gated rollout runbook

## Current scope

The ledger adds durable, idempotent job storage with lease-based claiming, bounded handler retries, attempt history, and append-only audit events. The API currently accepts only `platform.synthetic.validate`; it does not authorize real Notion writes or research actions. Do not add a job type until its handler, authorization, idempotency, and recovery behavior have tests.

## Required server-side environment

Configure these only on the private API and Celery worker services:

- `SUPABASE_URL`: HTTPS URL for the intended Supabase project.
- `SUPABASE_SERVICE_ROLE_KEY`: service-role secret. Never expose to Streamlit/browser, commit it, or include it in logs/task payloads.
- `PLATFORM_API_KEY`: existing API service-to-service key; the API rejects calls when absent.
- `PLATFORM_JOB_ACTOR_SCOPE`: fixed trusted scope such as `service:platform-api`. It is deliberately not accepted from the request body.
- `PLATFORM_JOB_LEDGER_ENABLED`: keep `false` until the migration is applied to a disposable/development database, grants are verified, and the worker is deployed and smoke-tested.

The API also needs its existing Celery/Redis configuration. The worker service must run Celery with the module registered by `celery_app.py`.

## Deployment topology gate

The current repository `render.yaml` defines the Streamlit web service and API web service; it does **not** yet define a dedicated ledger worker or Celery Beat service, and it does not provision Redis or configure `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` for the ledger. Therefore, the new ledger cannot execute end to end on the current Render blueprint merely by setting the feature flag.

Before staging activation, provision or select an approved Redis-compatible broker and configure the same private `REDIS_URL` for API, worker, and Beat. Configure the Supabase URL and service-role secret only on the API and worker/Beat services that need them. Add a dedicated Celery worker running `sh scripts/start_platform_ledger_worker.sh` and a separate Beat process running `sh scripts/start_platform_ledger_beat.sh`. Both scripts require an explicit Redis URL and fail closed on missing ledger credentials when the flag is enabled; the worker listens only to the dedicated `platform_ledger` queue. Keep all services on a non-production database and keep the ledger feature flag false until the migration and smoke tests pass.

Do not deploy a blueprint change that creates paid workers or managed Redis until the service plan and recurring cost have been explicitly reviewed. Do not put the service-role key in Streamlit, a browser, repository files, or client-side configuration.

## Safe rollout sequence

1. Review all three migrations (`20261022210000_platform_job_ledger.sql`, `20261023010000_platform_job_dispatch_reconciliation.sql`, and `20261023020000_platform_job_ledger_metrics.sql`); run them only on a disposable Supabase branch or local database first.
2. Validate the RPC grants, RLS flags, aggregate-metrics RPC privileges, idempotency conflict behavior, stale lease rejection, and append-only audit trigger. Do not apply to production as a substitute for these tests.
3. Deploy the API and worker with `PLATFORM_JOB_LEDGER_ENABLED=false`. Also run Celery Beat as a separate process (using `sh scripts/start_platform_ledger_beat.sh`) so the 30-second dispatch reconciliation task is actually scheduled.
4. Verify the API health route and worker startup. Confirm the service-role key is available only to server services.
5. In a non-production environment, apply the migration, run the unit suite, and exercise one synthetic job twice with the same `Idempotency-Key`. It must create one row and return the same job ID on retry.
6. Verify the status endpoint never returns the request payload or lease token, and verify a different request with the same idempotency key returns HTTP 409.
7. Only then set `PLATFORM_JOB_LEDGER_ENABLED=true` in the non-production environment and smoke-test:
   - `POST /api/v1/platform-jobs` with `{"job_type":"platform.synthetic.validate","payload":{"test":true}}` and an `Idempotency-Key` header.
   - `GET /api/v1/platform-jobs/{job_id}` until it reaches `succeeded`.
   - `GET /api/v1/platform-jobs/metrics` and verify aggregate counts only; the response must not contain job IDs, actor scopes, payloads, or error bodies.
8. Production enablement requires a separate approval after the same checks against the production release candidate. Never use real research records for the first test.

## Automatic dispatch recovery

- Celery Beat schedules `tasks.reconcile_platform_ledger_dispatches` every 30 seconds. Both the reconciler and the worker processor are inert while `PLATFORM_JOB_LEDGER_ENABLED` is false, so turning the flag off prevents new ledger claims.
- When enabled, the reconciler asks the database to reserve up to 25 queued jobs or jobs whose worker lease has expired, then dispatches worker tasks. It never reads or returns job payloads.
- The reservation RPC has a 60-second cooldown to bound duplicate broker messages when workers or the broker are unavailable. A later sweep retries unclaimed reservations. The worker claim remains atomic, so duplicate task messages cannot claim the same active lease.
- The reconciliation loop is best-effort, not a substitute for monitoring. Alert on repeated broker failures, queue age, expired leases, failed jobs, and `needs_review` jobs.

## Non-production end-to-end smoke test

After a separate staging API, database, Redis broker, worker, and Beat are provisioned and reviewed, run the smoke test from a trusted operator environment. It submits only the registered `platform.synthetic.validate` handler.

Required environment variables:

- `PLATFORM_LEDGER_SMOKE_BASE_URL`: HTTPS origin of the approved staging API only.
- `PLATFORM_LEDGER_SMOKE_API_KEY`: staging API key; keep it out of command history, source control, and logs.
- `PLATFORM_LEDGER_SMOKE_CONFIRM=I_UNDERSTAND_NON_PRODUCTION`: explicit confirmation.

Run with `python scripts/platform_ledger_staging_smoke.py`. The script refuses the known current production API hostname, verifies health and metrics, enqueues a synthetic job, checks same-key idempotency, checks that changed payload reuse returns HTTP 409, polls status until success, and checks that status/metrics do not expose payloads or lease tokens. It times out after two minutes and prints no secrets.

Do not run against production. The smoke script does not provision infrastructure, apply migrations, or enable feature flags. A successful run is evidence for the tested staging environment only.

## Aggregate operations endpoint

- Authenticated `GET /api/v1/platform-jobs/metrics` is gated by `PLATFORM_JOB_LEDGER_ENABLED` and the existing service-to-service API key.
- It returns counts by state, expired lease count, oldest queued age in seconds, counts created/finished in the last 24 hours, and a sample timestamp. It does not expose job IDs, actor scopes, payloads, or error bodies.
- The metrics RPC uses `SECURITY DEFINER`, a fixed search path, and service-role-only execution. It provides aggregate visibility without granting direct table reads.
- This is an endpoint for polling and dashboards, not a complete alerting system. Wire it to an approved monitor after staging validates it.

## API behavior

- Missing API key: rejected by the existing service-to-service authentication dependency.
- Disabled ledger or missing trusted actor scope: returns service unavailable; no job write is attempted when disabled.
- Missing/oversized idempotency key or invalid request: rejected before dispatch.
- Handler failures are retried by the ledger while `attempt_count < max_attempts`; exhausted jobs become `failed`. Worker crashes are recovered through lease expiry, and exhausted crash retries become `needs_review`.
- Redis dispatch failure after enqueue: API returns a retry-safe service-unavailable response. Retry with the *same* idempotency key; the durable row remains available for dispatch.
- Only the synthetic handler is registered. Unsupported job types are moved to `needs_review` and do not run arbitrary code.

## Operational limitations still to resolve

- All three SQL migrations must pass isolated PostgreSQL/Supabase validation; mocked Python tests do not prove the database contract.
- The current actor scope is service-wide because the API uses the existing shared API key. Do not expose this endpoint to end-user clients until per-user/tenant identity is derived from trusted authentication and authorization is enforced.
- Add metrics and alerts for queued age, expired leases, failed jobs, and `needs_review` before production use; confirm Celery Beat is running in the deployed environment.
- Add reviewed handlers for real workflows one at a time; keep Notion write-back disabled until durable recovery and read-after-write verification pass.
