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

- The public Streamlit page still stores data only in session state; the new SQLite repository module is an isolated foundation and is not connected to the UI.
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
4. Configure and test OIDC login using the secret template, then enforce the resolved principal and role policy at every UI and repository operation before using persistent storage in the UI.
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
2. Run focused CI and manual authentication tests with at least one account per role.
3. Add deployment-specific SQLite path, backup/restore, retention and monitoring configuration.
4. Connect the page to the repository only when an authenticated principal is present.
5. Add an operational admin/audit view and controlled export.
6. Validate low-bandwidth accessibility and pilot data-handling rules.
