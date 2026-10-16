# Workflow Execution Center — staging acceptance runbook

This runbook is for an isolated staging deployment with **synthetic data only**. It is not a production approval. Never paste secret values into Notion, issues, chat, screenshots, or committed files.

## 1. Configure staging secrets

Configure these in the platform's approved secret store (or local uncommitted .streamlit/secrets.toml):

- WORKFLOW_EXECUTION_PASSWORD: unique high-entropy secret, at least 24 characters.
- NOTION_API_KEY: least-privileged integration token, only if testing Notion handoff.
- NOTION_ANALYSIS_RUNS_DATABASE_ID: the disposable staging Analysis Runs database UUID.
- WORKFLOW_RUNTIME_DB: writable path on the intended staging filesystem.

The execution page must remain locked if WORKFLOW_EXECUTION_PASSWORD is missing or too short. Do not use the repository's legacy placeholder authentication gateway as a security boundary.

## 2. Confirm access controls

- [ ] Open the Workflow Execution Center without the operator secret configured. Expected: page stops before initializing the runtime database or showing run history.
- [ ] Configure the secret in staging and restart the app.
- [ ] Verify an incorrect password is rejected.
- [ ] Verify the correct password unlocks the page.
- [ ] Verify manual lock and the 15-minute expiry revoke the session.
- [ ] Confirm no secrets appear in application logs, errors, or page output.

The current gate is a shared-secret mitigation. It is not individual identity, MFA, or role-based authorization; those remain production blockers.

## 3. Run deterministic smoke tests

### A. FASTA syntax/alphabet screen

Choose FASTA validation and use only this synthetic fixture:

    >DEMO-SEQ-001 synthetic training sequence
    ACGTACGTNN
    >DEMO-PROTEIN-001 synthetic training sequence
    MKWVTFISLL

Expected:
- Two records are reported.
- The nucleotide example is screened as nucleic acid with a GC percentage calculated only from canonical A/C/G/T/U bases.
- The protein example is screened as protein; GC percentage is not reported.
- The result states that the handler does not persist sequences and does not perform biological interpretation.

Also test malformed sequence text before a header, duplicate IDs, empty records, unsupported symbols, and input above the 1,000,000-byte limit. Oversized input must be rejected before persistence.

### B. Numeric summary and runtime history

- [ ] Run the provided numeric summary example.
- [ ] Confirm a run ID, input, result, attempt count, and ordered event history are stored.
- [ ] Restart the app against the same configured database path and verify the run remains readable.
- [ ] Submit an oversized input and verify it is rejected before a run record is created.
- [ ] Use a test handler that returns an oversized result and verify the run fails visibly without storing the oversized result.

## 4. Test Notion handoff against a disposable database

Only perform this section with a least-privileged integration and a staging Analysis Runs database.

- [ ] Confirm the integration is explicitly shared with the target database.
- [ ] Verify the handoff fails closed if the token is absent or the schema lacks required properties/options.
- [ ] Run a successful synthetic task and trigger the explicit handoff button.
- [ ] Fetch the created page from Notion and verify the manifest hash, Run Status Complete, Workflow Gate Execution Recorded, QC Outcome Pending, Reproducibility Check Not Checked, and Record Classification Synthetic/Test.
- [ ] Verify timestamps include a timezone and Code Revision/Input Dataset Version fields disclose when values were not supplied.
- [ ] Repeat the same handoff sequentially. Expected: existing manifest match is returned without creating a second page.
- [ ] Simulate a transient 503 on the schema read. Expected: bounded retry.
- [ ] Simulate a transport failure after create dispatch. Expected: no blind automatic replay; repeat the handoff action to reconcile by manifest hash.
- [ ] Test concurrent same-manifest handoffs. The current query-before-create pattern is not atomic; if duplicate pages are possible, record the defect and keep release blocked.

Never change QC to Pass or reproducibility to Passed merely because the runtime completed successfully.

## 5. Persistence, backup, and recovery

- [ ] Confirm the configured runtime database path is writable and persists across app restarts.
- [ ] Create a SQLite-aware backup while accounting for WAL state; restore into an isolated staging location.
- [ ] Verify run records and event history after restore.
- [ ] Verify any required encryption/decryption or secret-recovery procedure separately.
- [ ] Confirm the actual hosting platform provides durable storage; local filesystem persistence alone is not sufficient evidence for ephemeral or multi-replica deployments.

## 6. Evidence record requirements

For every test, record in the Verification & Validation Evidence database:

- Test ID and status
- Tester/responsible role and execution date
- Exact commit SHA and environment
- Expected versus actual outcome
- Evidence URL (CI run, sanitized log, screenshot, or fetched Notion page)
- Defects opened and retest notes

A CI pass is code-level evidence. It does not replace authenticated staging, durable storage, authorization, concurrent delivery, or backup/restore tests.

## Release decision

**HOLD** until P0/P1 release blockers are resolved, required staging checks are evidenced, authorization is accepted by the security owner, and scientific QC/reproducibility decisions receive documented human review.


## 7. Additional operator-gate regression checks (added 2026-10-16)

- [ ] Pass an explicit empty environment mapping to the credential loader while a process-level password is present. Expected: fail closed; no ambient environment fallback.
- [ ] Configure a whitespace-only password longer than 24 characters. Expected: fail closed.
- [ ] Confirm the secret store takes precedence over the environment and the configured value is compared exactly; do not trim or normalize a password after loading.
- [ ] Test session timestamps containing booleans, NaN, positive infinity, malformed strings, and future timestamps. Expected: invalid sessions fail closed.
- [ ] Test invalid TTL values (boolean, non-integer, zero, negative). Expected: invalid session configuration fails closed.

The shared-secret gate remains a transitional operator barrier. These checks do not provide individual identity, MFA, durable global rate limiting, or role-based authorization. Keep production deployment blocked until the hosting identity boundary and authorization model are verified.


## 8. Local concurrent handoff serialization

The Workflow Execution Center now passes its configured runtime SQLite path to the Notion handoff adapter. The adapter takes a SQLite BEGIN IMMEDIATE write lock before querying the target database and holds it until the handoff finishes. Processes that share the same database file are therefore serialized; the second same-manifest request re-queries Notion after the first request completes.

- [ ] Confirm all local workers use the same durable SQLite file before relying on this coordination.
- [ ] Run the automated concurrent same-manifest test using a shared ledger path.
- [ ] In staging, submit the same successful run concurrently and verify only one Notion page is created.
- [ ] Test an ambiguous create response (request reaches Notion but the client loses the response); retry and verify the adapter reconciles by manifest hash.
- [ ] Test SQLite lock timeout and busy behavior; ensure the UI reports a safe failure rather than claiming delivery.
- [ ] Do not assume this is a distributed lock: separate hosts or separate local filesystems can still race. Multi-host production needs a centralized outbox/dispatcher with durable leases and reconciliation.
- [ ] Do not claim atomicity between SQLite and Notion; the remote API and local ledger cannot share one transaction.


## 9. Required payload encryption and key recovery

The Workflow Execution Center now requires WORKFLOW_RUNTIME_ENCRYPTION_KEY before it initializes the runtime. Generate a Fernet key in a trusted environment (never in a public issue or chat):

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

- [ ] Store the key only in the approved secret manager / Streamlit secrets; never commit it or write it into Notion.
- [ ] Keep an access-controlled recovery copy under the organization's key-recovery policy. A lost key makes encrypted payloads unreadable.
- [ ] Verify that new input_json, result_json, and error_message fields start with the versioned enc:v1: prefix and do not contain the synthetic fixture in plaintext.
- [ ] Reopen the same database with the same key and verify input/result/error readback.
- [ ] Verify that opening encrypted data without a key or with a wrong key fails closed.
- [ ] Verify that an existing synthetic-only plaintext database is migrated transactionally when opened with the configured key; confirm the original records and event ordering remain intact.
- [ ] Confirm SQLite metadata, run IDs, task types, statuses, timestamps, digests, and event records remain visible in plaintext. This is application-level field encryption, not whole-database encryption.
- [ ] Document and test key rotation, protected backups, restore, retention, and deletion before using real research data.

The UI still requires synthetic/demo-only confirmation. This is an interim data-classification guardrail; it cannot detect dishonest or accidental misclassification. Real research, identifiable, confidential, or regulated content remains prohibited until the complete data-protection controls are accepted.


## 10. Controlled key rotation

A rotation helper is now available at tools/rotate_workflow_encryption_key.py. It refuses to overwrite an existing backup, creates a SQLite-aware backup first, then rotates the workflow_runs input/result/error fields in one transaction. If any ciphertext cannot be decrypted with the old key, the transaction rolls back and the backup is retained.

1. Stop workflow submissions and ensure no worker is executing.
2. In the trusted environment, set WORKFLOW_RUNTIME_ENCRYPTION_KEY_OLD and WORKFLOW_RUNTIME_ENCRYPTION_KEY_NEW. Do not pass keys as command-line arguments or paste them into Notion/chat.
3. Choose a new, non-existing backup destination with restricted permissions.
4. Run:

       python tools/rotate_workflow_encryption_key.py --database .streamlit/workflow_runtime.sqlite3 --backup /secure/backups/workflow-before-rotation.sqlite3

5. Confirm the command reports success and the backup path. The command never prints key values.
6. Set WORKFLOW_RUNTIME_ENCRYPTION_KEY to the new key in the approved secret store, remove old-key variables according to the recovery policy, then restart the app.
7. Verify readback with the new key and verify the protected backup can still be opened with the old key in isolated recovery staging.
8. Retain or delete the backup only under the approved retention policy; do not leave unprotected copies in the repository or app filesystem.

Do not rotate keys against production data until the backup, rollback, key custody, and recovery tests have been approved. Key rotation does not encrypt metadata/event digests and is not a substitute for filesystem or whole-database controls.
