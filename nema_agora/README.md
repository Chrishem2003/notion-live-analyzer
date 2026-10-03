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
- Optional latitude/longitude and a simple map.
- CSV export and basic process metrics.
- Clear warnings about prototype status, privacy and unverified observations.

## Important limitations

- Data is stored only in Streamlit session state; it is not durable storage.
- No authentication or role-based authorisation is implemented yet.
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

1. Add isolated unit tests for data validation and record-state transitions.
2. Agree pilot scope, site, supervision, consent and data-handling rules.
3. Design a persistence layer only after the data model and access controls are reviewed.
4. Add authentication and audit logging before multi-user testing.
5. Test accessibility, low-bandwidth behaviour, backups and CSV export.
6. Validate budget assumptions and grant eligibility with the official NEMA call.

## Project links

- Applicant LinkedIn: https://www.linkedin.com/in/chris-shem-435166314
- Existing demo: https://notion-live-analyzer-w6ckned7rqd4gb8oppjjke.streamlit.app/
- Research planner: https://sleet-spectacles-fd3.notion.site/Bio-Research-Enterprise-Research-Planner-35f9142806c6805286a5c6767a7c9cfd?pvs=143
