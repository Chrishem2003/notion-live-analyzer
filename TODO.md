# Error Fix & Commit Plan

## Steps
- [x] Analyze all errors across 9 page files
- [x] Confirm plan with user

### Phase 1: Fix Syntax & Indentation Errors
- [ ] Fix `pages/16_🔗_Google_Sheets.py` — indentation of `for src` loop
- [ ] Fix `pages/21_🛰️_Global_Research_Radar.py` — indentation of `search_q` / `sev_filter`
- [ ] Fix `pages/25_🔍_Sensitivity_Analysis.py` — mojibake operators (`+`, `*`) and indentation
- [ ] Fix `pages/9_📋_Methodology_Advisor.py` — indentation of `options=...` and `num_groups`
- [ ] Fix `pages/31_💬_NL_Query.py` — indentation of `np.random.seed`, fix `fig = px.scatter(...)` line
- [ ] Fix `pages/32_🛡️_Audit_Compliance.py` — indentation of `if st.button`, fix `prev_hash[:12]  "..."` operator
- [ ] Fix `pages/34_🌐_Global_Localization.py` — indentation of `region_opts`
- [ ] Fix `pages/37_📊_Chart_Data_Extractor.py` — indentation of `np.random.seed`
- [ ] Fix `pages/42_🧮_Hypothesis_Simulator.py` — indentation of `stochastic_shocks`

### Phase 2: Verify + Check Other Files
- [ ] Re-run `py_compile` on all 9 files
- [ ] Check `app.py`, `main.py`, key modules for errors

### Phase 3: Commit & Push
- [ ] Stage all fixed files
- [ ] Create `.gitignore` entries for `.pyc`, `.db` if needed
- [ ] Commit with descriptive message
- [ ] Push to origin/main

