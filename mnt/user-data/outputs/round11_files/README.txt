ROUND 11 — apply order (matches every prior round's pattern):

Files in this package map 1:1 to real paths in your repo:
  app.py                              -> overwrite repo root app.py
  modules/billing_ui.py               -> overwrite repo modules/billing_ui.py
  modules/sovereign_analytics_engine.py -> NEW FILE, add to repo modules/

WHAT CHANGED AND WHY

1. app.py
   - Added one new sidebar menu item: "Sovereign Analytics Engine"
   - Routed it to modules.sovereign_analytics_engine.render_sovereign_analytics()
   - Same pattern as the existing Notion Vault / Billing routes — no restructuring.
   - Notion vault and billing routes are UNTOUCHED, exactly as you asked.

2. modules/billing_ui.py
   - Removed 3 dead input fields (card number, expiry, CVC) that were
     collected but never sent anywhere. The real charge already happens
     via the Stripe-hosted Checkout link created right below them
     (billing_stripe.create_checkout_session). Collecting card-shaped
     input that goes nowhere is both dead code and a bad security look.
   - Nothing else in billing_ui.py or billing_stripe.py touched.

3. modules/sovereign_analytics_engine.py (NEW)
   - Pulled from app_v3_sovereign_upscaled.py: kept only the genuinely
     real algorithms (SEIR epidemic model, Needleman-Wunsch alignment,
     PageRank, 2x2 Nash equilibrium solver, carbon budget calculator,
     proof-of-work, elbow-method clustering, Isolation Forest anomaly
     detection, Monte Carlo simulation).
   - Deleted everything else from app_v3: ~298 random-call sites feeding
     fake "live" telemetry/market/sentiment generators dressed up as
     real-time monitoring (generate_epidemiological_data,
     generate_financial_telemetry, _live_telemetry_feed, etc.)
   - Gated with the SAME modules.paywall.enforce_paywall() the Notion
     vault already uses — no new/parallel paywall system.
   - Every algorithm functionally verified against known-correct results
     before delivery (SEIR conserves population, PageRank sums to 1,
     Nash solver finds the correct Prisoner's-Dilemma equilibrium,
     proof-of-work finds a real valid nonce, Monte Carlo is
     seed-reproducible). Not just syntax-checked.

NOT DONE (flagged, not fixed, this round):
- modules/access_control.py defaults every session to
  user_tier = "Master Admin" and student_verified = True. Confirm
  before I change this — it's a security-relevant default, want your
  sign-off rather than silently changing access behavior.
- 27 pre-existing files (unrelated to this round's changes) still have
  the recurring missing-doubled-brace f-string bug from earlier rounds
  (brain_fm.py, mission_control.py, billing_stripe.py at root, etc.) —
  list in chat. Can sweep these next round if you want.

Full-repo py_compile sweep after these changes: app.py, billing_ui.py,
and sovereign_analytics_engine.py all compile clean; the 27 pre-existing
broken files are unchanged from before this round (not new breakage).
