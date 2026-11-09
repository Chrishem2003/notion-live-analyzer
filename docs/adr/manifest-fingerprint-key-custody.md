# ADR — Versioned keyed manifest fingerprints

**Status:** Prepared, not approved for integration  
**Date:** 2026-11-09  
**Scope:** Pure fingerprint primitive only; no production or staging key configuration.

## Context

The current Notion handoff computes a deterministic, unkeyed SHA-256 digest over the full run manifest and uses it as the replay lookup value. This is not anonymization. For low-entropy manifests, an observer who can guess likely values may perform dictionary comparisons.

The durable outbox decision is still open: extend the existing platform queue or create a dedicated research-run outbox. Tenant identity, retention, worker deployment, key custody, rotation, and backup/restore also require owner approval.

## Safe preparatory implementation

The new module, modules/manifest_fingerprint.py, provides a pure HMAC-SHA-256 primitive with:

- deterministic strict-JSON encoding;
- explicit domain separation and algorithm version, with NUL-byte delimiters between the domain, key identifier, and canonical manifest;
- a fixed known-answer test that locks the v1 encoding and HMAC output;
- a caller-supplied key of at least 32 bytes;
- a non-secret key identifier embedded in the fingerprint and bound into the MAC;
- constant-time fingerprint comparison;
- rejection of weak/text keys, invalid key IDs, non-finite numbers, non-string object keys, and unsupported values.

The module does not read environment variables, generate keys, persist keys, log key material, or change the current Notion adapter. Unit tests use fixed synthetic test keys only.

## Decisions deliberately left open

No choice is made here about:

1. existing queue extension versus dedicated outbox;
2. per-tenant, per-project, or other key scope;
3. key generation, secret-manager custody, access, rotation, and revocation;
4. dual-key migration and replay compatibility with existing SHA-256 records;
5. fingerprint retention, audit access, and backup/restore;
6. whether a fingerprint is ever permitted to leave the trusted backend.

These require explicit owner/security approval. Do not put a real key in source control, Notion, CI variables, logs, or client-visible configuration.

## Integration gate

Before replacing manifest_digest or enabling any live handoff:

- approve the decisions above;
- provision a server-only key through the approved secret manager;
- define a dual-read migration so existing SHA-256 records remain discoverable without blind duplicate creation;
- test key rotation, missing-key fail-closed behavior, tenant isolation, restart persistence, and backup/restore;
- verify the live Notion payload remains metadata-only.

Until then, the current SHA-256 adapter remains unchanged and research-run write-back stays disabled.
