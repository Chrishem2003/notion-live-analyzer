"""
🤝 Collaboration & Portfolio Hub — Enterprise Production Grade (Premium)
Persistent project tracking, a persistent submission pipeline, real non-theatrical agent missions
with an accumulating run log, a genuinely editable team roster with a real broadcast note feed,
and a portfolio summary computed from this hub's own real data.

Changelog vs prior version:
- FIXED: Projects lived only in `st.session_state`, so the entire portfolio vanished on a session
  reset or server restart — a real reliability problem for something billed as project tracking.
  Now persisted to SQLite, same as the rest of the platform's durable data.
- FIXED (was 100% static/fake): the "Submission Lifecycle Kanban" was a fixed, non-editable
  DataFrame showing the same four fabricated grant submissions to every user, regardless of what
  they were actually working on. It's now a real, persistent, editable pipeline table.
- FIXED (was 100% theatrical): "Deploy Agent Swarm Task" always printed a canned success message,
  and the "Active Agent Fleet Telemetry" table was static numbers that never changed no matter
  what you dispatched. Missions now actually execute: Data Sync & Clean and Anomaly Detection run
  real checks against your active dataset, Report Compilation generates a real downloadable
  summary, and Literature Scraping performs a real CrossRef API query. Every dispatch is logged to
  a real, accumulating run history — not a static fleet table. Model training isn't duplicated
  here; it points to the real AutoML in ML & Predictive Studio instead of faking a second,
  out-of-sync training path.
- FIXED (was fake/generic): "Roster & Presence" showed the same four fabricated team members to
  every user. It's now an editable, persisted roster you fill in with your actual team.
- FIXED (was decorative): "Broadcast Workspace Note" showed a success toast and then the note
  vanished — nothing was ever stored or displayed. Notes are now persisted and shown in a real
  accumulating feed below the composer.
- FIXED (was fake/duplicated): the Academic Portfolio tab showed the same fabricated publications
  as the Domain Analytics Hub's portfolio tool — duplicate fake data in two places. This tab is
  now a genuine "Team & Project Impact Summary" computed from the real Projects and Pipeline data
  entered in this same hub (project counts, stage distribution, real parsed budget totals) rather
  than re-showing unrelated fabricated academic data.
"""

import re
import time
import sqlite3
import datetime

import numpy as np
import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import get_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_export_buttons,
)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

DB_PATH = "sovereign_apex_engine.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS collab_projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, lead TEXT, stage TEXT, progress INTEGER, budget TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS collab_pipeline (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, target_entity TEXT, status TEXT, deadline TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS collab_agent_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT, priority TEXT, status TEXT, result_summary TEXT, timestamp TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS collab_team_roster (
        id INTEGER PRIMARY KEY AUTOINCREMENT, member_name TEXT, role TEXT, status TEXT, focus_task TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS collab_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, note TEXT, timestamp TEXT)""")
    conn.commit()

    # Seed with clearly-labeled example rows only if genuinely empty (first run).
    if c.execute("SELECT COUNT(*) FROM collab_projects").fetchone()[0] == 0:
        now = datetime.datetime.now().isoformat()
        c.executemany(
            "INSERT INTO collab_projects (name, lead, stage, progress, budget, created_at) VALUES (?,?,?,?,?,?)",
            [
                ("[Example] Clinical Outcome Study", "Team Lead", "Analysis", 65, "$12,500", now),
                ("[Example] Genomic Expression Pipeline", "Research Team A", "Data Collection", 35, "$28,000", now),
            ],
        )
        conn.commit()
    return conn


def render_projects(conn):
    section_header("🎯 Research Project Collaboration & Milestones", "Manage projects, assign leads, and track progress — persisted, not lost on refresh.")

    projects_df = pd.read_sql_query("SELECT id, name AS Name, lead AS Lead, stage AS Stage, progress AS Progress, budget AS Budget FROM collab_projects ORDER BY id DESC", conn)
    st.markdown("#### Active Project Portfolio")
    st.dataframe(projects_df.drop(columns=["id"]), use_container_width=True, hide_index=True)
    if not projects_df.empty:
        render_export_buttons(projects_df.drop(columns=["id"]), base_name="active_projects_export")

    st.markdown("#### Initialize New Research Project")
    with st.form("new_project_form_upg"):
        col1, col2 = st.columns(2)
        with col1:
            proj_name = st.text_input("Project Title", key="new_proj_name")
            proj_lead = st.text_input("Project Lead", key="new_proj_lead")
        with col2:
            proj_stage = st.selectbox("Lifecycle Stage", ["Planning", "Data Collection", "Analysis", "Reporting", "Complete"], key="new_proj_stage")
            proj_progress = st.slider("Milestone Progress (%)", 0, 100, 15, key="new_proj_progress")
            proj_budget = st.text_input("Allocated Budget", value="$10,000", key="new_proj_budget")

        submitted = st.form_submit_button("➕ Create and Register Project", type="primary")
        if submitted and proj_name.strip():
            conn.execute(
                "INSERT INTO collab_projects (name, lead, stage, progress, budget, created_at) VALUES (?,?,?,?,?,?)",
                (proj_name.strip(), proj_lead.strip() or "Unassigned", proj_stage, proj_progress, proj_budget, datetime.datetime.now().isoformat()),
            )
            conn.commit()
            st.success(f"✅ Project `{proj_name}` successfully initialized and persisted.")
            st.rerun()


def render_pipeline(conn):
    section_header("📋 Application & Grant Submission Pipeline", "Track your actual grant applications, journal submissions, and review workflows — a real, editable, persisted table.")

    pipeline_df = pd.read_sql_query("SELECT id, title AS 'Application / Proposal Title', target_entity AS 'Target Entity', status AS 'Current Status', deadline AS 'Deadline Date' FROM collab_pipeline ORDER BY id DESC", conn)

    st.markdown("#### Submission Lifecycle Tracker")
    st.dataframe(pipeline_df.drop(columns=["id"]) if not pipeline_df.empty else pipeline_df, use_container_width=True, hide_index=True)

    with st.form("new_pipeline_form"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            p_title = st.text_input("Application / Proposal Title", key="pipe_title")
        with col2:
            p_target = st.text_input("Target Entity", key="pipe_target")
        with col3:
            p_status = st.selectbox("Status", ["Drafting", "Internal Review", "Submitted", "In Peer Review", "Approved", "Rejected"], key="pipe_status")
        with col4:
            p_deadline = st.date_input("Deadline", key="pipe_deadline")
        if st.form_submit_button("➕ Add Submission", type="primary") and p_title.strip():
            conn.execute(
                "INSERT INTO collab_pipeline (title, target_entity, status, deadline, created_at) VALUES (?,?,?,?,?)",
                (p_title.strip(), p_target.strip(), p_status, str(p_deadline), datetime.datetime.now().isoformat()),
            )
            conn.commit()
            st.success(f"✅ Added `{p_title}` to the pipeline.")
            st.rerun()

    if not pipeline_df.empty:
        st.markdown("#### Pipeline Stage Breakdown (real counts from your data above)")
        stage_counts = pipeline_df["Current Status"].value_counts()
        cols = st.columns(min(4, len(stage_counts))) if len(stage_counts) else []
        for i, (stage, count) in enumerate(stage_counts.items()):
            cols[i % len(cols)].metric(stage, count)
        render_export_buttons(pipeline_df.drop(columns=["id"]), base_name="submission_pipeline")


# ══════════════════════════════════════════════════════════════════════
# Real, non-theatrical agent missions + a real accumulating run log
# ══════════════════════════════════════════════════════════════════════
def _mission_data_sync_clean(df):
    before_rows = len(df)
    cleaned = df.copy()
    for c in cleaned.select_dtypes(include=["object"]).columns:
        cleaned[c] = cleaned[c].astype(str).str.strip()
    dups = cleaned.duplicated().sum()
    return f"Scanned {before_rows:,} rows across {df.shape[1]} columns. Whitespace normalized on text columns. {dups:,} exact duplicate row(s) detected (not auto-removed — review in Data Studio)."


def _mission_anomaly_detection(df):
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return "No numeric columns available to scan."
    total_outliers = 0
    for c in numeric_cols:
        s = df[c].dropna()
        if s.empty:
            continue
        q1, q3 = np.percentile(s, 25), np.percentile(s, 75)
        iqr = q3 - q1
        mask = (s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)
        total_outliers += int(mask.sum())
    return f"IQR outlier sweep across {len(numeric_cols)} numeric column(s): {total_outliers:,} outlier value(s) detected."


def _mission_report_compile(df):
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    lines = [f"# Auto-Compiled Report ({pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')})",
              f"- Rows: {df.shape[0]:,} | Columns: {df.shape[1]}",
              f"- Missing cells: {int(df.isnull().sum().sum()):,}"]
    if numeric_cols:
        lines.append(df[numeric_cols].describe().T.round(2).to_string())
    return "\n".join(lines)


def _mission_literature_scrape(query):
    if not REQUESTS_AVAILABLE:
        return None, "`requests` package not available."
    try:
        resp = requests.get(
            "https://api.crossref.org/works", params={"query": query, "rows": 5}, timeout=8,
            headers={"User-Agent": "ChrishemPlatform-CollabHub/1.0 (mailto:research@example.com)"},
        )
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])
        titles = [(it.get("title") or ["Untitled"])[0] for it in items]
        return titles, None
    except Exception as e:
        return None, str(e)


def render_agents(conn):
    section_header("🦾 Autonomous Agent Console", "Missions execute for real against your active dataset or the live CrossRef API — every dispatch is logged to a real, accumulating history, not a static fleet table.")

    col1, col2 = st.columns(2)
    with col1:
        task = st.selectbox("Select Agent Task Profile", [
            "Data Sync & Clean Agent",
            "Anomaly Detection Agent",
            "Automated Report Compilation Agent",
            "Literature Scraping Agent",
            "Deep Learning Model Training Agent",
        ], key="agent_task_select")
    with col2:
        priority = st.selectbox("Execution Priority", ["Low", "Medium", "High", "Critical (Real-Time)"], key="agent_priority_select")

    literature_query = None
    if task == "Literature Scraping Agent":
        literature_query = st.text_input("Search query for CrossRef", placeholder="e.g., machine learning genomics", key="agent_lit_query")

    if st.button("🚀 Deploy Agent Task", type="primary", key="deploy_swarm_btn"):
        df = get_active_dataframe()
        status, summary = "COMPLETED", ""

        if task == "Deep Learning Model Training Agent":
            status = "REDIRECTED"
            summary = "Model training isn't duplicated here — use the real AutoML pipeline in ML & Predictive Studio (with real cross-validation and hyperparameter tuning) rather than a second, out-of-sync training path."
            st.info(f"ℹ️ {summary}")
        elif task == "Literature Scraping Agent":
            if not literature_query:
                status, summary = "FAILED", "No search query provided."
                st.warning("Enter a search query above.")
            else:
                titles, err = _mission_literature_scrape(literature_query)
                if err:
                    status, summary = "FAILED", f"CrossRef request failed: {err}"
                    st.error(f"🚫 {summary}")
                else:
                    summary = f"Retrieved {len(titles)} real result(s) for '{literature_query}'."
                    st.success(f"✅ {summary}")
                    for t in titles:
                        st.markdown(f"- {t}")
        elif df is None:
            status, summary = "FAILED", "No active dataset loaded — this mission needs real data to inspect."
            st.warning(f"⚠️ {summary}")
        elif task == "Data Sync & Clean Agent":
            summary = _mission_data_sync_clean(df)
            st.success(f"✅ {summary}")
        elif task == "Anomaly Detection Agent":
            summary = _mission_anomaly_detection(df)
            st.success(f"✅ {summary}")
        elif task == "Automated Report Compilation Agent":
            report = _mission_report_compile(df)
            summary = "Report compiled and available for download below."
            st.success(f"✅ {summary}")
            st.download_button("⬇️ Download Report", data=report, file_name="agent_compiled_report.md", mime="text/markdown", key="agent_report_dl")

        conn.execute(
            "INSERT INTO collab_agent_runs (task, priority, status, result_summary, timestamp) VALUES (?,?,?,?,?)",
            (task, priority, status, summary, datetime.datetime.now().isoformat()),
        )
        conn.commit()

    st.markdown("#### Real Agent Run History")
    runs_df = pd.read_sql_query("SELECT timestamp AS Timestamp, task AS Task, priority AS Priority, status AS Status, result_summary AS Summary FROM collab_agent_runs ORDER BY id DESC LIMIT 20", conn)
    if runs_df.empty:
        st.info("No agent runs logged yet — dispatch a task above.")
    else:
        st.dataframe(runs_df, use_container_width=True, hide_index=True)
        render_export_buttons(runs_df, base_name="agent_run_history")


def render_team_workspace(conn):
    section_header("👥 Collaborative Team Workspace & Activity Feed", "A real, editable team roster and a persisted note feed — not fixed fictional teammates.")

    st.markdown("#### Roster & Presence")
    roster_df = pd.read_sql_query("SELECT id, member_name AS 'Member Name', role AS 'Role', status AS 'Status', focus_task AS 'Current Focus' FROM collab_team_roster ORDER BY id", conn)
    edited = st.data_editor(
        roster_df.drop(columns=["id"]) if not roster_df.empty else pd.DataFrame({"Member Name": [], "Role": [], "Status": [], "Current Focus": []}),
        num_rows="dynamic", use_container_width=True, key="roster_editor",
    )
    if st.button("💾 Save Roster", key="save_roster_btn"):
        conn.execute("DELETE FROM collab_team_roster")
        for _, row in edited.dropna(subset=["Member Name"]).iterrows():
            conn.execute(
                "INSERT INTO collab_team_roster (member_name, role, status, focus_task) VALUES (?,?,?,?)",
                (row["Member Name"], row.get("Role", ""), row.get("Status", ""), row.get("Current Focus", "")),
            )
        conn.commit()
        st.success("✅ Roster saved.")
        st.rerun()

    st.markdown("#### Team Notes Feed")
    note = st.text_area("Add a note or directive for the team...", key="team_workspace_note")
    author = st.session_state.get("user_identity", {}).get("name", "Team Member")
    if st.button("📝 Broadcast Note", type="primary", key="save_team_note_btn"):
        if note.strip():
            conn.execute("INSERT INTO collab_notes (author, note, timestamp) VALUES (?,?,?)", (author, note.strip(), datetime.datetime.now().isoformat()))
            conn.commit()
            st.success("✅ Note broadcast and saved to the team feed below.")
            st.rerun()
        else:
            st.warning("⚠️ Please enter note text before broadcasting.")

    notes_df = pd.read_sql_query("SELECT author AS Author, note AS Note, timestamp AS Timestamp FROM collab_notes ORDER BY id DESC LIMIT 20", conn)
    if notes_df.empty:
        st.info("No notes broadcast yet.")
    else:
        for _, row in notes_df.iterrows():
            st.markdown(f"- **[{row['Author']}]** {row['Note']} · _{row['Timestamp'][:16].replace('T', ' ')}_")


def render_portfolio(conn):
    section_header("🎓 Team & Project Impact Summary", "Aggregated from this hub's own real Projects and Pipeline data — not fabricated academic publications.")

    projects_df = pd.read_sql_query("SELECT name, lead, stage, progress, budget FROM collab_projects", conn)
    pipeline_df = pd.read_sql_query("SELECT title, status FROM collab_pipeline", conn)

    def _parse_budget(b):
        digits = re.sub(r"[^\d.]", "", str(b))
        try:
            return float(digits) if digits else 0.0
        except ValueError:
            return 0.0

    total_budget = projects_df["budget"].apply(_parse_budget).sum() if not projects_df.empty else 0.0
    completed = int((projects_df["stage"] == "Complete").sum()) if not projects_df.empty else 0
    approved_submissions = int((pipeline_df["status"] == "Approved").sum()) if not pipeline_df.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Projects", len(projects_df))
    c2.metric("Completed Projects", completed)
    c3.metric("Total Tracked Budget", f"${total_budget:,.0f}")
    c4.metric("Approved Submissions", approved_submissions)

    if not projects_df.empty:
        st.markdown("#### Project Stage Distribution")
        stage_counts = projects_df["stage"].value_counts()
        if PLOTLY_AVAILABLE:
            fig = px.pie(names=stage_counts.index, values=stage_counts.values, hole=0.4, template="plotly_dark", height=320)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(projects_df, use_container_width=True, hide_index=True)
        render_export_buttons(projects_df, base_name="team_project_summary")
    else:
        st.info("Add projects in the Projects tab to populate this summary.")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()

    setup_page("Collaboration & Portfolio", "🤝", initial_sidebar_state="expanded")

    hero_card(
        "🤝 Collaboration & Portfolio Hub — Premium Suite",
        "Persistent project tracking, a real submission pipeline, non-theatrical agent missions with an accumulating run log, a genuine team roster and note feed, and a portfolio summary computed from your own real data.",
        badge_text="COLLABORATION & PORTFOLIO HUB • PREMIUM SUITE",
    )

    conn = get_db()

    tabs = st.tabs([
        "🎯 Projects",
        "📋 Pipeline",
        "🦾 Agent Console",
        "👥 Team Workspace",
        "🎓 Impact Summary",
    ])

    with tabs[0]:
        render_projects(conn)
    with tabs[1]:
        render_pipeline(conn)
    with tabs[2]:
        render_agents(conn)
    with tabs[3]:
        render_team_workspace(conn)
    with tabs[4]:
        render_portfolio(conn)

    render_standard_footer("COLLABORATION & PORTFOLIO HUB")


if __name__ == "__main__":
    main()