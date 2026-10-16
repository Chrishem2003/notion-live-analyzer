# Research Submission Portal setup

The Streamlit page is `pages/18_Research_Submission_Portal.py`. It stores submissions in the application's SQLite database through `modules.audit_portal.CHRISHEMSubmissionSystem`.

## Required secrets

Configure **both** values before starting the app. Use long, randomly generated, different values; the application rejects identical values.

### Streamlit secrets

Create a local `.streamlit/secrets.toml` file (never commit it):

```toml
AUDIT_PORTAL_ENCRYPTION_PASSWORD = "replace-with-a-long-random-secret"
AUDIT_PORTAL_PROFESSOR_PASSWORD = "replace-with-a-different-long-random-secret"
```

### Environment variables

Alternatively, set:

- `AUDIT_PORTAL_ENCRYPTION_PASSWORD`
- `AUDIT_PORTAL_PROFESSOR_PASSWORD`

Streamlit secrets take precedence over environment variables. Missing or blank values stop the portal from accepting submissions; the application does not fall back to a built-in password.

## Security and operational notes

- The encryption password is used to encrypt submission content and review feedback. The professor password is a separate gate for the review page.
- Research content and review feedback are encrypted; researcher name, email, title, project ID, status, timestamps, and other record metadata remain plaintext in SQLite. Restrict database files, backups, and server access accordingly.
- Keep the encryption password in a secret manager, restrict access, and maintain a tested backup/recovery procedure. Losing or changing the encryption password without a migration will make existing records unreadable.
- The default database path is `research_workspace.db` at the repository root. Back it up using a SQLite-aware procedure and test restores in staging.
- The integrity hash is an application-generated reference, not a public blockchain transaction and not proof of authorship.
- This first UI integration does not calculate plagiarism or AI-authorship scores. Do not present demo scores as evidence.
- The shared professor password is a first integration gate, not a replacement for user accounts, roles, MFA, or organization-level access controls. Add the application's established authentication/authorization before production use.
- Run the full test suite and a staging smoke test before deploying: submit a test record, restart the app, decrypt it, review it, and confirm the stored status/feedback.


## Submission event history

The portal now records submission creation, review, and return-for-revision status transitions in a SQLite event table in the same database transaction as the corresponding write. Event rows intentionally avoid storing research content or feedback text. The history improves operational traceability, but it is **not tamper-proof** and does not identify an individual professor while the shared-password gate remains in use. Restrict database access and add per-user identity/authorization before relying on it for formal accountability.


## Current combined review candidate

The current combined candidate is [PR #19](https://github.com/Chrishem2003/notion-live-analyzer/pull/19), which includes the persistent portal and its transactional submission-status event history. PR #18 is superseded for release purposes; do not merge both separately. Check the latest exact-head CI result and complete the documented staging and authorization gates before production use.


## Staging release checklist (required before production)

Complete this checklist in a non-production environment using synthetic data. Record the tester, date, application commit, and evidence for each item in the release record; do not mark a gate complete based on CI alone.

- [ ] Confirm both required secrets are configured, non-empty, distinct, and supplied through the approved secret store; verify no secret values appear in logs or screenshots.
- [ ] Start the app with a fresh temporary database. Confirm the portal refuses submission when either secret is missing or both secrets are identical.
- [ ] Submit synthetic content and confirm it persists after restarting the app; inspect the SQLite row to verify the research content is ciphertext rather than plaintext.
- [ ] Confirm the configured encryption secret decrypts the record and a wrong secret fails without exposing cryptographic details.
- [ ] Unlock the review queue with the professor password; confirm incorrect credentials fail and the session expires after 15 minutes.
- [ ] Save a review and a return-for-revision decision. Verify statuses, grades/scores where applicable, and event ordering after restarting the app. Confirm event details do not contain research text or feedback text.
- [ ] Simulate an event-table write failure for submission, review, and return actions. Confirm the related state change rolls back and no partial decision is persisted.
- [ ] Restore a database backup into an isolated staging instance and verify records can be decrypted using the approved encryption secret.
- [ ] Verify filesystem permissions, database and WAL/SHM file access, backup access, TLS, deployment secrets, and access to application logs against the deployment threat model.
- [ ] Confirm per-user professor identity, role-based authorization, and the institution's data-retention/privacy requirements before using the portal for sensitive or official assessments.

**Release gate:** keep production deployment blocked until the staging checks are evidenced, deployment-specific authentication/authorization is in place, and an authorized reviewer accepts the remaining plaintext metadata and key-recovery risks. A green CI run is necessary but not sufficient.
