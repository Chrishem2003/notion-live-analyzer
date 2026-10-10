# Phase 35 — Independent Audit Verification & Recovery

## Purpose
Phase 35 verifies a ledger against a previously exported checkpoint and provides a read-only foundation for comparing backups. It does not restore, repair, or mutate records.

## Implemented
- Versioned checkpoint export envelope with strict sequence and SHA-256 format validation.
- Full supplied-chain validation: contiguous sequence, previous-hash linkage, canonical entry hash, and checkpoint hash at the exact checkpoint sequence.
- Explicit detection of a checkpoint ahead of the ledger, checkpoint hash mismatch, sequence gaps, and entry tampering.
- Current-ledger verification that fails closed if the Phase 34 verifier detects an error or the 5,000-entry verification limit is exceeded.
- Backup comparison API that consumes entries and does not write to the backup.
- Authenticated Streamlit page for exporting a stored checkpoint and verifying an uploaded checkpoint.
- Phase 34 append operation now obtains a SQLite immediate write lock before reading the head, avoiding concurrent appenders building from the same head.

## Operational procedure
1. Create a checkpoint in the Audit Ledger page.
2. Export it from the Audit Recovery page.
3. Preserve the JSON in a separately controlled location, ideally with independent access controls and version history.
4. Later, upload the preserved checkpoint and verify the current ledger.
5. If verification fails, preserve the database and report first; investigate from a copy. Do not automatically rewrite or repair the source ledger.
6. Compare a candidate backup against the external checkpoint before any separately governed restoration process.

## Trust and limitations
- Checkpoint exports are not digitally signed by this phase. Integrity depends on protecting the checkpoint outside the database being verified.
- A checkpoint stored only in the same database is not an independent trust anchor.
- The ledger verifier is deliberately bounded at 5,000 entries and fails closed above that threshold; it does not silently treat a partial prefix as the complete ledger.
- SQLite triggers are not a defence against a privileged database/file owner.
- Backup comparison establishes artifact consistency only, not environmental truth, environmental impact, regulatory status, NEMA authorization, or production approval.
- No automatic restoration, deletion, rewriting, or evidence promotion is performed.
