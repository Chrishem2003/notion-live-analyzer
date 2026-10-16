# Research Submission Portal setup

The Streamlit page is `pages/18_Research_Submission_Portal.py`. It stores submissions in the application's SQLite database through `modules.audit_portal.CHRISHEMSubmissionSystem`.

## Required secrets

Configure **both** values before starting the app. Use long, randomly generated, different values.

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
