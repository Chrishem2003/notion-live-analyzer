# NEMA-AGORA Indicator Measurement Ledger — Migration Notes

Status: **proposed; not applied to any Supabase project**.

The migration `004_nema_indicator_measurements.sql` defines a durable schema for versioned, period-bound indicator measurements. It records source references, evidence references, exclusions, calculation method, reviewer, and verification timestamp. Database constraints prevent invalid status values, reversed reporting periods, negative measurements, malformed JSON array fields, and a `verified` status without evidence.

## Security posture

- Row-level security is enabled.
- `anon` and `authenticated` receive no table privileges.
- `service_role` receives SELECT only.
- No application write path is enabled by this migration.
- A later write path must use an audited transactional database function/RPC with actor authorization, idempotency, concurrency control, and append-only audit events.

## Apply gate

Before applying, confirm the exact staging project, inspect existing table/schema state, back up/export the current schema, and review the SQL. Do not apply directly to production. After applying to staging, verify RLS and grants from database metadata. Do not write sample records to the live project merely to test the schema; use a disposable local/test database or a specifically approved staging fixture.

The application-level validator in `nema_agora/indicator_measurements.py` is the corresponding in-memory contract. It is not yet wired to a database or shown as a live metric in the Streamlit UI.
