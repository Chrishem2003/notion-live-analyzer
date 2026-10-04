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


## Phase 11 — Pilot Intelligence Observatory

Phase 11 converts the Phase 9 evaluation foundation and Phase 10 reviewer feedback trail into measurable readiness evidence.

### Implemented
- Transparent observatory snapshot with labelled readiness gates.
- Feedback volume and correction-rate measurement.
- Category accuracy, duplicate F1 and summary-faithfulness gates.
- Principal-bound service access and a dedicated Streamlit observatory surface.
- Conservative `NOT_READY` default when evidence is insufficient.

### Readiness policy
The baseline pilot gate requires:
- at least 25 labelled evaluation cases;
- at least 20 reviewer feedback records;
- category accuracy ≥ 80%;
- duplicate F1 ≥ 80%;
- summary faithfulness ≥ 90%.

A passing snapshot means **READY_FOR_REVIEW**, not production approval, regulatory validation, NEMA endorsement, or permission to automate decisions.

### Next gate
Before connecting a live external or local model:
1. collect a larger, diverse, human-labelled evaluation set;
2. inspect false positives, false negatives and correction patterns;
3. establish data-retention and model-provider governance;
4. run a controlled shadow-mode comparison;
5. require explicit human approval before any model output can influence workflow.


## Phase 12 — Controlled AI Shadow Mode

Phase 12 introduces a strict shadow boundary for model evaluation. A model can analyse a pilot case beside the existing human workflow, but its output is isolated from the case record and workflow engine.

### Implemented

- Provider-neutral shadow execution contract in `nema_agora/shadow.py`.
- Deterministic local adapter for exercising the pipeline without external model/API data transfer.
- Safety validation through the Phase 9 advisory-output contract.
- Source-case binding, mandatory human review and bounded error capture.
- Provider/model-version and latency capture for reproducibility.
- Separate SQLite `shadow_runs` storage and audit trail.
- Principal-bound `intelligence:shadow` permission for reviewer/coordinator/admin roles.
- Streamlit shadow workspace with run history and explicit workflow-isolation messaging.
- Tests for safe output, unsafe-output rejection, latency capture, authorization and persistence.

### Shadow-mode rule

The shadow result is **evaluation evidence only**. It cannot:

- change observation status or review notes;
- create, merge, delete or overwrite observations;
- declare environmental truth, illegality or an official incident status;
- trigger enforcement, emergency dispatch or external reporting;
- connect to NEMA, ELMIS, SWIMS or another official system.

The default adapter is deliberately deterministic and local. It is a test harness, not evidence that an external AI model has passed evaluation.

### Next gate

1. Collect a diverse labelled pilot set and reviewer feedback.
2. Run the same cases through human judgement, deterministic baseline and an approved model adapter.
3. Measure agreement, false positives/negatives, corrections, latency and failure rates by model version.
4. Add calibration and slice-level analysis before considering any model for limited pilot use.
5. Keep human approval mandatory for every workflow-affecting decision.


## Phase 13 — AI Evaluation Laboratory

Phase 13 turns the shadow pipeline into a reproducible evaluation laboratory. The laboratory is deliberately separated from live case workflow and does not claim that an AI model is safe, accurate or approved merely because a run completed.

### Implemented

- nema_agora/lab.py provides versioned labelled cases and provider-neutral adapter execution.
- Every adapter output is checked against the Phase 9 safety contract before metrics are calculated.
- Source-case binding prevents an adapter from returning results for another case.
- Category accuracy is measured only on cases with a valid category prediction.
- Duplicate precision, recall and F1 are measured from explicit human labels.
- Error rate and mean latency are recorded for every adapter.
- Optional confidence values are evaluated with Brier score when the adapter supplies a bounded 0–1 confidence.
- Dataset slices are evaluated separately so aggregate scores do not hide weak subgroups.
- Unsafe adapter outputs fail safely and remain isolated from observations.
- Evaluation runs are persisted separately with run ID, actor, dataset version, timestamp and immutable result JSON.
- A dedicated Streamlit Evaluation Laboratory is available to reviewer/coordinator/admin roles.
- The only enabled adapter is the local deterministic baseline. No external model/API is silently connected.
- The laboratory requires human-labelled cases; it does not manufacture ground truth.

### Readiness rule

The baseline laboratory status is NOT_READY unless there are at least 25 labelled cases, zero adapter execution errors, category accuracy of at least 80%, and duplicate F1 of at least 80% for every evaluated adapter.

READY_FOR_REVIEW means the evidence meets these engineering thresholds. It is not production approval, environmental validation, regulatory authority, NEMA endorsement, or permission for autonomous decisions.

### Evaluation discipline

Summary-faithfulness labels are retained as human-label metadata and reported as label coverage; the laboratory does not treat a model's own self-reported faithfulness as ground truth. Human review must supply the actual summary-quality judgement.

### Next gate

1. Build a diverse, permissioned labelled dataset with documented annotation rules.
2. Add inter-reviewer agreement and adjudication for disputed labels.
3. Add an explicitly approved second adapter and run identical cases side-by-side.
4. Add regression thresholds to CI for fixed benchmark fixtures.
5. Review error slices, confidence calibration, latency and failure modes before any limited pilot model is considered.
6. Keep workflow-changing decisions behind explicit human approval.


## Phase 14 — Human Annotation & Dataset Governance

Phase 14 establishes the human-labelled evidence layer required for credible AI evaluation.

### Implemented
- Annotation domain model with strict dataset-version and case binding.
- One independent annotation per annotator, case and dataset version.
- Reviewer-facing Annotation Studio with blind peer-label isolation.
- Optional human summary-faithfulness judgement; no model self-report is treated as ground truth.
- Pairwise category observed agreement and Cohen's kappa.
- Duplicate-label agreement.
- Explicit disagreement detection.
- Coordinator/admin adjudication with required rationale.
- Independent annotations are immutable records; adjudication never overwrites them.
- Authenticated principal binding and deny-by-default annotation permissions.
- Annotation data is isolated from observation workflow transitions.
- Dedicated Streamlit page pages/21_NEMA_AGORA_ANNOTATION_STUDIO.py.

### Governance rules
- Use only synthetic, permissioned or otherwise approved records.
- Do not include personal/confidential data in annotation notes.
- Annotators must label independently before seeing peer labels.
- Disagreements are reviewed rather than silently averaged away.
- Adjudication must record who adjudicated, what final label was selected and why.
- Agreement is evidence about annotation consistency, not proof of environmental truth.

### Next evaluation gate
Build a sufficiently diverse labelled benchmark, document annotation guidelines, run independent double annotation, adjudicate disagreements, then freeze a dataset version before comparing a real AI adapter against the deterministic baseline.


### Phase 14 readiness gates

The Annotation Studio now exposes a dataset-process gate. It requires:
- at least 25 labelled cases;
- at least two independent annotators;
- category Cohen's kappa of at least 0.80;
- all detected disagreements explicitly adjudicated.

A READY_FOR_REVIEW result means the annotation process has met these engineering thresholds. It does not certify that labels are correct, representative, unbiased, legally sufficient, or suitable for regulatory decisions.


Phase 14 was tightened after review: the readiness gate now requires at least 25 distinct cases to have two independent annotations, measures every available annotator pair, and uses the minimum pairwise category Cohen's kappa rather than silently selecting only one pair. This prevents a strong pair from masking a weak annotator pair.


## Phase 15 — Controlled Model Comparison

Phase 15 establishes the model-to-model evidence gate before any AI provider is allowed near pilot workflow.

### Implemented
- Frozen dataset manifest with version, ordered case IDs and SHA-256 fingerprint.
- Provider-neutral side-by-side adapter execution on identical cases.
- Existing safety contract enforced for every model output.
- Fail-closed handling for unsafe, malformed and cross-case outputs.
- Category accuracy and macro precision/recall/F1.
- Duplicate precision/recall/F1 and explicit false-positive/false-negative counts.
- Human summary-faithfulness label coverage/rate.
- Optional confidence Brier score and confidence coverage.
- Latency and failure measurement.
- Slice-level metrics, model disagreement and baseline regression deltas.
- Separate immutable comparison-run persistence and authenticated service access.
- Dedicated Streamlit comparison laboratory.
- Role permission intelligence:comparison for reviewer/coordinator/admin; submitters denied.

### Readiness gate
A comparison is READY_FOR_REVIEW only when the frozen benchmark contains at least 25 cases, every compared adapter has zero execution failures, category accuracy is at least 80%, and duplicate F1 is at least 80%. These thresholds are engineering evidence gates only. They do not establish environmental truth, model fairness, regulatory compliance, NEMA endorsement, production safety or autonomous-decision permission.

### External-model gate
No external model is enabled by default. Before adding one, document the provider, model version, data handling, retention, cost, geographic processing implications, failure behaviour and approval authority. Run it only against the frozen benchmark and keep its outputs isolated from live workflow. A model must never change case status, enforcement state, official reporting or emergency response.


## Phase 16 — Benchmark Governance & Model Admission Gate

Phase 16 establishes the governance boundary between controlled model comparison and controlled shadow eligibility.

### Implemented
- Versioned ModelAdmissionPolicy with minimum benchmark, category accuracy, duplicate F1 and annotation kappa thresholds.
- Explicit ModelCandidate metadata covering provider, exact model version, adapter, intended use, data handling, retention, processing location and failure behaviour.
- Evidence-bound admission decisions tied to the exact dataset version, manifest SHA-256 and comparison run ID.
- Exact provider/model-version/adapter matching against the selected comparison evidence.
- Annotation readiness and unresolved-disagreement gates.
- Zero-failure, category-accuracy and duplicate-F1 gates.
- Explicit human-review safety contract checking for comparison outputs.
- Authenticated coordinator/admin-only admission permission.
- SQLite-backed admission history with policy version and rationale.
- Dedicated Model Governance page.

### Decision semantics
The only positive decision is ADMITTED_FOR_CONTROLLED_SHADOW. This means a candidate may participate in isolated advisory shadow evaluation under human review. It does not mean production approval, NEMA endorsement, regulatory authorization, environmental truth, enforcement authorization, emergency response authorization, official reporting permission or autonomous decision authority.

### Evidence binding
Admission must reject stale or mixed evidence. Dataset version, manifest hash, comparison run ID, provider, model version and adapter name must all match the selected evidence bundle exactly.

### Next gate
Introduce a real external model only as an explicitly documented candidate, evaluate it against the frozen benchmark, and route its result through the same Phase 16 admission gate before controlled shadow use.


## Phase 26 — Controlled Pilot Readiness Gate

Phase 26 consolidates the evidence produced by the evaluation, governance,
shadow, provenance, field, impact, accessibility and reproducibility layers
into one conservative readiness review.

### Implemented
- Versioned fail-closed PilotReadinessPolicy.
- Minimum evidence coverage across the five Evidence Observatory domains.
- Minimum controlled-shadow run volume and Phase 18 healthy status.
- Shadow error-rate ceiling of 5%.
- Reproducibility-manifest presence and verified Git revision requirement.
- Explicit human-review and lifecycle-control checks.
- Dedicated controlled pilot readiness Streamlit page.
- Focused unit tests and CI compilation coverage.

### Decision semantics
The positive result is READY_FOR_CONTROLLED_PILOT_REVIEW. It only indicates
that the engineering/research evidence is sufficient to enter a
human-supervised controlled pilot review process. It is not NEMA endorsement,
regulatory authorization, environmental truth, environmental impact,
production approval, official reporting permission, enforcement authority or
emergency-response authorization.

### Next gate
Validate the readiness gate, then move into deployment hardening and a
controlled public demonstration track: automated manifest generation,
deployment smoke tests, synthetic demo data, accessibility verification,
operational runbooks and an award/demo evidence package.


## Phase 27 — Deployment & Demonstration Hardening

Phase 27 establishes a deterministic demonstration track so the system can be
shown end-to-end without mixing synthetic demo records with pilot evidence.

Implemented:
- reproducible synthetic demonstration dataset and fingerprint;
- explicit synthetic/non-persistent safety metadata;
- tests for deterministic and session-safe demo artifacts;
- demonstration hardening documentation;
- continued focused CI coverage.

Next: operational runbooks, automated deployment identity capture, deployment
smoke checks, demo reset controls, and an award-quality evidence package.


## Phase 27.5 — Award & Demonstration Evidence Package

Implemented:
- end-to-end synthetic observation → quality → intelligence → reviewer-support chain;
- deterministic dataset and evidence fingerprints;
- reproducibility manifest bound to an explicit Git revision;
- separation of demonstration evidence from persistent pilot evidence;
- safety assertions for the session-only demonstration path;
- dedicated demonstration evidence presentation/download surface.

This package demonstrates software behaviour on synthetic records only. It does not establish environmental impact, environmental truth, NEMA authorization, regulatory status, production approval, enforcement authority, or emergency-response authority.


## Phase 21 — Real Pipeline Strengthening (v2)

Completed after Phase 27 hardening:

- restored persistent FieldEvaluationStore compatibility;
- controlled six-scenario fixtures now execute the actual observation → quality → intelligence → reviewer-support chain;
- duplicate evaluation uses a real synthetic peer record and the existing duplicate heuristic;
- scenario assertions validate actual quality flags rather than manually injected outputs;
- human-review and non-autonomous safety contracts are explicitly checked;
- service-layer execution is principal-bound and persists the resulting evaluation evidence;
- Field Evaluation page now runs the full six-scenario suite and reports stored evidence;
- Phase 21 documentation records the v2 methodology and governance boundary;
- focused CI path/compilation coverage remains enabled.

Phase 21 results are software-behaviour evidence only and must not be presented as environmental truth, environmental impact, regulatory status, NEMA authorization, production approval, enforcement authority, or emergency-response authority.


## Phase 28 — Controlled Outcome Study

Implemented a paired outcome-analysis layer over the Phase 22 impact observations.

- Matches BASELINE and ASSISTED observations by scenario ID only.
- Excludes unmatched observations instead of fabricating comparisons.
- Reports assisted-minus-baseline deltas for review time, evidence completeness, duplicate detection, reviewer workload, correction rate, and end-to-end success.
- Produces a reproducible dataset fingerprint and policy version.
- Adds a dedicated Outcome Study page and focused CI compilation coverage.
- Keeps all conclusions bounded to software/workflow behaviour; no environmental impact, regulatory, NEMA, enforcement, emergency-response, or autonomous-decision claims are permitted.


## Phase 29 — Evidence Synthesis

Implemented an auditable evidence narrative layer with six bounded evidence domains and a claim → evidence → limitation matrix. Claims retain source identifiers, sample sizes, support status and limitations; synthesis identities are deterministic from canonical evidence inputs. Added authenticated Streamlit evidence synthesis page and focused CI coverage. This layer is research/engineering evidence only and cannot establish environmental truth, environmental impact, NEMA authorization, regulatory status, production approval, enforcement or autonomous decision authority.


## Phase 30 — Evidence Provenance Graph & Research Report

Implemented deterministic provenance lineage with parent and claim-support edges, explicit missing-parent/orphan-claim detection, and a machine-readable research report. Added authenticated evidence-report page, tests and focused CI coverage.

## Phase 31 — Research & Award Dossier

Implemented a human-reviewed dossier layer with Executive Summary, Technical Contribution, Evidence & Results, Governance & Safety, and Limitations & Next Steps sections. The dossier preserves claim/evidence references, limitations, review status and deterministic identity, and blocks publication readiness when claims are unlinked or lineage is broken. Added authenticated dossier page, tests, documentation and CI coverage.


## Phase 32 — Evaluation & Publication Control

Added a fail-closed publication control gate that checks report identity, linked claims, valid provenance graph, source coverage, limitations, sample-size validity and explicit human sign-off/rationale. A pass means documentation is approved by a human reviewer under the stated policy only; it does not publish externally or confer NEMA/regulatory/production authority. Added focused tests, authenticated review page, policy documentation and repaired CI page coverage for Phases 30–32.


## Phase 33 — Evidence Integrity & Audit Hardening

Added integrity checks for duplicate provenance IDs and event identities, missing lineage parents, graph node/edge integrity, graph fingerprint and identity verification, report-to-graph binding, duplicate/missing claim IDs, unresolved source references, and publication-decision/report binding. Added tests, an authenticated audit page, documentation, and focused CI coverage. Integrity is artifact consistency—not proof of environmental truth.


## Phase 34 — Tamper-Evident Audit Ledger

Added an append-only SQLite ledger with unique IDs, canonical JSON payloads, sequential entries, SHA-256 hash chaining, update/delete triggers, chain verification, and verified-head checkpoints. Added tamper/trigger/duplicate/checkpoint tests, authenticated ledger page, documentation and focused CI coverage. The threat model explicitly notes that privileged database-file access can rewrite local history; independent checkpoint protection is required for stronger assurance.


## Phase 35 — Independent Audit Verification & Recovery

Added read-only verification against a separately preserved checkpoint, portable checkpoint exports, detection of chain tampering and rollback/truncation, and a backup-comparison service API. The Audit Recovery page supports checkpoint export and upload-based verification. Phase 34 now fails closed above its 5,000-entry verification bound and acquires a SQLite immediate write lock before reading the append head to reduce concurrent-chain races. Checkpoint exports are not digitally signed and must be preserved independently; verification is integrity evidence only. No automatic restore, repair, or workflow mutation is performed.


## Phase 36 — Governed Audit Event Capture

Added a reusable capture service for allowlisted event types, deterministic idempotency keys, duplicate suppression/conflict detection, and metadata-only payload validation. Added an authenticated human-triggered capture page, focused tests, CI compile coverage, and operational documentation. The checkpoint-creation page and publication-gate decision page call the capture service at their actual decision boundaries. Other workflows are not claimed as automatically instrumented until connected explicitly.


## Phase 37 — End-to-End Governance Traceability

Implemented an explicit traceability validator from an originating event through provenance records, evidence graph, research report, human publication decision and governed audit event. The validator fails closed on broken or ambiguous identifiers, lineage failures, report/graph binding mismatches, unresolved claim sources, invalid publication decisions, failed ledger verification, and missing publication-gate audit coverage. Added deterministic trace fingerprints, structured error codes, tests, a read-only authenticated trace-bundle page, documentation and CI coverage.

The Phase 36 instrumentation boundary remains explicit: missing origin-event audit coverage is reported as a warning until that workflow is actually instrumented. Traceability is an engineering/research integrity control only; it does not establish environmental truth, NEMA authorization, regulatory status, production approval, enforcement authority, emergency response authority or autonomous decision authority.

### Next gate

Move from artifact-level traceability toward **Phase 38 — Governance Decision Ledger Integration**, connecting additional real workflow decision boundaries to the governed audit-event layer while preserving idempotency, privacy, human authority and fail-closed semantics.


## Phase 38 — Governance Decision Ledger Integration

Connected actual application decision boundaries to the governed audit-event layer. Evaluation completion, human shadow review, and human lifecycle decisions now emit metadata-only, deterministic, idempotent governed audit events through a reusable adapter. Added a read-only Governance Decision Ledger page, focused tests, CI coverage, and documentation. Checkpoint creation and publication-gate capture remain connected from Phase 36. Backup verification and access-denial event types are supported by the adapter but are not claimed as automatically instrumented until concrete workflow boundaries are wired.

The integration preserves human authority and fail-closed semantics: the audit layer records decisions already made; it never makes, changes, or infers governance decisions. Source decision stores and the audit ledger currently use separate SQLite writes, so reconciliation is required if the second write fails.

### Next gate

**Phase 39 — Governance Reconciliation & Exception Handling**: detect authoritative decision records that lack corresponding governed audit events and surface reconciliation exceptions for human review without silently repairing history.


## Phase 39 — Governance Reconciliation & Exception Handling

Added a read-only reconciliation engine comparing authoritative evaluation, human-review, and lifecycle decision stores with governed audit events. It detects missing and orphaned audit coverage, duplicate source decisions, ambiguous coverage, actor mismatches, decision/status mismatches, source-module mismatches, invalid source records, and invalid ledger verification. Results have deterministic reconciliation IDs/fingerprints and fail closed to CONTROL_REQUIRED on discrepancies. Added authenticated reconciliation page, focused tests, documentation, and CI coverage. No automatic repair, deletion, or rewriting of historical audit events is performed.

### Next gate

Phase 40 — Controlled Governance Exception Resolution: introduce an explicit human-governed workflow for investigating and resolving reconciliation exceptions without rewriting historical evidence.
\n\n## Phase 40 — Controlled Governance Exception Resolution\n\nImplemented an explicit human-governed resolution workflow for Phase 39 reconciliation exceptions. Resolutions are append-only GOVERNANCE_EXCEPTION_RESOLVED events with controlled exception identity, reconciliation fingerprint, outcome, reason code, authenticated actor role and policy version. Historical source decisions and prior audit events are never rewritten. Allowed outcomes are ACKNOWLEDGED, CORRECTED_AT_SOURCE, DUPLICATE_CONFIRMED, FALSE_POSITIVE and ESCALATED.\n\n## Phase 41 — Governance Exception Closure\n\nImplemented the closure layer that reconciles Phase 40 resolution events back to the current Phase 39 exception set. An exception is CLOSED only when the resolution matches the current reconciliation fingerprint and exact exception identity, uses a closeable outcome (CORRECTED_AT_SOURCE, DUPLICATE_CONFIRMED or FALSE_POSITIVE), and has independently preserved closure evidence identified by a stable evidence_id and valid SHA-256 evidence_hash. ACKNOWLEDGED remains REVIEW_REQUIRED and ESCALATED remains CONTROL_REQUIRED. Stale resolutions never close a newer reconciliation.\n\nAdded nema_agora/governance_exception_closure.py, pages/49_NEMA_AGORA_GOVERNANCE_EXCEPTION_CLOSURE.py, focused tests and Phase 41 documentation. The closure surface is read-only and never repairs, edits or deletes historical evidence.\n\n### Next gate\n\nPhase 42 should strengthen closure evidence provenance and operational reconciliation reporting while preserving append-only history, explicit human authority, privacy controls and fail-closed semantics.\n
## Phase 42 — Closure Evidence Provenance & Operational Reconciliation

Phase 42 strengthens the Phase 41 closure gate with an append-only evidence registry, exact provenance binding and an operational reconciliation report.

### Implemented
- Append-only closure_evidence registry with stable evidence IDs and SHA-256 hashes.
- Explicit evidence types and verification states.
- Binding to the current reconciliation fingerprint, exact exception identity and resolution event.
- Provenance reference retained alongside the evidence record.
- Fail-closed evaluation: unverified, stale, wrong, rejected or mismatched evidence cannot close an exception.
- Operational report for open, review-required, control-required and closed states, stale resolutions, missing evidence and unresolved critical exceptions.
- Authenticated read-only Phase 42 dashboard.
- Focused tests and CI compilation/smoke coverage.

### Governance boundary
Evidence supports closure evaluation; it never silently creates a closure decision. Historical observations, source decisions and audit events remain immutable. Phase 42 outputs are engineering/research governance evidence only and are not NEMA authorization, regulatory status, environmental truth, enforcement authority, emergency response authority or production approval.


## Phase 43 — Governance Evidence Integrity & Attestation

Implemented a fail-closed integrity and human-attestation layer over Phase 42 closure evidence.

### Implemented
- Evidence-registry integrity verification with duplicate, malformed, missing-field, policy-version and hash checks.
- Deterministic evidence-registry fingerprint so any changed current evidence snapshot invalidates prior attestations.
- Provenance completeness gate binding observation/reference identity, review decision, audit event, current reconciliation fingerprint, human resolution, closure evidence and derived closure identity.
- Append-only governance attestation registry with immutable attestation records.
- Explicit human attestation restricted to authenticated coordinator/admin principals through the `intelligence:attest` permission.
- Attestation states PENDING, ATTESTED, REJECTED, STALE and CONTROL_REQUIRED as derived governance states.
- Exact binding of attestation to reconciliation, evidence-registry and provenance fingerprints.
- Fail-closed stale-attestation behaviour when evidence, reconciliation or provenance changes.
- Authenticated Governance Integrity dashboard with human attestation control and read-only review for other authorized roles.
- Focused unit tests, compilation and Streamlit CI coverage.

### Governance boundary

Attestation is explicit governance evidence only. It does not authorize production, NEMA integration, regulatory action, enforcement, emergency response, environmental conclusions or autonomous decisions. Historical observations, source decisions, reconciliation records, closure evidence and audit events remain immutable.


## Phase 44 — Attestation Lifecycle Governance

Implemented a human-governed lifecycle over Phase 43 attestations using a
separate append-only lifecycle decision ledger.

### Implemented
- Explicit lifecycle states: PENDING_REVIEW, ACTIVE, REJECTED, REVOKED,
  EXPIRED, SUPERSEDED, STALE and CONTROL_REQUIRED.
- Human lifecycle decisions: APPROVE, REJECT, REVOKE and SUPERSEDE.
- Second-person separation of duties for approval/rejection: the lifecycle
  reviewer must differ from the original attester.
- Deterministic expiration evaluated against an explicit evaluation timestamp.
- Immutable lifecycle decision records with rationale, actor, role, policy and
  exact attestation identity.
- Conflict detection for multiple active attestations bound to the same exact
  integrity snapshot.
- Fail-closed lifecycle evaluation when current integrity/provenance evidence
  is invalid or the attestation is stale.
- Authenticated lifecycle dashboard with explicit human decision controls and
  read-only historical ledger visibility.
- Focused unit tests, compilation and Streamlit CI coverage.

### Governance boundary

Lifecycle state is governance evidence only. It never authorizes NEMA
integration, regulatory action, enforcement, emergency response, official
reporting, production deployment, environmental truth or autonomous decisions.
Phase 43 attestations remain immutable; lifecycle history is append-only.

### Next gate

Phase 45 should strengthen lifecycle provenance and decision accountability,
including exact decision-to-snapshot binding, supersession-chain validation,
reviewer/attester identity evidence, and an operational lifecycle evidence
report before any broader demonstration or pilot workflow expansion.


## Phase 45 — Lifecycle Provenance & Decision Accountability

Implemented an append-only provenance binding ledger connecting lifecycle decisions to the exact attestation, reviewer/attester identities, current reconciliation fingerprint, evidence-registry fingerprint, provenance fingerprint and supersession target. Historical bindings become stale when the current governance snapshot changes; identity and duplicate-binding mismatches fail closed. Supersession validation rejects missing targets, self-reference and cycles. The authenticated dashboard now derives the current snapshot from the live Phase 42/43 governance evidence chain rather than treating a historical binding as authoritative.

### Governance boundary
Phase 45 is an accountability and reproducibility control only. It does not authorize production, NEMA integration, regulatory action, enforcement, emergency response, official reporting or environmental truth. Historical decisions and evidence remain append-only.

### Next gate
Phase 46 — Governance Evidence Observatory: consolidate current attestation/lifecycle/provenance states into a read-only operational evidence surface with explicit coverage gaps, stale bindings, conflicts, supersession health and fail-closed status, without inventing or mutating governance decisions.


## Phase 46 — Governance Evidence Observatory

Implemented a read-only operational evidence surface over the current integrity, attestation, lifecycle and provenance layers. The observatory reports coverage gaps, stale/control-required lifecycle states, provenance failures and supersession-chain health without creating or mutating governance decisions.

### Governance boundary
EVIDENCE_COVERAGE_OK is an engineering evidence condition only. It is not NEMA authorization, regulatory status, environmental truth, production approval, enforcement authority, emergency response authorization or autonomous decision authority.

### Next gate
Phase 47 — Governance Evidence Reconciliation: add deterministic cross-layer consistency checks between attestation, lifecycle and provenance records so conflicting or orphaned accountability records are surfaced before broader pilot demonstration.


## Phase 47 — Governance Evidence Reconciliation

Implemented deterministic cross-layer reconciliation across Phase 43 attestations, Phase 44 lifecycle evidence, Phase 45 provenance bindings and the live governance snapshot. Findings include orphan records, duplicate bindings, lifecycle identity mismatches, provenance snapshot mismatches, validation failures and active lifecycle records without provenance bindings. The reconciler is read-only and fail-closed.

### Completion gate
Phase 47 is complete only after GitHub Actions verifies focused tests, compilation and Streamlit smoke for the new module and page. No green status is inferred from source inspection.

### Next gate
Phase 48 — Governance Evidence Casebook: produce a read-only, deterministic case-level view that groups every finding with its exact accountable artifacts, identities, fingerprints and human-review requirement without changing governance state.


## Phase 48 — Governance Evidence Casebook

Implemented a deterministic, read-only casebook that packages Phase 47 findings with related attestation, lifecycle decision, provenance binding, exact current snapshot and an explicit human-review requirement. Each case and the complete casebook receive deterministic SHA-256 fingerprints. The casebook never mutates governance state or implies NEMA authorization.

### Completion gate
GitHub Actions must verify focused tests, compilation and Streamlit smoke for Phase 48 before this phase is declared green.

### Next gate
Phase 49 — Governance Review Queue: derive a deterministic, read-only prioritization queue from casebook findings for authorized human reviewers, with explicit severity, aging, dependency and review-state signals.


## Phase 49 — Governance Review Queue

Implemented a deterministic, read-only prioritization layer over Phase 48 governance cases. The queue exposes severity, review requirement, aging and dependency signals, assigns stable positions, and fingerprints the complete queue against the current governance snapshot. It is strictly a human-review aid and cannot mutate governance state.

### Completion gate
GitHub Actions must verify focused tests, compilation and Streamlit smoke before Phase 49 is declared green.

### Phase 50 — Governance Review Workspace

Implemented an authenticated, read-only case investigation workspace over the Phase 49 review queue and Phase 48 casebook. The workspace exposes queue context, finding severity/age/dependency, accountable artifacts, lifecycle evidence, provenance validation state, exact current snapshot fingerprints and an explicit human-review requirement. Governance mutations remain outside this evidence surface.

### Governance boundary

The workspace is an investigation aid only. It does not change governance state, establish environmental truth, authorize NEMA integration, regulatory action, enforcement, emergency response, production approval or autonomous decisions.

### Completion gate

GitHub Actions must verify focused tests, compilation and Streamlit smoke before Phase 50 is declared green.

### Next gate

Phase 51 — Governance Review Decision Preparation: create a separate, human-governed preparation layer that assembles the evidence needed for an authorized reviewer to make an existing governance decision, without executing that decision automatically.


## Phase 51 — Governance Review Decision Preparation

Implemented a deterministic evidence-preparation layer over the Phase 50 read-only review workspace. It assembles the selected case, queue context, accountable artifacts, lifecycle evidence, provenance bindings and exact current snapshot for an authorized human reviewer.

### Governance boundary

Every package is explicitly marked NOT_DECIDED. This layer does not execute or record APPROVE, REJECT, REVOKE or SUPERSEDE decisions, mutate observations, change workflow state, establish environmental truth, authorize NEMA integration, enforcement, emergency response, production approval or autonomous decisions.

### Completion gate

GitHub Actions must verify focused tests, compilation and Streamlit smoke before Phase 51 is declared green.

### Next gate

Phase 52 — Governance Decision Execution Boundary: preserve the separation between evidence preparation and the existing human-governed lifecycle decision ledger, with explicit actor/role checks and fail-closed snapshot binding.


## Phase 52 — Governance Decision Execution Boundary

Implemented a fail-closed prerequisite validator between Phase 51 evidence preparation and the existing human-governed lifecycle decision ledger. It requires an explicit supported decision, actor identity, coordinator/admin role, an undecided preparation package and exact current snapshot equality. Successful validation is READY_FOR_HUMAN_EXECUTION only; execution_authorized remains false and no lifecycle decision is written.

### Governance boundary

The boundary does not approve/reject/revoke/supersede records, change observations or workflow state, establish environmental truth, authorize NEMA integration, enforcement, emergency response, production approval or autonomous decisions.

### Completion gate

GitHub Actions must verify focused tests, compilation and Streamlit smoke before Phase 52 is declared green.

### Next gate

Phase 53 — Decision Receipt & Audit Binding: produce an append-only, human-confirmed receipt around an already-executed lifecycle decision without making the receipt itself authoritative.


## Phase 53 — Decision Receipt & Audit Binding

Implemented an append-only evidentiary receipt layer for already human-executed lifecycle decisions. Receipts bind decision identity, reviewer identity, prepared-package fingerprint and exact current snapshot. UPDATE/DELETE are blocked by database triggers. Receipts never execute decisions and are not authoritative governance state.

### Next gate

Phase 54 — Governance Decision Audit Reconciliation: reconcile receipts against the authoritative lifecycle ledger and detect missing, orphaned, duplicated or mismatched decision receipts.


## Phase 54 — Governance Decision Audit Reconciliation

Implemented a read-only reconciliation layer between the authoritative Phase 44 lifecycle decision ledger and Phase 53 evidentiary receipts. It detects missing, orphaned, duplicate, identity-mismatched and stale-snapshot receipts. The authoritative lifecycle ledger remains unchanged and authoritative.

### Strategic platform roadmap reconciliation

The current implementation is a governance/evidence pilot foundation, not yet the full environmental intelligence platform originally envisioned. The following major product tracks remain explicitly deferred and must be built as separate, permissioned modules: remote-sensing spatial change analytics (Earth Engine/Sentinel-2 NDVI/NDWI), biological and water-quality aggregation, community USSD/SMS alerting, and a unified compliance analytics dashboard. These must be added without weakening the existing governance boundaries.

### Next gate

Phase 55 — Platform Capability Registry & Integration Roadmap: establish explicit capability contracts and implementation status for the environmental product tracks, so future builds can be measured against the original platform vision rather than accumulating governance layers alone.


## Phase 55 — Platform Capability Registry

Implemented the machine-readable roadmap registry that tracks the original environmental platform capabilities alongside the existing governance/evidence foundation. It covers observation, spatial intelligence, Sentinel-2 remote sensing, NDVI/NDWI, spatial-change evidence, water quality, biodiversity/eDNA, community USSD/SMS, community alerts, the unified environmental analytics dashboard, governance/evidence, and AI evaluation. Capability dependencies and statuses are validated fail-closed.

### Next gate

Phase 56 — Spatial Intelligence Foundation: establish geometry/AOI contracts, spatial observation records, coordinate validation and provider-neutral spatial analysis interfaces.


## Phase 56 — Spatial Intelligence Foundation

Implemented the provider-neutral spatial foundation required for environmental remote sensing and spatial-change analytics. Spatial observations use WGS84 (EPSG:4326), GeoJSON-compatible point geometry, deterministic fingerprints, source/capture metadata and optional accuracy. AOIs support district, wetland, watershed, protected-area and custom types. Validation is fail-closed for coordinates, CRS, identity, source and capture metadata. A provider-neutral analysis contract accepts evidence while rejecting autonomous regulatory conclusions.

No live Earth Engine or external spatial provider is connected in this phase.

### Governance boundary

Spatial analytics can surface candidate changes and evidence for human review. They do not establish illegality, environmental truth, regulatory status, enforcement action, emergency response or NEMA authorization.

### Completion gate

GitHub Actions must verify focused tests, compilation and Streamlit startup before Phase 56 is declared CI-green. No green status is inferred from source inspection.

### Next gate

Phase 57 — Sentinel-2 Remote Sensing Adapter: define imagery metadata, acquisition/cloud-quality contracts and a provider adapter boundary before connecting live imagery.


## Phase 57 — Sentinel-2 Remote Sensing Adapter

Implemented a provider-neutral Sentinel-2 imagery contract on top of Phase 56 spatial intelligence. The module validates scene/product identity, L1C/L2A collection, acquisition timestamps, WGS84 bounding boxes, cloud-cover quality and the initial B02/B03/B04/B08 optical band set. Valid scenes receive deterministic fingerprints and can be represented as remote-sensing evidence. A provider adapter boundary is present, but no live credentials or external network access is required.

### Governance boundary

Imagery and cloud-quality metadata are evidence inputs only. Sentinel-2 outputs do not establish environmental truth, illegality, regulatory status, enforcement action, emergency response or NEMA authorization.

### Completion gate

GitHub Actions must verify Phase 57 focused tests, compilation and Streamlit startup before this phase is declared CI-green. No green status is inferred from source inspection.

### Next gate

Phase 58 — NDVI / NDWI Analytics: derive transparent spectral indices from validated imagery inputs, with explicit quality handling and no automatic regulatory conclusions.


## Phase 58 — NDVI / NDWI Analytics

Implemented transparent, deterministic spectral-index calculations on validated Sentinel-2 optical inputs.

### Implemented
- NDVI using Sentinel-2 B08 NIR and B04 red reflectance.
- McFeeters NDWI using B03 green and B08 NIR reflectance.
- Explicit normalized-reflectance contract of [0, 1].
- Finite-input, required-band, zero-denominator and expected-range quality gates.
- Deterministic SHA-256 evidence fingerprints with formulas, source bands and quality assumptions.
- Read-only Streamlit demonstration using synthetic inputs.
- Focused tests, compilation and Streamlit CI coverage.

### Governance boundary

NDVI and NDWI are analytical measurements only. They do not establish deforestation, wetland loss, illegality, regulatory status, enforcement action, emergency response, NEMA authorization or environmental truth. Spatial/temporal change interpretation remains a human-reviewed evidence task.

### Completion gate

GitHub Actions must verify focused tests, compilation and Streamlit startup before Phase 58 is declared CI-green. No green status is inferred from source inspection.

### Next gate

Phase 59 — Spatial/Temporal Change Evidence: compare validated Sentinel-2 scenes and spectral-index observations across time and space, with explicit baseline and uncertainty handling.


## Phase 59 — Spatial/Temporal Change Evidence

Implemented deterministic baseline-versus-comparison change evidence from validated Sentinel-2-derived NDVI and McFeeters NDWI observations.

### Implemented
- Baseline/comparison scene identity and chronological validation.
- Optional minimum temporal-gap gate.
- Transparent per-index delta and absolute-delta calculations.
- Deterministic SHA-256 evidence fingerprint.
- Quality metadata and explicit human-review requirement.
- Fail-closed handling for missing/invalid indices, duplicate scenes and invalid chronology.
- Read-only Streamlit demonstration with synthetic observations.
- Focused tests, compilation and Streamlit CI coverage.

### Governance boundary

The engine reports candidate change evidence only. Index differences do not establish deforestation, wetland loss, illegality, regulatory status, enforcement action, emergency response, NEMA authorization or environmental truth.

### Completion gate

GitHub Actions must verify focused tests, compilation and Streamlit startup before Phase 59 is declared CI-green. No green status is inferred from source inspection.

### Next gate

Phase 60 — Spatial/Temporal Evidence Quality: add explicit AOI/grid identity, co-location checks and uncertainty/quality metadata before broader change-detection workflows.


## Phase 60 — Spatial/Temporal Evidence Quality

Implemented evidence-quality controls on top of Phase 59 candidate-change evidence.

### Implemented
- Stable baseline/comparison AOI identity.
- Stable baseline/comparison grid identity.
- Explicit spatial-alignment gate; only ALIGNED passes.
- Spatial-resolution validation.
- Cloud-cover and valid-pixel quality thresholds.
- Non-negative finite upstream-provided NDVI/NDWI uncertainty metadata.
- Deterministic SHA-256 quality evidence fingerprint.
- Fail-closed quality findings and a read-only Streamlit demonstration.

### Governance boundary

Passing the quality gate only means the evidence met defined engineering checks for human review. It does not establish deforestation, wetland loss, illegality, environmental truth, regulatory status, NEMA authorization, enforcement, emergency response or production approval.

### Completion gate

GitHub Actions must verify Phase 60 focused tests, compilation and Streamlit startup before Phase 60 is declared CI-green. No green status is inferred from source inspection.

### Next gate

Phase 61 — Broader Spatial Change Detection: introduce explicit change-detection policies and candidate generation over quality-approved spatial/temporal evidence while preserving human review and non-regulatory outputs.


## Phase 61 — Broader Spatial Change Detection

Implemented deterministic candidate generation over Phase 60 quality-approved spatial/temporal evidence. The phase adds explicit NDVI and McFeeters NDWI absolute-change thresholds, ANY/ALL/WEIGHTED rule modes, transparent reason codes, deterministic candidate IDs, and quality/uncertainty carry-forward. Detected candidates remain human-review evidence only.

### Governance boundary

Threshold detection does not establish deforestation, wetland loss, illegality, environmental truth, regulatory status, enforcement action, emergency response, NEMA authorization or production approval.

### Completion gate

GitHub Actions must verify Phase 61 focused tests, compilation and Streamlit startup before Phase 61 is declared CI-green. No green status is inferred from source inspection.

### Next gate

Phase 62 — Spatial Change Evidence Scoring & Review Queue Integration: strengthen candidate prioritisation with transparent evidence scoring and deterministic review-queue records.


## Phase 62 — Spatial Change Evidence Scoring & Review Priority

Implemented transparent engineering prioritisation for Phase 61 detected candidates. Scores combine configurable NDVI/NDWI magnitude with optional quality and uncertainty components, producing deterministic fingerprints and HIGH/MEDIUM/LOW priority tiers.

### Governance boundary

The score is not a calibrated probability, environmental-risk score, compliance score or regulatory finding. It cannot establish environmental truth, illegality, enforcement status, emergency conditions, NEMA authorization or production approval.

### Completion gate

GitHub Actions must verify Phase 62 tests, compilation and Streamlit startup before Phase 62 is declared CI-green. No green status is inferred from source inspection.

### Next gate

Phase 63 — Persistent Spatial Change Review Queue: create append-only candidate review records and connect analytical priority to the existing human-governed review workflow without autonomous decisions.

## Phase 63 — Persistent Spatial Change Review Queue

Implemented a persistent, append-only SQLite review queue for Phase 62 spatial-change priority outputs. The queue validates scored candidates, persists deterministic review-item IDs and fingerprints, prevents duplicate candidate records, carries AOI/grid identity, score components and reason codes, and blocks UPDATE/DELETE operations with database triggers. Queue records remain QUEUED and require a separate human-governed review workflow for any review outcome.

### Governance boundary

The queue is an analytical persistence layer only. It does not establish deforestation, wetland loss, illegality, environmental truth, regulatory status, enforcement action, emergency response, NEMA authorization or production approval. No autonomous review or regulatory decision is performed.

### Completion gate

GitHub Actions must verify Phase 63 focused tests, compilation and Streamlit startup before Phase 63 is declared CI-green. No green status is inferred from source inspection.

### Next gate

Phase 64 — Spatial Change Human Review & Audit Binding: connect queued analytical candidates to explicit human review outcomes and append-only audit evidence without granting autonomous regulatory authority.


## Phase 65 — Spatial Review Reconciliation & Evidence Integrity

Implemented a read-only reconciliation layer between the Phase 63 immutable spatial-change review queue and Phase 64 human-review audit evidence. It detects missing reviews, orphan reviews, duplicate reviews, queue-fingerprint mismatches, stale queue records and candidate-identity mismatches. Findings and the complete reconciliation result receive deterministic SHA-256 fingerprints; source records are never repaired or mutated.

### Governance boundary

Reconciliation is an evidence-integrity control only. It does not reinterpret human outcomes, establish environmental truth, wetland loss, deforestation, illegality, regulatory status, NEMA authorization, enforcement action, emergency response or production approval.

### Completion gate

GitHub Actions must verify Phase 65 focused tests, compilation and Streamlit startup before Phase 65 is declared CI-green. No green status is inferred from source inspection.

### Next gate

Phase 66 — Spatial Review Evidence Casebook & Provenance: package reconciled review evidence with exact queue and audit artifacts for human investigation and downstream evidence tracking.


## Phase 66 — Spatial Review Evidence Casebook & Provenance

Implemented deterministic evidence casebooks that package exact Phase 63 queue artifacts and Phase 64 human-review audit events, bound to the exact Phase 65 reconciliation fingerprint. The casebook recomputes audit-event fingerprints and fails closed on tampering, identity mismatch, queue-binding mismatch or non-unique review evidence.

### Governance boundary

The casebook is evidence packaging only. Human review outcomes remain human evidence and are not converted into environmental truth, regulatory findings, NEMA authorization, official reporting, enforcement, emergency response or production approval.

### Completion gate

GitHub Actions must verify Phase 66 focused tests, compilation and Streamlit startup before Phase 66 is declared CI-green. No green status is inferred from source inspection.

### Next gate

Phase 67 — Spatial Evidence Longitudinal Tracking: preserve case history across repeated observations and reviews without mutating historical evidence.


## Phase 67 — Spatial Evidence Longitudinal Tracking

Implemented immutable longitudinal evidence records for repeated spatial observations and reviews. Each history record binds the Phase 66 case fingerprint, candidate identity, AOI/grid identity, observation time, sequence and provenance, with an explicit predecessor fingerprint. Timeline construction detects duplicate records and broken chains without mutating historical evidence.

### Governance boundary

Longitudinal tracking preserves evidence history only. It does not infer environmental truth, legality, regulatory status, NEMA authorization, enforcement or emergency action.

### Completion gate

GitHub Actions must verify Phase 67 focused tests, compilation and Streamlit startup before Phase 67 is declared CI-green.

### Next gate

Phase 68 — Spatial Evidence Storage & Query Layer.
