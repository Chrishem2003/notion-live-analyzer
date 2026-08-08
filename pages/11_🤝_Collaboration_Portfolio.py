"""
🤝 Collaboration & Portfolio Hub — Consolidated Collaboration & Project Management Hub
Consolidates old pages: 45 (Project Collaboration), 46 (Application Pipeline),
60 (Agent Swarm Console), 63 (Academic Portfolio) — collaboration/list portion.
"""

import datetime

import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import (
    hero_card,
    section_header,
    render_export_buttons,
)


def render_projects():
    """Tab: Project collaboration."""
    section_header("🎯 Project Collaboration", "Manage research projects, teams, and shared workflows.")

    st.markdown("#### Active Projects")
    if "projects" not in st.session_state:
        st.session_state["projects"] = [
            {"Name": "Clinical Outcome Study", "Lead": "Chrishem", "Stage": "Analysis", "Progress": 65},
            {"Name": "Genomic Expression Analysis", "Lead": "Research Team", "Stage": "Data Collection", "Progress": 30},
            {"Name": "Agricultural Impact Assessment", "Lead": "Field Team", "Stage": "Reporting", "Progress": 80},
        ]

    projects_df = pd.DataFrame(st.session_state["projects"])
    st.dataframe(projects_df, use_container_width=True, hide_index=True)

    st.markdown("#### Create New Project")
    with st.form("new_project_form"):
        proj_name = st.text_input("Project Name")
        proj_lead = st.text_input("Project Lead")
        proj_stage = st.selectbox("Stage", ["Planning", "Data Collection", "Analysis", "Reporting", "Complete"])
        proj_progress = st.slider("Progress (%)", 0, 100, 10)
        submitted = st.form_submit_button("➕ Create Project")
        if submitted:
            st.session_state["projects"].append({"Name": proj_name, "Lead": proj_lead, "Stage": proj_stage, "Progress": proj_progress})
            st.success(f"Project '{proj_name}' created.")


def render_pipeline():
    """Tab: Application pipeline."""
    section_header("📋 Application & Workflow Pipeline", "Manage applications, submissions, and workflows.")

    st.markdown("#### Submission Pipeline")
    st.info("Track applications through the pipeline: Draft → Review → Submitted → Decision.")

    pipeline = pd.DataFrame({
        "Application": ["Grant Proposal", "Journal Submission", "Dataset Request", "Conference Abstract"],
        "Status": ["Draft", "In Review", "Submitted", "Accepted"],
        "Deadline": ["2024-06-01", "2024-05-15", "2024-04-30", "2024-07-01"],
    })
    st.dataframe(pipeline, use_container_width=True, hide_index=True)

    st.markdown("#### Pipeline Stages")
    stages = ["Draft", "Review", "Submitted", "Decision"]
    cols = st.columns(len(stages))
    for i, (col, stage) in enumerate(zip(cols, stages)):
        col.metric(f"Stage {i+1}", stage, delta="Active" if i < 2 else "Pending")


def render_agents():
    """Tab: Agent swarm task console."""
    section_header("🦾 Agent Swarm Task Console", "Deploy and manage autonomous agent tasks.")

    st.markdown("#### Task Orchestration")
    task = st.selectbox("Select Task", [
        "Data Sync Agent",
        "Anomaly Detection Agent",
        "Report Generation Agent",
        "Literature Scraping Agent",
        "Model Training Agent",
    ], key="c_task")

    priority = st.selectbox("Priority", ["Low", "Medium", "High", "Critical"], key="c_priority")

    st.markdown("#### Agent Fleet Status")
    fleet = pd.DataFrame({
        "Agent": ["Data Sync", "Anomaly", "Report", "Scraping", "Training"],
        "Status": ["Running", "Idle", "Running", "Idle", "Idle"],
        "Tasks Completed": [210, 98, 156, 45, 34],
        "Last Run": ["1m ago", "5m ago", "2h ago", "1h ago", "3h ago"],
    })
    st.dataframe(fleet, use_container_width=True, hide_index=True)

    if st.button("🚀 Deploy Selected Agent", type="primary", key="deploy_c_agent"):
        st.success(f"Agent task '{task}' deployed with {priority} priority.")


def render_team_workspace():
    """Tab: Team workspace."""
    section_header("👥 Team Workspace", "Shared workspace for team collaboration and communication.")

    st.markdown("#### Team Members")
    team = pd.DataFrame({
        "Name": ["Chrishem", "Researcher A", "Analyst B", "Field Officer C"],
        "Role": ["Lead", "Researcher", "Analyst", "Field Officer"],
        "Status": ["Online", "In Meeting", "Online", "Field"],
        "Current Task": ["Analysis", "Lit Review", "Modeling", "Data Collection"],
    })
    st.dataframe(team, use_container_width=True, hide_index=True)

    st.markdown("#### Team Activity Feed")
    st.markdown("""
    - **[Chrishem]** completed analysis for Clinical Outcome Study (10:32 AM)
    - **[Researcher A]** added 15 references to Literature Review (10:15 AM)
    - **[Analyst B]** trained a classification model (9:58 AM)
    - **[Field Officer C]** uploaded field data (9:41 AM)
    """)

    st.markdown("#### Shared Notes")
    note = st.text_area("Team Note", placeholder="Add a note for the team...", key="team_note")
    if st.button("📝 Save Note", type="primary", key="save_note"):
        st.success("Note saved to the team workspace.")


def render_portfolio():
    """Tab: Portfolio & achievements."""
    section_header("🎓 Portfolio & Achievements", "Showcase publications, grants, and tracked achievements.")

    st.markdown("#### Achievement Metrics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Publications", 12)
    c2.metric("Citations", 340)
    c3.metric("Grants Awarded", 5)
    c4.metric("Projects Completed", 18)

    st.markdown("#### Publication Portfolio")
    pub_df = pd.DataFrame({
        "Title": ["ML in Healthcare", "Statistical Methods Review", "Genomic Data Analysis"],
        "Journal": ["Nature Medicine", "Statistics & Methods", "Bioinformatics"],
        "Year": [2023, 2022, 2024],
        "Citations": [45, 120, 18],
    })
    st.dataframe(pub_df, use_container_width=True, hide_index=True)
    render_export_buttons(pub_df, base_name="publication_portfolio")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()  # paywall/trial gate, real DB check

    setup_page("Collaboration & Portfolio", "🤝", initial_sidebar_state="expanded")

    hero_card(
        "🤝 Collaboration & Portfolio Hub",
        "Consolidated collaboration hub: project management, workflow pipeline, agent swarm tasks, team workspace, and academic portfolio.",
        badge_text="COLLABORATION & PORTFOLIO HUB • CONSOLIDATED",
    )

    tabs = st.tabs([
        "🎯 Projects",
        "📋 Pipeline",
        "🦾 Agents",
        "👥 Team Workspace",
        "🎓 Portfolio",
    ])

    with tabs[0]:
        render_projects()
    with tabs[1]:
        render_pipeline()
    with tabs[2]:
        render_agents()
    with tabs[3]:
        render_team_workspace()
    with tabs[4]:
        render_portfolio()

    render_standard_footer("COLLABORATION & PORTFOLIO HUB")


if __name__ == "__main__":
    main()
