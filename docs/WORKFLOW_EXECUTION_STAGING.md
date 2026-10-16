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
