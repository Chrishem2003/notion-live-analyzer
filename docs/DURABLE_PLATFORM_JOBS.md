# Durable platform jobs (service-to-service foundation)

This adds a Postgres-backed queue for the allow-listed `intelligence.solve` task.
The job and event tables live in Supabase; enqueue, retry, failure, and completion are audited. The claim function uses row locking and
`SKIP LOCKED`, jobs have bounded attempts and expiring leases, and retries use a
bounded delay. Idempotency is enforced per service tenant and key. RLS is enabled
with no end-user policies; only the server-side service-role credential can access
these tables.

## API

- `POST /api/v1/jobs` with `X-API-Key`, `Idempotency-Key`, and a JSON body containing
  `job_type: "intelligence.solve"` plus `prompt` and optional provider/model/strategy.
- `GET /api/v1/jobs/{job_id}` with `X-API-Key` to poll the status/result.

The key is service-to-service only. Do not place it in browser JavaScript or expose
these endpoints directly to end users. The current implementation uses the fixed
service tenant `platform-service`; this is **not** per-user authentication or tenant
isolation. Supabase Auth/JWT validation and per-user authorization must be implemented
before multi-user job submission is enabled.

## Worker

Run a separate worker process with `python -m platform_jobs.worker`. It needs the
same application code and server-side `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
plus the AI provider configuration required by Sovereign Intelligence. It only
executes the allow-listed intelligence solve job, never arbitrary submitted code.

The current Render deployment has not been changed to add a worker. Do not assume
jobs will execute until a persistent worker process is actually deployed and its
logs/round-trip are verified. A web-service process can enqueue durable jobs even
while no worker is running, but they will remain queued.

## Privacy and reliability notes

The 30-day retention migration is applied and scheduled to redact stored job prompts
and results, including stale queued/running jobs. It preserves job metadata and writes a
`content_redacted` audit event. Do not submit secrets or highly sensitive personal
data. This retention rule does not replace per-user authorization or a separate
retention policy for the Sovereign Intelligence memory store. Postgres persists job
state, but backups, restore drills, worker availability, and provider availability
still need separate verification.

## Configuration

Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` as server-only secrets on the API
and worker. Never expose the service-role key to Streamlit browser code. Keep the
existing research-run write-back disabled until its own idempotency and Notion
configuration preflight is complete.
