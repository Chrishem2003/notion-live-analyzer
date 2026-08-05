# Full Upgrade — Progress Tracker

## Phase 1 — Security Hardening (brief §0)
- [x] Create `modules/security_config.py` — centralized secret resolution, admin seeding, password hashing
- [x] Fix `modules/access_control.py` — remove hardcoded admin email, use env-based check
- [x] Fix `modules/admin_portal.py` — server-side role check, admin email from env (also fixed mojibake operators)
- [x] Add `tests/test_security_config.py` (14 tests passing)

## Phase 2 — Subscription / Trial / Agency Core (brief §6, §7 + addendum)
- [x] Create `modules/subscription_core.py` — pure-logic: has_access, require_access, require_admin, start_trial, webhook verification
- [x] Create `modules/workspace.py` — multi-workspace/agency mode
- [x] Refactor `modules/subscription.py` — delegate trial/access checks to subscription_core.has_access(); fixed mojibake operators (+1, +timedelta)
- [x] Add `tests/test_subscription_core.py` (31 tests passing combined)

## Phase 3 — Real Automations & AI (brief §4, §5)
- [ ] Create `modules/llm_client.py` — call_llm() wrapper, tag suggestion, NL query
- [ ] Create `modules/audit_rules.py` — condition types, rule evaluation, run_audit
- [ ] Create `modules/weekly_digest.py` — digest data, email HTML builder, run_all_digests
- [ ] Wire `modules/advanced_automations.py` to real handles where possible
- [ ] Add `tests/test_llm_client.py`
- [ ] Add `tests/test_audit_rules.py`

## Phase 4 — Governance & Presentations (brief §4, addendum)
- [ ] Create `modules/governance.py` — activity log, permission health check, CSV export
- [ ] Create `modules/presentations.py` — health report generation, streamlit render
- [ ] Add `tests/test_governance.py`
- [ ] Add `tests/test_presentations.py`

## Phase 5 — Integration & Landing (brief §8)
- [ ] Create `landing.py` — value prop + trial CTA page
- [ ] Wire `app.py`/`main.py` to show subscription status and gate premium modules

## Phase 6 — Final Verification
- [ ] Run `pytest` — all tests pass
- [ ] Run `python -m py_compile` on all new/modified modules
- [ ] Manual QA smoke test notes added

