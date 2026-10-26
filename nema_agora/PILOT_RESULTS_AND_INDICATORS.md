# NEMA-AGORA Pilot Results, Indicators, and Verification Plan

Status: proposed measurement contract for the pilot. This document defines how results should be measured; it does not assert that any target has already been achieved or that any pilot, gateway, institutional partnership, or deployment is active.

## Why this exists

The pilot needs indicators that can be reproduced from system records and independently checked. A feature is not considered operational merely because a UI screen or configuration option exists. Each reported result must identify its period, denominator, source data, known limitations, and verification artifact.

## Phase alignment

- **Phase A — trustworthy data foundation:** identity and authorization, provenance, timestamps, storage readiness, auditability, privacy, and synthetic-test coverage.
- **Phase B — environmental intelligence:** satellite observations, change candidates, confidence and uncertainty, spatial thresholds, and independent ground-truth evaluation.
- **Phase C — operational workflows:** case/alert triage, community reporting and messaging integrations, officer dashboard, review and escalation.
- **Phase D — evaluation and dissemination:** performance evaluation, reproducible technical reporting, policy brief, workshops, and independently verifiable outputs.

Phase A is a gate for sensitive case data and accountable workflows. Remote sensing and mobile gateway work can be prototyped in parallel with synthetic/sample data, but must not be described as operational until end-to-end checks pass.

## Result 1 — Automated spatial change detection

**Intended result:** a tested change-detection pipeline for explicitly defined pilot wetland catchments.

### Indicators and definitions

1. **Spatial infringement alert tickets generated per calendar month**
   - Count distinct alert IDs created during the reporting month.
   - Report separate counts for raw candidates, deduplicated alerts, alerts accepted for officer review, and alerts closed after verification.
   - Do not equate more alerts with better performance; duplicate and false-positive rates must be reported alongside volume.
2. **Recall for reference changes larger than 0.1 hectares**
   - Numerator: independently ground-truthed reference changes above the threshold that the pipeline detected within the pre-agreed time window.
   - Denominator: all eligible, independently verified reference changes above the threshold in the evaluation set.
   - Report recall as a percentage with sample size and a confidence interval. A 100% result is meaningful only for the stated evaluation set and conditions, not as a universal guarantee.
3. **Precision / false-positive burden**
   - Numerator: evaluated alerts confirmed as relevant changes.
   - Denominator: all evaluated alerts.
   - Report false positives by likely cause where possible (seasonality, cloud/shadow, water-level fluctuation, classification error, duplicate alert).
4. **Timeliness and coverage**
   - Record observation acquisition date, processing date, alert creation date, usable-area coverage, cloud/shadow exclusions, and data gaps.
   - Report the percentage of the pilot area and period for which usable observations were available.

### Evaluation protocol

- Define pilot catchment boundaries, land-cover/change classes, the meaning of “unauthorized,” the reference period, and the operational response window before scoring.
- Treat 0.1 hectares as 1,000 square metres. Specify how polygons are measured, projected, and filtered for area.
- Store source imagery/provider, acquisition date, processing version, parameters, geometry, score/confidence, and provenance for each candidate.
- Compare alerts with independent field inspections or a documented reference dataset. Keep tuning samples separate from the final evaluation set where feasible.
- Distinguish “detected change candidate” from “verified infringement” and from an official enforcement finding. Satellite output alone must not make a legal determination.
- Record known limitations including cloud cover, revisit intervals, seasonal variation, mixed pixels, georegistration error, and changes not visible at the available resolution.

### Means of verification

Versioned processing logs and outputs, source-data identifiers, alert/case IDs, reference-site register, field inspection reports, evaluation scripts/results, and a reproducible summary showing denominators and exclusions.

### Acceptance gate

Do not claim the 100% target unless every eligible reference change in the declared evaluation set was detected, the denominator and exclusions are published, and independent verification supports the result. Always publish precision, sample size, coverage, and limitations beside recall.

## Result 2 — USSD/SMS community reporting

**Intended result:** a secure, privacy-aware multi-channel reporting service for an explicitly defined pilot zone.

### Indicators and definitions

1. **Unique community users onboarded**
   - Count unique, deduplicated user records that completed the defined consent and onboarding process during the pilot.
   - Report community members and local council leaders separately where appropriate. Avoid collecting unnecessary identity details.
   - Target: at least 500 successfully onboarded users in the pilot zone; this remains a target until verified.
2. **Reporting activity**
   - Count valid reports submitted, reports accepted by validation, duplicate/spam reports, and reports successfully linked to a case or triage queue.
   - Report unique active reporters separately from total submissions.
3. **Gateway delivery and availability**
   - Report submitted, accepted by provider, delivered, failed, timed out, and unknown-status transactions separately.
   - Provider acceptance is not proof of handset delivery or user receipt. Retain provider transaction IDs and timestamps without exposing credentials or unnecessary personal data.
4. **Operational response**
   - Measure median and 90th-percentile time from report receipt to triage, plus the percentage triaged within the agreed service window.

### Implementation and verification gates

- Treat Africa's Talking, USSD *144#, and SMS as planned integrations until credentials, shortcode/USSD code allocation, account configuration, and end-to-end tests have been verified.
- Do not send live messages to real users during tests without explicit pilot authorization and consent. Use provider sandbox/mock adapters first.
- Use consent language, data minimization, rate limiting, spam controls, abuse handling, retention rules, and an accessible non-USSD alternative where practical.
- Means of verification: provider transaction/delivery logs, anonymized or pseudonymized user metrics, onboarding event records, report/case linkage records, consent/retention documentation, and test reports.

## Result 3 — Regional officer compliance dashboard

**Intended result:** an interactive dashboard backed by governed APIs and reproducible spatial/compliance queries.

### Indicators and definitions

1. **Query and visualization latency**
   - Target: under 2 seconds for the agreed spatial queries and interactive visualizations.
   - Define the benchmark query set, dataset size, geographic extent, hardware/service tier, concurrency, cache state, and test duration before measurement.
   - Report p50, p95, and p99 latency; report errors/timeouts separately. A mean or a single warm-cache result is not sufficient.
2. **Reliability**
   - Report successful request rate, timeout/error rate, API availability, and data freshness.
3. **Usability**
   - Use task-based evaluation with representative officers: completion rate, time to complete common tasks, accessibility issues, and user feedback.
4. **Evidence traceability**
   - Every displayed compliance count or map layer should identify its reporting period, data source, refresh time, filters, and whether items are candidate, under review, verified, or formally determined.

### Means of verification

Automated load-test results, timestamped application/API telemetry, query plans or profiling output where appropriate, versioned benchmark datasets, error logs, and structured user evaluation results.

## Result 4 — Evaluation and dissemination

**Intended result:** independently reviewable technical results and documented dissemination.

### Deliverables and evidence

- One comprehensive technical report that describes the architecture, evaluation methods, datasets, results, limitations, security/privacy controls, and reproducibility instructions.
- One policy brief prepared for submission to NEMA. Record submission date, recipient/channel, and acknowledgement or formal receipt if obtained.
- One workshop planned for Muni University. Count it as held only after the event occurs and retain agenda, proceedings/materials, attendance evidence collected appropriately, and feedback summary.
- Do not imply endorsement, acceptance, or institutional partnership without documented confirmation.

**Means of verification:** versioned reports and briefs, publication/submission records, formal receipt where provided, workshop agenda/proceedings, appropriately protected attendance records, and feedback summaries.

## Cross-cutting evidence and reporting rules

Every indicator record should include:
- indicator ID and definition/version;
- reporting period and timezone;
- numerator, denominator, units, exclusions, and calculation method;
- source system and stable record references where available;
- data freshness, collection method, and responsible reviewer;
- result, target, status (not_started, in_progress, measured, verified, or blocked);
- verification artifact location, reviewer/date, caveats, and corrective action.

Status rules:
- **Not started:** no implementation evidence.
- **In progress:** partial implementation or integration exists, but acceptance tests are incomplete.
- **Measured:** a defined metric was calculated from identified data.
- **Verified:** the method and evidence were independently reviewed against the stated acceptance criteria.
- **Blocked:** a prerequisite, access, data, deployment, or governance decision prevents a valid test.

Never convert an absent metric into zero, and never display a target as an achieved result. Preserve synthetic/demo data labels. Keep secrets, raw phone numbers, and unnecessary personal information out of reports and application logs.

## Recommended build order

1. Complete Phase A authorization, owner scoping, provenance, storage and audit checks.
2. Add a versioned indicator registry and synthetic test fixtures so each metric has a definition and an honest status.
3. Build a repeatable satellite-evaluation harness before claiming operational detection performance.
4. Add USSD/SMS provider adapters behind a disabled-by-default feature flag; validate with mocks/sandbox before any live pilot.
5. Benchmark the officer dashboard against a defined workload and report percentile latency.
6. Generate reports only from measured/verified indicator records, with missing evidence and limitations visible.

This is a measurement and implementation plan, not evidence that any target has been achieved.

## Phase 191 — measurement evidence validation

The workspace now has a structural validator for individual measurement records in `nema_agora/indicator_evidence.py`, surfaced in the single-page Pilot metrics workspace. A user may upload a JSON record and receive a validation result without changing the registry or persisting the submitted record.

The validator requires the record to match a registry indicator and checks:
- ISO reporting dates and a timezone-aware calculation timestamp;
- a finite numeric value and exact unit match;
- a non-empty set of unique source-record IDs;
- an evidence reference, SHA-256 artifact digest, and method version;
- numerator/denominator presence and arithmetic consistency for ratio-style indicators;
- independent reviewer metadata and an accepted review outcome for records labelled `verified`.

A passing result is explicitly structural only. It does not authenticate the evidence bytes, validate source ownership, authenticate a reviewer, or establish institutional acceptance. Registry statuses remain unchanged; evidence validation is not evidence ingestion or persistence.


## Phase 192 — evidence artifact byte-integrity check

The in-memory measurement validator now optionally accepts the exact evidence artifact bytes and computes SHA-256 itself. When bytes are supplied, the upload is rejected if its digest differs from the measurement record's declared `evidence_sha256`. The single-page workspace exposes a second uploader for the artifact; it never claims a digest check when the artifact is absent. Tests cover matching bytes, mismatch rejection, and the missing-artifact case.

A digest match establishes byte consistency against the declared digest, not truth, source authenticity, authorship, legal status, or reviewer identity. Both uploads remain session-only; there is still no durable ledger write path, and indicator registry statuses are not promoted automatically.
