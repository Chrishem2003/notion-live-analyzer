# NEMA-AGORA Supabase storage setup (read-only pilot)

This is a deployment runbook for the read-only storage adapter. Do not put database credentials in GitHub, Notion, screenshots, chat messages, or Streamlit/browser code.

## What this enables

The API can be configured to read NEMA case records and append-only audit history from a managed PostgreSQL database through Supabase's server-side REST API. The adapter is read-only: it has no create/update/delete methods. It does not migrate records from SQLite, and it does not make the case API production-ready for writes.

Supabase's Free tier is listed at $0/month with a 500 MB database, but free projects may pause after inactivity and automatic backups are not included. Confirm current terms at https://supabase.com/pricing before relying on it.

## One-time project setup

1. Sign in to https://supabase.com and create a new project on the Free plan. Choose a strong database password and store it in a password manager. Do not send it to ChatGPT.
2. Wait until the database is ready.
3. Open **SQL Editor** in that Supabase project.
4. Open the repository file migrations/supabase/001_nema_case_storage_readonly.sql and copy the entire SQL into a new SQL Editor query. Confirm you are in the intended project, then run it.
5. In Supabase **Project Settings → API** (wording may vary), copy the project URL and the **service_role** secret. The service-role secret bypasses row-level security, so it must remain server-side and must never be used in a browser or Streamlit UI. This schema grants the role SELECT only on the NEMA tables.
6. In Render, open the **notion-live-analyzer-api** service → **Environment**. Add/update these variables, using the values directly in Render:
   - NEMA_CASE_STORAGE_BACKEND = supabase_postgres
   - SUPABASE_URL = the project URL, beginning with https://
   - SUPABASE_SERVICE_ROLE_KEY = the service-role secret
7. Save the changes and allow the API service to redeploy. Do not change PLATFORM_API_KEY, and do not enable any write flag.

## Verify safely

1. Call GET https://notion-live-analyzer-api.onrender.com/api/v1/nema/cases/storage-readiness with the existing X-API-Key header using a trusted server-side client. Do not paste the key into a browser URL.
2. Expected response when the two tables are reachable: status: configured, storage_backend: supabase_postgres, database_reachable: true, required_schema_present: true, storage_durability_verified: false, production_writes_enabled: false.
3. Call the list endpoint with the same header. An empty result is acceptable if no real cases have been migrated.
4. Do not copy demo/dummy cases into the live database without an explicit data-migration review. Do not claim restart persistence until a synthetic test record can be written through a separately authorized test path, the service is restarted, and the same record is read back. This read-only adapter intentionally does not provide that write path yet.

## Stop conditions

- If the project is not ready, the SQL fails, or Render returns a 503, stop and review the exact non-secret error.
- If any credential was pasted into a public place, rotate it immediately.
- Do not enable production writes until server-derived actor identity, per-actor permissions, idempotency, expected-version conflict checks, transactional audit, backup/export, and restore tests are implemented and verified.
