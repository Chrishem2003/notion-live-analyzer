# Phase 34 — Tamper-Evident Append-Only Audit Ledger

Phase 34 adds a separate SQLite ledger with monotonically increasing sequence numbers, unique entry IDs, canonical JSON payloads, SHA-256 entry hashes, and previous-entry hash links. SQLite triggers reject ordinary UPDATE and DELETE statements. Verification recomputes the chain and detects payload/hash changes, sequence gaps and broken links. Checkpoints record a verified head hash and sequence.

## Security boundary

This is tamper-evident, not tamper-proof. A privileged operator who can modify the database file or drop triggers can rewrite local history. Stronger assurance requires exporting signed checkpoints to an independently controlled system, protected backup retention, restricted filesystem/database access, and operational monitoring. The ledger does not prove source observations are true or establish NEMA authorization, environmental impact, regulatory status or production approval.
