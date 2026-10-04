# NEMA-AGORA Pilot

**Working title:** National Environment Governance, Automated Monitoring, and Response Engine  
**Applicant / project lead:** Kula Chris, B.Sc. Biological Sciences student, Muni University  
**Funding proposal:** UGX 7,000,000 over six months

NEMA-AGORA is an independent student-led prototype proposal. It is **not** an official NEMA system and has no implied NEMA endorsement or integration. The initial MVP is a deliberately narrow environmental observation and case-tracking workflow.

## Current MVP

The Streamlit page is `pages/18_NEMA_AGORA.py` and provides:

- Structured environmental observation entry.
- Session-only case identifiers and status tracking.
- Reviewer notes and update timestamps.
- Guarded case-status transitions with a current-session status-change history.
- Length limits on user-entered fields and spreadsheet-formula neutralisation on CSV export.
- Optional latitude/longitude and a simple map.
- CSV export and basic process metrics.
- Clear warnings about prototype status, privacy and unverified observations.

## Authentication and identity foundation

Streamlit's native OpenID Connect (OIDC) flow is the proposed login layer. The helper in `nema_agora/identity.py` maps the authenticated issuer + subject claims (`iss` + `sub`) to a server-configured role. It deliberately ignores role claims supplied by the identity provider and treats unregistered users as authenticated but unauthorised.

- `nema_agora/access.py` defines the permission policy; `identity.py` resolves a principal. Neither module alone enforces access at every application entry point.
- The sample configuration is `.streamlit/secrets.toml.example`. Copy and complete it in the host's secret manager; never commit a real `secrets.toml`, client secret, or cookie secret.
- Configure the OIDC client with the exact deployed app URL and its `/oauth2callback` redirect URI. Test local and hosted configurations separately.
- Use the stable issuer + subject pair as the account key. Do not grant roles based only on display name or email.
- Provision roles explicitly with least privilege; a valid login must not automatically grant access.
- Before enabling persistent data, enforce the resolved principal and permission policy for every create/read/review/export/audit operation and test direct navigation as well as UI controls.

The helper does not itself start the login flow, validate OIDC tokens, manage users, or integrate the public page. Deployment configuration and enforcement remain required.

## Important limitations

- The Streamlit page now has two explicit modes: demo (session-only) and persistent. Persistent mode is available only after OIDC authentication resolves to a server-configured role and an explicit database path is configured.
- A standalone, deny-by-default role-permission policy now exists in `nema_agora/access.py`; it is policy logic only, not authentication or enforcement at the UI/database boundary. SQLite audit events record actor identifiers supplied by the caller, so the policy and repository must not be exposed until actor identifiers come from verified authentication and every sensitive operation enforces permissions.
- A database audit table is not automatically tamper-proof; production use needs access controls, backups, retention rules, monitoring and an appropriate audit-protection design.
- No reports are sent to NEMA or any other authority.
- No ELMIS/SWIMS integration or official dataset access is implemented.
- The system does not verify allegations or make regulatory decisions.
- Do not enter personal, confidential, or urgent incident information.

## Run locally

From the repository root, with the repository's environment activated:

```powershell
python -m streamlit run pages/18_NEMA_AGORA.py
```

The repository already includes Streamlit in its main requirements. If setting up a new environment, install the project requirements first.

## Recommended next steps

1. Review the implemented status transitions and data fields with a supervisor.
2. Agree pilot scope, site, supervision, consent, retention and data-handling rules.
3. Review the isolated SQLite repository and data model; do not connect it to the public page yet.
4. Configure and test OIDC login using the secret template, set nema_agora.mode = "persistent" and an approved nema_agora.database_path, then test each role before real-user use.
5. Add deployment-specific database configuration, backup/restore tests, retention rules and operational monitoring.
6. Test accessibility, low-bandwidth behaviour and CSV export.
7. Validate budget assumptions and grant eligibility with the official NEMA call.

## Project links

- Applicant LinkedIn: https://www.linkedin.com/in/chris-shem-435166314
- Existing demo: https://notion-live-analyzer-w6ckned7rqd4gb8oppjjke.streamlit.app/
- Research planner: https://sleet-spectacles-fd3.notion.site/Bio-Research-Enterprise-Research-Planner-35f9142806c6805286a5c6767a7c9cfd?pvs=143


## Security milestone: authorization boundary

The persistent layer now has an explicit authorization boundary:

- Streamlit OIDC identity is converted into a stable issuer + subject principal.
- Roles are assigned only from server-side nema_agora.role_bindings.
- Unknown or unbound users fail closed.
- SQLite create/read/review/audit operations enforce the role policy at the repository boundary.
- Submitters can read only records they own; reviewers/coordinators can read according to their permissions.
- Audit events record the actor identifier supplied by the authenticated application boundary.
- The SQLite layer is still not connected to the public page until deployment-specific authentication, database path, backup/restore, retention and operational controls are configured.

Streamlit provides native OIDC through st.login(), st.user, and st.logout(). Keep secrets outside Git and configure the deployed callback URL in the host secret manager.

## Next build gate

1. Configure OIDC in the host secret manager and create explicit role bindings.
2. Run focused tests and manual authentication tests with at least one account per role.
3. Add deployment-specific SQLite path plus backup/restore, retention and monitoring configuration.
4. Connect the page to the repository only when an authenticated principal is present.
5. Add an operational admin/audit view and controlled export.
6. Validate low-bandwidth accessibility and pilot data-handling rules.

## Phase 4 implementation: authenticated persistence gate

The next build phase is now wired end-to-end at the application boundary:

- `nema_agora/auth.py` converts Streamlit OIDC state into a trusted `Principal`.
- `nema_agora/service.py` prevents UI code from supplying arbitrary actor IDs or roles.
- `nema_agora/config.py` makes persistence an explicit deployment choice (`demo` or `persistent`) and requires explicit backup configuration for operations.
- `nema_agora/backup.py` provides verified SQLite backup, integrity checking, bounded file retention and explicitly confirmed restore.
- `pages/19_NEMA_AGORA_ADMIN.py` provides an admin-only operations console with health, backup inventory, restore safeguards and administrative audit events.
- `pages/18_NEMA_AGORA.py` requires authentication and a provisioned role before persistent data is exposed.
- Repository reads, reviews, audit access and exports are permission-gated.
- Submitter ownership isolation is preserved.
- A legacy SQLite schema without `owner_id` is migrated to an inaccessible `legacy-unowned` owner rather than guessing ownership.

### Deployment configuration

The secret template contains the OIDC client settings and server-side role bindings. Add the following non-secret application settings to the same `nema_agora` section in the host secret manager:

```toml
[nema_agora]
mode = "persistent"
database_path = "/approved/persistent/location/nema_agora.sqlite3"

[nema_agora.role_bindings]
# "<issuer>|<stable sub>" = "submitter" | "reviewer" | "coordinator" | "admin"
```

Do not enable persistent mode until the database location, backup/restore, retention, access controls and pilot governance have been reviewed. The application deliberately fails closed for authenticated users who have no configured role.

### Verification state

GitHub Actions has started the focused NEMA-AGORA checks for the latest implementation commit. Final acceptance still requires the workflow to complete successfully and manual OIDC testing with one account per role.

## Phase 5 implementation: operational resilience

The next operational layer is now implemented in the pilot branch:

- SQLite backups use the SQLite online backup API rather than copying a live database file byte-for-byte.
- Source and resulting backup files are checked with SQLite `integrity_check`.
- Backups use a predictable UTC filename and a bounded retention count (1–3650 files).
- Restore is denied unless the caller explicitly confirms the destructive action.
- The admin console creates a fresh safety backup before a confirmed restore.
- Administrative backup/restore actions are recorded separately from case audit events.
- The admin console is unavailable to demo-mode or non-admin users.

Deployment settings are explicit:

```toml
[nema_agora]
mode = "persistent"
database_path = "/approved/persistent/location/nema_agora.sqlite3"
backup_dir = "/approved/backup/location"
backup_retention = 7
```

Do not treat a local backup directory as a complete disaster-recovery strategy. A production pilot should additionally use an independently protected backup destination, test restoration periodically, define retention with the supervisor/institution, and monitor backup failures.


## Phase 8: Evidence Intelligence

The pilot now includes a deterministic, explainable evidence-intelligence layer
for authorised reviewer/coordinator/admin roles. It can produce neutral
extractive summaries, keyword-supported category suggestions, review-priority
advisories and duplicate candidates.

These outputs are **advisory only**. Every analysis requires human review and
does not establish environmental truth, illegality, urgency, regulatory
priority or enforcement action. Model-based AI is intentionally not enabled
until a labelled evaluation set, data governance and an approved model/data
handling plan exist.


## Phase 10: Reviewer Copilot & Human Evaluation

Phase 10 adds a structured reviewer workspace on top of the evaluated deterministic intelligence foundation. The copilot:

- surfaces only evidence fields actually supplied in the observation;
- presents quality signals, category guidance and duplicate candidates;
- asks uncertainty questions and provides a reviewer checklist;
- binds every brief to the source case ID and a versioned copilot contract;
- captures accepted, rejected or corrected reviewer feedback for future evaluation;
- records persisted analysis and feedback events in an auditable intelligence trail.

Reviewer feedback is evaluation data, not a workflow command. It never changes case status, merges records, verifies an allegation, declares illegality, dispatches an emergency response or triggers enforcement. No external LLM/API provider is enabled by this phase.

## Phase 9: AI evaluation and decision-support gate

Phase 9 establishes the measurement and safety layer before any live model
provider is connected. Synthetic/human-labelled evaluation fixtures support
category accuracy, duplicate precision/recall/F1 and human-labelled summary
faithfulness. Advisory outputs are checked for prohibited autonomous decision
fields and must preserve the source case ID with `human_review_required=true`.

No LLM provider, API credential or external data transfer is enabled by this
phase. A provider-neutral adapter contract is present so future models can be
evaluated without coupling the core workflow to a specific vendor.
