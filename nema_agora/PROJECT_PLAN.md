# NEMA-AGORA: Six-Month Pilot Plan

## Objective

Pilot and evaluate a structured digital workflow for recording, reviewing, spatially organising and tracking selected environmental observations. The funded phase is a pilot, not a nationwide production platform.

## Scope

### Included in the first pilot

- Environmental observation form.
- Case identifier, category, date, site label, description and optional coordinates.
- Reviewer status and notes.
- Basic map/dashboard and CSV export.
- User testing, data-quality checks, evaluation and final report.

### Deferred to later phases

- Persistent database and multi-user authentication (must follow security design).
- Official integrations with NEMA, ELMIS or SWIMS.
- SMS/USSD/IVR, remote sensing, wildlife/eDNA, IoT, climate prediction and oil-spill modelling.
- Automated regulatory or enforcement decisions.

## Timeline

| Month | Work | Evidence / deliverable |
|---|---|---|
| 1 | Confirm academic supervisor, pilot site, stakeholders, data permissions and evaluation protocol. | Scope note, stakeholder map, data-handling protocol. |
| 2 | Implement and test observation form, record identifier and status workflow. | Working MVP and test log. |
| 3 | Add map, CSV export, process metrics and documentation; review risks. | Demonstration build, user guide, test report. |
| 4 | Run a small, permissioned user test with synthetic or consented records. | Feedback log and pilot dataset. |
| 5 | Operational resilience: authenticated persistence, backup/restore, retention and admin audit. | Security review, recovery test and operations log. |
| 6 | Quality/governance gate: deterministic validation, duplicate suspicion, role matrix and data-handling controls. | Quality report, governance checklist and role-by-role test evidence. |
| 5 | Fix priority issues, repeat testing and provide user orientation. | Updated build and validation summary. |
| 7 | Evaluate indicators, document costs/limitations and prepare final report. | Technical report, financial report and next-phase plan. |

## Suggested pilot indicators

- At least 10 end-to-end workflow test cases documented.
- At least 80% of valid pilot records complete all mandatory fields.
- At least 90% of sampled records have a clear status and review history.
- At least 8 consenting users provide structured feedback, subject to permission and recruitment feasibility.
- Final technical and financial report completed by Month 6.

Targets are proposed and must be adjusted if site access, recruitment or grant conditions change. Do not claim environmental improvements without a credible baseline and appropriate evidence.

## Stakeholders to approach (not confirmed partners)

- NEMA Research and Innovations Unit or relevant technical staff.
- Muni University academic supervisor and relevant staff.
- District/local-government environment officers at an agreed site.
- Community participants, student groups or environmental organisations.
- GIS/software/data-protection mentors.

Do not describe any organisation as a confirmed partner without its consent and evidence of agreement.

## Risk controls

- Keep the MVP narrow; prevent scope creep.
- Use synthetic data until permissions and consent are clear.
- Treat user submissions as unverified observations.
- Minimise personal data and protect sensitive locations.
- Do not connect to official systems without written permission.
- Document receipts, test results, issues and budget use.


## Current engineering gates

Before any real-user pilot, the build should demonstrate:

1. Every authenticated user resolves to a server-side role or is denied.
2. Ownership is derived from the trusted principal, not submitted form data.
3. Every accepted observation receives deterministic quality flags.
4. Duplicate suspicion is a review signal, never an automatic deletion or environmental finding.
5. Personal-data intake, urgent-incident handling and official integrations remain disabled by governance policy.
6. Backup and restore have been exercised successfully in the target deployment environment.
7. The role-permission matrix has automated tests and manual verification evidence.
8. Supervisor/institutional approval and data-handling arrangements are documented before real-user use.


## Phase 8 — Evidence Intelligence & Human-in-the-Loop

The intelligence layer is intentionally advisory and explainable. It does not
make regulatory, enforcement, environmental-truth or emergency decisions.

Implemented foundation:

- Neutral extractive summaries that do not invent facts.
- Keyword-supported category suggestions with visible matched terms.
- Review-priority advisories derived only from pilot fields and quality state.
- Deterministic duplicate candidates linked to existing quality heuristics.
- Mandatory human-review signal in every analysis result.
- Principal-bound `intelligence:use` permission for reviewer/coordinator/admin roles.
- Streamlit evidence-intelligence workspace with rationale and safety notices.

Next intelligence gate:

1. Compare deterministic outputs with a labelled pilot evaluation set.
2. Measure false positives/false negatives for duplicate and category suggestions.
3. Add an optional model adapter only after data governance and evaluation are approved.
4. Keep model outputs separate from stored facts and require human acceptance before
   any workflow state changes.
5. Never use the intelligence layer as an autonomous enforcement or regulatory engine.


## Phase 10 — Reviewer Copilot & Human Evaluation

Implemented reviewer-support layer:

1. Structured copilot briefs are derived from the existing deterministic analysis.
2. Evidence facts are explicitly labelled by source field; the copilot does not invent evidence.
3. Uncertainty questions and a bounded reviewer checklist keep human judgement central.
4. Every brief carries a source case ID and a versioned copilot contract.
5. Reviewer feedback supports accepted/rejected/corrected evaluation labels without changing workflow state.
6. Persisted analysis and feedback events are stored separately from case facts for audit/evaluation.
7. Reviewer/coordinator/admin permissions are required for copilot use and feedback; submitters remain denied.

### Phase 10 safety gate

- AI/copilot output is advisory only.
- No autonomous status transitions, enforcement, regulatory decisions or emergency dispatch.
- No external model provider or data transfer is enabled.
- Feedback notes must avoid personal/confidential information.
- Before a live model adapter: approve data governance, establish a labelled evaluation set, measure performance, and review model/provider handling.
