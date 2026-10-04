# Phase 16 — Benchmark Governance & Model Admission

## Purpose

Phase 16 is the formal evidence gate between controlled model comparison and controlled shadow eligibility.

It asks whether this exact model/adapter has a sufficiently reproducible, human-reviewed and safety-constrained evidence package to enter isolated shadow evaluation.

It does not establish environmental truth, legal authority, NEMA approval, production readiness or autonomous decision authority.

## Admission chain

Human annotation → annotation readiness → frozen dataset → controlled comparison → safety/regression evidence → model admission → controlled shadow.

## Required evidence

A candidate must be bound to:

- exact provider;
- exact model version;
- exact adapter name;
- dataset version;
- frozen dataset manifest SHA-256;
- comparison run ID;
- authenticated approver;
- documented intended use;
- data handling;
- retention policy;
- processing location;
- failure behaviour.

## Default gates

- at least 25 frozen benchmark cases;
- annotation process READY_FOR_REVIEW;
- minimum category Cohen's kappa >= 0.80;
- no unresolved annotation disagreements;
- comparison run matches the exact dataset version and manifest hash;
- exact provider/model/adapter identity match;
- comparison READY_FOR_REVIEW;
- zero adapter failures;
- category accuracy >= 0.80;
- duplicate F1 >= 0.80;
- explicit human-review contract for comparison outputs.

Any failed gate produces NOT_ADMITTED.

## Decision

The only positive decision is ADMITTED_FOR_CONTROLLED_SHADOW.

This means the candidate may be evaluated in isolated advisory shadow mode under human review.

It does not authorize NEMA or government integration, official reporting, environmental-truth claims, regulatory decisions, enforcement, emergency dispatch, autonomous workflow transitions or production deployment.

## Evidence-binding rule

Admission rejects mixed evidence. Dataset version, manifest hash, comparison run ID, provider, model version and adapter name must all match the selected evidence.

## Persistence

Admission decisions are stored in model_admissions with the policy version, actor, approver, model identity, dataset evidence, comparison run, decision and rationale.

## Roles

intelligence:admit_model is granted only to coordinator and admin roles. Submitters and reviewers cannot admit a model.

## Next phase

After Phase 16 is verified, a real external provider may be introduced as a candidate only if it implements the provider-neutral adapter contract and is evaluated against the frozen benchmark. The model remains outside live workflow until the admission gate passes.
