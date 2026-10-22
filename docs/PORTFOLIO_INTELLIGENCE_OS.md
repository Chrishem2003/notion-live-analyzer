# Portfolio Intelligence OS — implementation baseline

## Purpose

Create one evidence-led operating layer across the user's products and repositories. It should help identify consequential problems, rank opportunities transparently, test demand cheaply, track delivery and economics, and learn from outcomes. It is not an autonomous authority and must not invent market demand, live telemetry, revenue, or successful deployments.

## Existing assets to coordinate

- **Notion Live Analyzer**: Streamlit research and analysis workspace; contains NEMA-AGORA, sovereign-intelligence, career, opportunity-feed, and reproducibility modules.
- **CHRISHEM AUTO-STUDIO**: workflow builder and execution reliability foundation. Its own progress review explicitly notes that staging/provider execution and several advanced workflow capabilities still need verification.
- **HACKFORGE / Ethical Hacking Guide**: cybersecurity education and isolated lab concept. Security configuration needs a separate fail-closed hardening pass before production use.
- **Bio-Research Enterprise in Notion**: intended research lifecycle from literature/protocols through intake, analysis, QC, and publication; workspace inspection awaits an active Notion connection.

## First working slice in this commit

- Add a Streamlit Portfolio Intelligence OS page to the existing Notion Live Analyzer application.
- Store opportunity records in the existing local SQLite database by default, with an environment-variable override.
- Rank opportunities using seven explicit 0–5 factors and a visible risk penalty.
- Require stronger evidence and a willingness-to-pay signal before the top recommendation can be a pilot.
- Track stage, next experiment, source URL, estimated price/cost, and simple break-even economics.
- Seed four editable starter hypotheses aligned with existing project capabilities and published global/Uganda research. Starter hypotheses are not validated markets.
- Add pure scoring tests and isolated SQLite persistence tests.

## Decision model

Positive weights: impact 20%, urgency 15%, feasibility 15%, willingness-to-pay evidence 20%, strategic fit 10%, evidence quality 10%, and speed to value 10%. Risk subtracts up to 15 points. Ratings are a triage mechanism only; a buyer interview, paid pilot, measured outcome, and repeatable delivery are required before scaling.

## Evidence signals informing the initial hypotheses

- The World Economic Forum's *Future of Jobs Report 2025* identifies AI and big data, networks/cybersecurity, and technological literacy among the fastest-growing skills through 2030, while noting a substantial reskilling challenge: https://www.weforum.org/publications/the-future-of-jobs-report-2025/in-full/3-skills-outlook/
- The World Bank's 2025 Uganda climate report announcement describes material climate risks and investment opportunities in climate-smart agriculture, renewable energy, resilient infrastructure, and digital connectivity: https://www.worldbank.org/en/news/press-release/2025/09/11/embracing-climate-smart-growth-is-a-net-win-for-uganda

These sources justify research directions, not product-market fit or guaranteed financial returns.

## Architecture target

1. **Signal layer** — sourced reports, tenders, regulations, user interviews, operational incidents, and measurable local needs; each item carries source, timestamp, freshness, confidence, and geography.
2. **Opportunity layer** — pain severity, affected population, urgency, buyer, ability to pay, existing alternatives, feasibility, risks, and strategic fit.
3. **Experiment layer** — falsifiable assumptions, cheapest test, owner, deadline, success threshold, result, and decision.
4. **Execution layer** — approved work is dispatched to the relevant existing product or Auto-Studio workflow; no execution without permission, idempotency, audit log, and rollback plan.
5. **Evidence and governance layer** — provenance, privacy, threat model, human approvals, test results, and versioned decisions.
6. **Economics and impact layer** — acquisition cost, contribution margin, break-even, retention, delivery cost, time saved, beneficiaries, and measurable environmental/social outcomes.
7. **Learning loop** — compare forecast to outcomes, calibrate scores, stop weak bets, and reinvest in proven solutions.

## Release gates

- **R0 — Local logic:** scoring and storage unit tests pass; Streamlit page starts without traceback.
- **R1 — Persistence and access:** authenticated managed database, workspace isolation, migrations, backups, and audit history.
- **R2 — Evidence ingestion:** approved data sources with citations, timestamps, deduplication, freshness checks, and failure handling.
- **R3 — Workflow execution:** Auto-Studio adapter, dry-run, idempotency, retry budget, least privilege, approval gates, and safe rollback.
- **R4 — Domain adapters:** NEMA-AGORA geospatial/environmental data, Bio-Research lifecycle, HACKFORGE learning outcomes, and career/workforce opportunities remain separate domain modules behind stable contracts.
- **R5 — Commercial validation:** at least five target-buyer interviews, one observed workflow baseline, one paid or budget-backed pilot, measured unit economics, and explicit stop/continue criteria.

## Known limitations and non-claims

- The initial release is a working local/Streamlit pipeline, not yet a connected multi-agent production system.
- SQLite persistence may not survive redeployments on ephemeral hosting and is not appropriate for multi-tenant production without access controls.
- Global signals are curated research links, not live monitoring feeds.
- No paid demand, live provider execution, environmental alert accuracy, regulatory approval, or production readiness is claimed by this release.
- Notion workspace consolidation and sharing verification require the Notion connection to become active.
