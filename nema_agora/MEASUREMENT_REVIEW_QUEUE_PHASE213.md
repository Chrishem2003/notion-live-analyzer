# Phase 213 — canonical read-only officer review queue

## Implemented

- Added read-only PostgREST methods for canonical indicator measurements and submission audit events.
- Added an authenticated review queue loader restricted to reviewer, coordinator, and admin roles.
- Queue loads only canonical records in measured status, retrieves audit events by canonical measurement ID, flags missing submission audit, and detects whether the current officer appears as submitter.
- Added a Streamlit renderer with a queue table, canonical record details, audit history, and explicit read-only notice.
- Added regression tests for role denial, missing audit, audit actor detection, and no writes.

## Not implemented by design

The proposed SQL migration 006 is not applied, and the submission RPC is not exposed by the API. If the measurement/audit tables are unavailable, the queue fails closed with an unavailable message. Review decisions are not persisted and verified status is not changed. A durable review ledger, append-only audit action, transactional review API, and independently authorized verification transition remain release gates.
