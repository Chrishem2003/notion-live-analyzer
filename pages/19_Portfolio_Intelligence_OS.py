from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pandas as pd
import streamlit as st

from portfolio_os.core import score_opportunity, unit_economics
from portfolio_os.storage import STATUSES, list_opportunities, save_opportunity, seed_examples_if_empty

st.set_page_config(page_title="Portfolio Intelligence OS", page_icon="🧭", layout="wide")

st.title("🧭 Portfolio Intelligence OS")
st.caption("A decision and execution cockpit: find painful problems, rank opportunities transparently, test demand, and track the economics. Starter entries are hypotheses—not validated markets or guaranteed revenue.")

DB_PATH = os.getenv("PORTFOLIO_OS_DB_PATH", "research_os.db")
try:
    seed_examples_if_empty(DB_PATH)
    records = list_opportunities(DB_PATH)
except Exception as exc:
    st.error("The opportunity store could not be opened. Check the configured database path and write permissions.")
    st.exception(exc)
    st.stop()

for record in records:
    record["assessment"] = score_opportunity(record)
    record["score"] = record["assessment"]["score"]
    record["recommendation"] = record["assessment"]["recommendation"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Tracked opportunities", len(records))
col2.metric("Ready for a pilot", sum(1 for r in records if r["recommendation"] == "Pilot with real users"))
col3.metric("In validation or pilot", sum(1 for r in records if r.get("status") in {"Validation", "Pilot"}))
col4.metric("Highest opportunity score", max((r["score"] for r in records), default=0))

st.info("Decision rule: score impact, urgency, feasibility, willingness to pay, strategic fit, evidence quality, and speed to value; subtract a visible risk penalty. A high score never replaces customer evidence or human approval.")

pipeline_tab, add_tab, economics_tab, operating_tab = st.tabs(["Opportunity pipeline", "Add an opportunity", "Unit economics", "Operating rules"])

with pipeline_tab:
    if records:
        view = pd.DataFrame([{
            "Opportunity": r.get("title", ""),
            "Sector": r.get("sector", ""),
            "Target customer": r.get("target_customer", ""),
            "Stage": r.get("status", "Hypothesis"),
            "Score / 100": r["score"],
            "Recommended next step": r["recommendation"],
            "Next experiment": r.get("next_experiment", ""),
            "Evidence source": r.get("source_url", ""),
        } for r in records])
        st.dataframe(view, use_container_width=True, hide_index=True, column_config={"Evidence source": st.column_config.LinkColumn("Evidence source")})
        chosen = st.selectbox("Inspect an opportunity", options=[r["opportunity_id"] for r in records], format_func=lambda x: next((r["title"] for r in records if r["opportunity_id"] == x), x))
        selected = next(r for r in records if r["opportunity_id"] == chosen)
        a, b = st.columns([2, 1])
        with a:
            st.subheader(selected["title"])
            st.write(selected.get("problem", ""))
            st.caption(f"Target customer: {selected.get('target_customer', 'Not specified')} · Stage: {selected.get('status', 'Hypothesis')}")
            st.write("**Next experiment:** " + (selected.get("next_experiment") or "Define a small test that can disprove the idea."))
            if selected.get("source_url"):
                st.markdown(f"**Evidence source:** [{selected.get('source_note', 'Open source')}]({selected['source_url']})")
        with b:
            st.metric("Priority score", f"{selected['score']}/100")
            st.write(selected["recommendation"])
            st.metric("Risk penalty", f"−{selected['assessment']['risk_penalty']} points")
            st.caption(selected["assessment"]["note"])
        with st.expander("Score breakdown"):
            st.json(selected["assessment"])
        with st.form("update_opportunity_form"):
            st.markdown("**Update stage and next experiment**")
            status = st.selectbox("Stage", STATUSES, index=STATUSES.index(selected.get("status", "Hypothesis")) if selected.get("status", "Hypothesis") in STATUSES else 0)
            next_experiment = st.text_area("Next experiment / evidence to collect", value=selected.get("next_experiment", ""), height=90)
            if st.form_submit_button("Save pipeline update", type="primary"):
                updated = {k: v for k, v in selected.items() if k not in {"assessment", "score", "recommendation", "created_at", "updated_at"}}
                updated["status"] = status
                updated["next_experiment"] = next_experiment.strip()
                save_opportunity(updated, DB_PATH)
                st.success("Opportunity updated.")
                st.rerun()
        st.download_button("Export opportunity pipeline (CSV)", data=view.to_csv(index=False).encode("utf-8"), file_name="portfolio-opportunity-pipeline.csv", mime="text/csv")
    else:
        st.warning("No opportunities have been added yet.")

with add_tab:
    with st.form("new_opportunity_form", clear_on_submit=True):
        title = st.text_input("Opportunity title *")
        sector = st.text_input("Sector / domain", placeholder="Climate, research, AI operations, education…")
        problem = st.text_area("Specific painful problem *", placeholder="Who experiences the problem, how often, and what does it cost them?")
        target_customer = st.text_input("Target customer / buyer *")
        source_url = st.text_input("Evidence URL", placeholder="https://…")
        source_note = st.text_input("What does this source actually establish?", placeholder="Separate sourced facts from your hypothesis")
        c1, c2, c3 = st.columns(3)
        impact = c1.slider("Potential impact", 0, 5, 3)
        urgency = c2.slider("Urgency", 0, 5, 3)
        feasibility = c3.slider("Delivery feasibility", 0, 5, 3)
        c4, c5, c6 = st.columns(3)
        willingness_to_pay = c4.slider("Willingness-to-pay evidence", 0, 5, 1)
        strategic_fit = c5.slider("Fit with existing capabilities", 0, 5, 3)
        evidence_quality = c6.slider("Evidence quality", 0, 5, 1)
        c7, c8 = st.columns(2)
        time_to_value = c7.slider("Speed to value (5 = fast)", 0, 5, 3)
        risk = c8.slider("Risk (5 = high)", 0, 5, 3)
        c9, c10, c11 = st.columns(3)
        monthly_price = c9.number_input("Expected monthly price per customer (USD)", min_value=0.0, value=0.0, step=5.0)
        variable_cost = c10.number_input("Monthly variable cost per customer (USD)", min_value=0.0, value=0.0, step=1.0)
        monthly_fixed_cost = c11.number_input("Estimated monthly fixed costs (USD)", min_value=0.0, value=0.0, step=10.0)
        status = st.selectbox("Current stage", STATUSES, index=0)
        next_experiment = st.text_area("Smallest useful validation experiment", placeholder="For example: interview five buyers, secure a paid pilot, or compare current workflow time with a prototype.")
        submitted = st.form_submit_button("Score and save opportunity", type="primary")
        if submitted:
            if not title.strip() or not problem.strip() or not target_customer.strip():
                st.error("Title, problem, and target customer are required.")
            elif source_url.strip() and not source_url.strip().startswith(("https://", "http://")):
                st.error("Evidence URL must start with http:// or https://.")
            else:
                payload = {
                    "opportunity_id": str(uuid.uuid4()), "title": title.strip(), "sector": sector.strip(),
                    "problem": problem.strip(), "target_customer": target_customer.strip(),
                    "source_url": source_url.strip(), "source_note": source_note.strip(),
                    "impact": impact, "urgency": urgency, "feasibility": feasibility,
                    "willingness_to_pay": willingness_to_pay, "strategic_fit": strategic_fit,
                    "evidence_quality": evidence_quality, "time_to_value": time_to_value, "risk": risk,
                    "monthly_price": monthly_price, "variable_cost": variable_cost,
                    "monthly_fixed_cost": monthly_fixed_cost, "status": status,
                    "next_experiment": next_experiment.strip(),
                }
                save_opportunity(payload, DB_PATH)
                st.success("Saved. The score is a prioritization aid; validate demand with real buyers.")
                st.rerun()

with economics_tab:
    st.subheader("Unit economics calculator")
    e1, e2, e3 = st.columns(3)
    price = e1.number_input("Monthly revenue per customer (USD)", min_value=0.0, value=25.0, step=5.0, key="econ_price")
    variable = e2.number_input("Monthly variable cost per customer (USD)", min_value=0.0, value=5.0, step=1.0, key="econ_variable")
    fixed = e3.number_input("Monthly fixed operating cost (USD)", min_value=0.0, value=100.0, step=10.0, key="econ_fixed")
    economics = unit_economics(price, variable, fixed)
    e4, e5, e6 = st.columns(3)
    e4.metric("Contribution / customer", f"${economics['contribution_per_customer']:,.2f}")
    e5.metric("Gross margin", "—" if economics["gross_margin_pct"] is None else f"{economics['gross_margin_pct']:.1f}%")
    e6.metric("Break-even customers", "Not viable yet" if economics["break_even_customers"] is None else economics["break_even_customers"])
    st.caption("This is a simple monthly contribution model. It excludes tax, payment fees, churn, acquisition costs, financing, and one-off setup costs; include them before making investment decisions.")

with operating_tab:
    st.subheader("Rules that keep the system honest")
    st.markdown("""
- **Evidence before certainty:** every opportunity records a source and states what that source does—and does not—prove.
- **Validate payment, not compliments:** seek a paid pilot, budget owner, or other observable commitment before scaling.
- **Small experiments first:** define the cheapest test that can falsify the main assumption.
- **No fake live data:** these starter signals are sourced research snapshots, not continuously refreshed feeds.
- **Human approval for consequential actions:** the cockpit ranks work; it does not automatically spend money, contact people, or change production systems.
- **Protect sensitive data:** never put API keys, credentials, personal secrets, or confidential customer information in opportunity notes.
- **Durability matters:** this first release uses SQLite. For multi-user production, migrate to authenticated managed storage with backups, audit logs, and per-workspace access controls.
""")
    st.markdown("**Research starting points**")
    st.markdown("- [World Economic Forum — Future of Jobs Report 2025](https://www.weforum.org/publications/the-future-of-jobs-report-2025/in-full/3-skills-outlook/)")
    st.markdown("- [World Bank — Climate-smart growth is a net win for Uganda](https://www.worldbank.org/en/news/press-release/2025/09/11/embracing-climate-smart-growth-is-a-net-win-for-uganda)")
    st.markdown("- [CHRISHEM AUTO-STUDIO repository](https://github.com/Chrishem2003/chrishem-autostudio)")
    st.markdown("- [Notion Live Analyzer repository](https://github.com/Chrishem2003/notion-live-analyzer)")
    st.markdown("- [HACKFORGE / Ethical Hacking Guide repository](https://github.com/Chrishem2003/Ethical-Hacking-Guide)")
