# Phase 196 — Proposed PostgreSQL Transactional Write RPC

Status: SQL candidate and static contract tests added; **not applied and not integration-tested**.

## Scope
Migration 006 proposes a server-only PostgreSQL function that inserts a measurement, idempotency key, and audit event within one database transaction. It uses an advisory transaction lock keyed by idempotency key, returns replay for same-key/same-digest requests, rejects same-key/different-digest requests, and prevents update/delete of audit events. Submission accepts only status `measured`; a verified status must come from a separate review workflow.

## Mandatory trust boundary
Only the trusted NEMA API may call the function using server-side credentials. The API must derive actor identity and role from an authenticated OIDC/session context. The function accepts actor values as parameters and cannot authenticate them; therefore passing browser-supplied identity/role is a critical security defect. The API must compute the payload digest from canonical JSON and must not trust a client-provided digest.

## Release gate
This migration is a proposal only. It has not been applied to Supabase or any database, and static tests do not prove PostgreSQL execution. Before staging, run it against a disposable PostgreSQL/Supabase project and test successful insert, identical retry, changed-payload conflict, concurrent duplicate requests, rollback, RLS and role grants, function ownership, and fixed search_path. Review digest semantics, audit ID uniqueness, and all constraint behavior. Then obtain explicit staging approval. Do not wire it into Streamlit directly or merge/deploy as production-ready.
