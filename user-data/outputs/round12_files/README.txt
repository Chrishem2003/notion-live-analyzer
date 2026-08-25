ROUND 12 — two deliverables in this package.

===========================================================================
1. app_v4.py — THE SINGLE-FILE APPLICATION (ready to copy-paste)
===========================================================================
This is the real app.py plus its full recursive dependency closure —
database, paywall, audio_engine, subscription, billing_stripe, billing_ui,
brain_fm, notion_gating, sovereign_analytics_engine, user_preferences —
merged into ONE file. 2,763 lines.

IMPORTANT — why this is 2,763 lines, not 5,000+:
I traced app.py's actual import graph before merging anything. It only
really depends on those 10 modules above. The rest of the 541-file repo
(portal.py, mission_control.py, dozens of other feature modules) is not
imported by app.py at all — it's a separate, unused set of features from
another iteration of this project. Padding app_v4.py with unrelated code
just to hit a line count would make it long, not good, so I didn't.
I'd rather hand you an honest, fully-verified 2,763 lines than an
unverified 5,000.

VERIFICATION — this was not just "made to compile":
- Every one of the 10 modules' real algorithms/flows were preserved exactly
  (same Stripe Checkout logic, same Notion vault, same real SEIR/Needleman-
  Wunsch/PageRank/Nash/Monte Carlo engines from round 11).
- I actually ran app_v4.py as a live Streamlit server (not just
  py_compile) and confirmed: /_stcore/health returns "ok", the root page
  returns HTTP 200 with real rendered content, and the server log has
  zero tracebacks.
- The few places the original app.py called things as
  subscription.get_status(...) / billing_stripe.verify_checkout_session(...)
  are preserved via a small namespace shim at the point in the file where
  those modules' functions become available — no call sites were rewritten.

HOW TO USE: replace your repo's app.py with this file, keep the rest of
your modules/ folder as-is (app_v4.py no longer imports from it, but
nothing is deleted from your repo), and your Procfile's
`streamlit run app.py` still works if you rename this file to app.py.

===========================================================================
2. Bug fixes to the real modular repo (all other files in this zip)
===========================================================================
Since I was fixing bugs anyway, here is the same set of fixes applied
directly to the real 541-file repo structure, in case you'd rather keep
running the modular version instead of app_v4.py. Apply order: each file
overwrites the same path in your repo.

REAL BUGS FOUND AND FIXED THIS ROUND (not just syntax errors):
- database.py / modules/database.py: was writing audit logs and user
  sessions to a completely different SQLite file ("chrishem_engine.db")
  than the rest of the app ("sovereign_apex_engine.db") — every
  log_backend_event() and save_user_session() call was silently writing
  to a file nothing else ever read from. Fixed to use the same DB file.
- billing_stripe.py (root copy only — modules/billing_stripe.py was
  already correct): Stripe's {CHECKOUT_SESSION_ID} placeholder in the
  success_url wasn't fully escaped, which would have broken checkout
  verification after a real payment.
- notion_sync.py / modules/notion_sync.py: every branch of
  _build_property_payload() (rich_text, title, select, status, checkbox,
  date, email, phone, url, multi_select) and add_page_comment() was
  missing closing braces on its dict literals. Rewrote each against the
  real Notion API property-object schema and verified all 11 property
  types produce correct payloads against known-correct expected output.
- .streamlit/config.toml and config.toml: both had a UTF-8 BOM byte at
  the very start of the file, which silently broke Streamlit's TOML
  parser — meaning headless mode, CORS, and XSRF settings were never
  actually being applied. Removed the BOM from both.
- modules/access_control.py: defaulted every new session to
  user_tier="Master Admin" and student_verified=True regardless of who
  was logged in, and let anyone overwrite a free-text email field with
  the admin's address to see "Verified (Admin)" displayed. Now derives
  identity/tier from the real logged-in session (st.session_state.
  user_identity, set by the real PBKDF2/OAuth flow) instead. Note: the
  real app.py is_admin() check was never affected by this bug — it reads
  a separate, correct session key — so this was a misleading-display bug
  local to this one panel, not a full privilege escalation.
- modules/billing_ui.py: removed 3 dead card-number/expiry/CVC input
  fields that were collected but never sent anywhere (the real charge
  happens via the Stripe-hosted Checkout link created separately).

SYNTAX-ONLY FIXES (the recurring "doubled opening brace, single closing
brace" corruption in JS/CSS pasted into Python f-strings, from earlier
rounds), all verified to compile AND — for the widget files — verified
that the actual rendered JavaScript is brace/paren/bracket-balanced, not
just that Python's parser accepts it:
  brain_fm.py, chat_widget_snippet.py, deck_builder.py,
  docs_widget_snippet.py, file_converter.py, git_integration.py,
  literature_engine.py, meet_widget_snippet.py, meta_analysis.py,
  report_generator.py, structure_viewer.py, chart_builder.py,
  mission_control.py, test_notion_client.py (+ tests/ copy)

RESULT: a full repo-wide py_compile sweep now shows 0 broken files,
down from 27 at the start of this round (and down from the same 27
flagged-but-unfixed at the end of round 11).

NOT DONE (still flagged, no new info this round):
- The GitHub Personal Access Token question is still open. Given this
  round again required tracking two copies of ~15 files (root + modules/)
  by hand, direct commit access would remove an entire category of
  "did I remember to fix both copies" risk going forward.
