# Phase 195 — Atomic Measurement Write Reference Harness

Status: local contract-test harness added; production write path remains blocked.

This phase adds a disposable SQLite reference implementation that tests atomic insertion of a measurement, an idempotency mapping, and an append-only audit event. Identical retries return the original result without duplicate audit events; reusing a key with a different payload conflicts. An injected failure after the first insert verifies all three records roll back. The submit path only accepts measured records; verification must be a separate authorized review transition.

This is not the production API or proof of Supabase/PostgreSQL behavior. Actor identity and role must come from authenticated server-side context; the harness itself does not authenticate callers, verify evidence bytes, or prove reviewer independence. It must not be wired to the live Streamlit UI as a substitute for shared durable storage.

Migration 004 remains proposed and unapplied. No RPC was installed, no database was changed, and no Render configuration or secrets were changed. Before staging, an equivalent PostgreSQL RPC must be implemented and tested in an isolated project for grants, RLS, concurrency, rollback, function ownership, and fixed search_path, then separately approved.
