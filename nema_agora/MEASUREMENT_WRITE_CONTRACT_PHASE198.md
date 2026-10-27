# Phase 198 — trusted API measurement payload adapter

## Implemented

- Adds `nema_agora/measurement_write_contract.py` to bridge the Phase 191 evidence record into the proposed PostgreSQL RPC schema.
- Validates the source record against the indicator definition and verifies the actual uploaded artifact bytes against its SHA-256.
- Allows submission status `measured` only; reviewer verification remains a separate workflow.
- Builds the exact RPC record first, then calculates the canonical payload digest over that mapped record, reducing the risk that the digest describes a different object than the one inserted.
- Adds unit tests for mapping, digest consistency, altered evidence bytes, status separation, role validation, and payload changes.

## Boundaries

This is a pure Python adapter, not a live API endpoint and not a database writer. The caller must authenticate the user, derive actor ID/role from the verified server-side session, and enforce indicator-level authorization. It does not authenticate actors, establish reviewer independence, or prove evidence source authenticity.

The adapter uses the existing Phase 191 evidence schema (`period_start`, `source_record_ids`, `evidence_reference`, `evidence_sha256`) and maps it to the proposed RPC schema (`reporting_period_start`, `source_refs`, `evidence_refs`). Before connecting it to the RPC, review the indicator registry and make `reporting_timezone` and `definition_version` required at the API boundary.

## Release gate

No database migration applied. No Render service, secrets, or production deployment changed. PostgreSQL concurrency, function ownership, digest verification at the database boundary, and authenticated API integration remain untested.
