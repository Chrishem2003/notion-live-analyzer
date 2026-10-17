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
- [ ] Test concurrent same-manifest handoffs in authorized staging. A shared SQLite ledger serializes callers using the same file, but this does not protect separate hosts/filesystems; keep release blocked until the deployed topology is verified.
- [ ] If more than one Notion page matches the manifest hash, expect the adapter to stop and require manual duplicate reconciliation rather than choosing an arbitrary page.

Never change QC to Pass or reproducibility to Passed merely because the runtime completed successfully.

## 5. Persistence, backup, and recovery

- [ ] Confirm the configured runtime database path is writable and persists across app restarts.
- [ ] Create a SQLite-aware backup while accounting for WAL state; restore into an isolated staging location.
- [ ] Verify run records and event history after restore.
- [ ] Verify any required encryption/decryption or secret-recovery procedure separately.
- [ ] Confirm the actual hosting platform provides durable storage; local filesystem persistence alone is not sufficient evidence for ephemeral or multi-replica deployments.

## 5.1 Deployment configuration review (Batch 82)

Repository configuration review on 2026-10-17 found:

- `render.yaml` declares the web service on Render's `free` plan and does not declare a persistent disk or mount path.
- The web service configuration does not declare `WORKFLOW_RUNTIME_DB` or `WORKFLOW_RUNTIME_ENCRYPTION_KEY`; these must be configured in the approved platform secret/environment settings before the workflow execution page can safely initialize.
- The repository also defines a keepalive cron job. A keepalive request is not a durable-storage mechanism and must not be treated as proof that local SQLite data survives restart, redeploy, host replacement, or scale-out.
- The Dockerfile copies application files into the image but does not provision a durable database volume.

**Release blocker:** Do not use this Render configuration for real research data or claim durable workflow history until the deployment owner selects and configures a supported persistent storage design. For a single-instance pilot, verify that the chosen plan supports a persistent disk, mount it at an explicit path, configure `WORKFLOW_RUNTIME_DB` to a database file on that mount, and test restart/redeploy plus backup/restore. For multiple instances or workers on separate hosts, use a shared transactional database/outbox and coordination mechanism rather than relying on a local SQLite file. Do not change the service plan or incur hosting costs without an explicit owner decision.

- [ ] Record the approved hosting plan and storage architecture.
- [ ] Verify the runtime DB path resolves to the intended durable mount at runtime.
- [ ] Test persistence after restart and redeploy, not only a Streamlit rerun.
- [ ] Verify backup/restore and encryption-key recovery using synthetic data.
- [ ] If durable storage is unavailable, keep workflow execution disabled for persistent operations and clearly label the deployment as non-durable.

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


## 11. Configuration preflight (added 2026-10-16)

Before the manual staging run, execute:

    python tools/check_workflow_configuration.py

The command checks that the operator password meets the configured policy and the workflow payload encryption key is a valid Fernet key. It prints only pass/fail diagnostics and never prints secret values. It also reports the configured runtime database path, but does not create the database or prove that the hosting filesystem is durable.

- [ ] Run with both required secrets absent; expected non-zero exit and safe failure messages.
- [ ] Run with valid staging-only secrets; expected zero exit and no secret values in output.
- [ ] Confirm the script's result is recorded against the exact candidate commit.
- [ ] Do not treat this preflight as a substitute for the manual acceptance sections above.

The associated regression tests are in tests/test_workflow_configuration_preflight.py. Automated tests must pass on the exact candidate head before the preflight is relied upon.


## 12. Protected key-rotation backup files (added 2026-10-16)

The rotation helper now atomically reserves a new backup path using exclusive file creation, refuses pre-existing files and dangling symlinks, and applies POSIX mode `0600` to the backup. If backup creation fails, cleanup targets only the file reservation created by that invocation. This reduces local overwrite and accidental disclosure risk but does not replace host-level access control.

- [ ] On POSIX staging, verify the generated backup mode is `0600`.
- [ ] Verify an existing destination and dangling symlink destination are rejected without modifying the destination or creating the symlink target.
- [ ] On Windows or managed hosting, separately verify effective filesystem ACLs; POSIX mode bits are not a portable ACL guarantee.
- [ ] Verify backup retention, secure deletion, off-host backup policy, and recovery-key custody with the platform owner.

The additional regression tests live in `tests/test_workflow_runtime.py`. Exact-head CI must pass before this control is accepted.


## 13. Read-only backup verification (added 2026-10-16)

After creating a SQLite-aware backup, run the structural verifier against that backup file:

    python tools/verify_workflow_backup.py /secure/backups/workflow-before-rotation.sqlite3

The verifier opens the existing file in SQLite read-only mode. It checks SQLite integrity, required workflow tables/columns, record counts, and counts of fields using the versioned `enc:v1:` encryption prefix. It does not create a missing file or change the backup.

- [ ] Confirm the verifier returns exit code 0 and `"verified": true`.
- [ ] Confirm reported run/event counts are plausible for the isolated backup snapshot.
- [ ] Confirm encryption-prefix counts are consistent with the expected encrypted dataset; legacy plaintext fields may exist only where explicitly accepted during migration.
- [ ] Test missing, non-SQLite, incomplete-schema, and corrupt backups; failures must be non-zero and must not modify the candidate file.
- [ ] Follow with a restore to an isolated location, initialize the runtime using the approved key, and verify representative input/result/error readback and event ordering.

This is a structural pre-check, not proof of recoverability. The verifier cannot decrypt fields, prove key custody, compare against a moving source database, establish backup freshness, or prove the hosting platform's durability. Record exact commit, backup identifier, result, and restore evidence in the Verification & Validation Evidence database.


## 14. Concurrent worker claim and handler side effects (added 2026-10-16)

The runtime uses a SQLite write transaction to claim a queued run before invoking its registered handler. A regression test now races two callers against the same run and asserts the handler is invoked once and the durable event sequence remains queued → running → succeeded.

- [ ] Confirm the concurrent claim regression test passes on the exact candidate head.
- [ ] Treat a handler's external side effects separately from SQLite state. If a process dies after an external API call but before the terminal result commits, stale-run recovery may retry the handler and repeat that side effect.
- [ ] Therefore, every handler that calls an external system must use an external idempotency key, durable outbox, or reconciliation strategy appropriate to that system. Do not promise exactly-once external execution based only on the SQLite claim.
- [ ] Test process interruption after a simulated external side effect but before outcome persistence; verify reconciliation prevents duplicate external effects.
- [ ] Do not run stale-run recovery concurrently with long-lived handlers without leases/heartbeats and an agreed timeout. A slow legitimate handler can otherwise be mistaken for a dead worker.
- [ ] Keep multi-process/multi-host deployments blocked until the worker topology, lease strategy, durable storage, and cross-host coordination are validated.

This test establishes local single-run claim behavior under the tested race; it is not a distributed lock or a guarantee of exactly-once side effects.


## 15. Notion API response validation (added 2026-10-16)

The handoff adapter now rejects malformed query result structures, matching records without a non-empty page ID or HTTPS URL, and create responses that do not confirm both a page ID and HTTPS URL. This prevents the UI from claiming a successful handoff from an incomplete response.

- [ ] Verify malformed query responses fail before a page-create request.
- [ ] Verify incomplete create responses are surfaced as an unconfirmed outcome and are reconciled by querying the manifest hash before any retry.
- [ ] Verify database IDs are UUID-shaped before any network request; use a disposable staging database and least-privileged token for live acceptance.
- [ ] Confirm that an uncertain create outcome is never blindly replayed. Notion query-before-create plus a local SQLite lock is not a cross-host atomic uniqueness guarantee.

The new tests use mocked HTTP only. They do not establish live Notion permissions, target schema correctness, or successful staging delivery.


## 16. Ambiguous-create reconciliation regression (added 2026-10-16)

A new mocked-HTTP regression models the remote Notion page being committed while the client loses the create response. The next handoff attempt must query by the deterministic manifest hash, return the existing page, and avoid a second create request. A separate test rejects an existing-match URL that is not HTTPS.

- [ ] Confirm both tests pass on the exact candidate commit.
- [ ] In isolated staging, use a disposable run and verify the same recovery path against the real Notion API.
- [ ] Record the fetched page ID and manifest hash as evidence; do not record integration tokens.
- [ ] Remember that this reconciliation depends on the manifest hash being queryable and the target page being visible to the integration. It is recovery logic, not an atomic remote uniqueness constraint.


## 8. Research QC/provenance gate tests (synthetic fixtures)

The pure gate evaluator is available as the allow-listed `research_qc_gate` handler. It does not modify Notion records and its output is not a human scientific approval.

- [ ] Confirm missing classification, units, protocol relation/version, raw-source reference, or source dataset version blocks QC approval.
- [ ] Confirm missing reviewer, review date, or QC evidence blocks approval and downstream report/close.
- [ ] Confirm `🔴 Anomalous` and `🟡 Pending` block report and close even when workflow Status says Verified or the sample stage says Archived/Reported.
- [ ] Confirm `🟢 Verified` with missing review evidence remains blocked.
- [ ] Confirm a fully populated synthetic fixture passes the report gate, and inspect the returned blockers/decision before wiring any mutation.
- [ ] Treat the evaluator as validation only: a future application integration must record the actor, timestamp, record identity, evidence, and gate decision atomically with any status transition. Do not automatically update historical records based on this check.
