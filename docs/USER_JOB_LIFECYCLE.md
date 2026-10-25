# Per-user durable job lifecycle

This feature is opt-in and must remain disabled until an isolated staging environment has passed the release gates.

## Feature flags

- `SUPABASE_AUTH_ENABLED=false` keeps the Streamlit Supabase login adapter off.
- `USER_JOB_API_ENABLED=false` keeps the per-user job router unmounted.
- The Supabase service-role key is server-only. Never expose it to Streamlit browser code, clients, logs, or API responses.
- Do not apply the migrations to the connected production Supabase project as a staging shortcut.

## Request lifecycle

1. The client signs in with Supabase Auth and sends its short-lived access token as a bearer token.
2. The API verifies the token against Supabase Auth and derives the owner UUID from the verified response. Client-supplied tenant IDs, user IDs, or roles are rejected.
3. `POST /api/v1/user-jobs` accepts only `intelligence.solve`, a bounded prompt, bounded retry attempts, and an idempotency key.
4. An atomic database RPC reserves a per-user rolling-window quota. If quota enforcement is unavailable, the API fails closed.
5. The repository inserts the durable queue row using the verified UUID as both `tenant_id` and `requested_by`.
6. A worker claims a queued job with a lease, calls the governed intelligence service, and attempts an atomic completion. Failed attempts are recorded through the queue RPC and may be retried within the configured attempt limit.
7. `GET /api/v1/user-jobs/{job_id}` returns a tenant-scoped status projection and result, not the original prompt payload. The durable queue's terminal success state is `succeeded` (not `completed`).
8. `DELETE /api/v1/user-jobs/{job_id}` atomically cancels only a queued/running job owned by that user. A late provider response cannot complete a job once cancellation has changed its status.

## Status and errors

- `202`: job accepted and durably queued.
- `succeeded`: worker completed the job successfully; `failed` and `cancelled` are separate terminal states.
- `401`: missing, invalid, or expired bearer token.
- `404`: job does not exist or is not visible to this user.
- `409`: idempotency conflict or job is no longer cancellable.
- `422`: invalid input, UUID, or unsupported job type.
- `429`: rolling-window quota reached.
- `503`: authentication verification or durable storage is unavailable; retry may be appropriate.

Cancellation does not forcibly interrupt an in-flight provider network call. It prevents the cancelled row from being completed or overwritten after the provider returns. Provider-side compute may continue until that call ends or times out.

## Release gates

- [ ] Unit/API tests and authentication role-security workflow pass on the exact candidate commit.
- [ ] Disposable PostgreSQL integration workflow passes on the exact candidate commit, including quota concurrency, tenant isolation, cancellation, and RPC privilege checks.
- [ ] Run the full migration sequence against an isolated staging project/database that contains no production data.
- [ ] Exercise sign-up/sign-in, expired tokens, two independent users, quota exhaustion, idempotent retries, worker restart/lease recovery, result polling, cancellation, and provider outage.
- [ ] Confirm the worker process is deployed separately from the request API and has explicit resource limits/timeouts.
- [ ] Review logging and ensure prompts, bearer tokens, service-role credentials, and provider responses are not written to logs.
- [ ] Get explicit approval before production migrations, environment changes, enabling either feature flag, or deploying a worker.

Until these gates pass, keep the pull request in draft and production feature flags disabled.


## Shared AI UI

The feature-gated Shared AI workspace includes a durable-job mode for submitting an intelligence job, checking its owner-scoped status/result, and requesting cancellation. The browser never receives the Supabase service-role key; Streamlit keeps the bearer token and pending idempotency key in server-side session state. If a request fails ambiguously, retrying the same prompt reuses the same idempotency key; changing the prompt creates a new key. The UI validates job IDs as UUIDs before making status/cancellation requests.

The UI does not start a worker or enable the API. If the per-user API is disabled, it reports a safe service-unavailable message. The API flag and the worker deployment must be enabled only in staging after the database integration workflow and two-account tests pass.
