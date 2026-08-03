
import streamlit as st
import pandas as pd

def render_personal_workspace_panel():
    st.subheader("ðŸ’» Universal Personal Workspace & Productivity Hub")
    st.caption("Manage research milestones, bioinformatics pipelines, system configurations, and daily workflow tasks.")
    st.markdown("<br>", unsafe_allow_html=True)

    # Scoped Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(border=True):
            st.caption("ACTIVE MILESTONES")
            st.subheader("ðŸŽ¯ 4 Tracked")
            st.caption("ðŸŸ¢ Up to Date")
    with c2:
        with st.container(border=True):
            st.caption("RESEARCH PROGRESS")
            st.subheader(" 94.2%")
            st.caption("ðŸ“ˆ 3.5% Auto")
    with c3:
        with st.container(border=True):
            st.caption("WORKSPACE STATUS")
            st.subheader("âš¡ Synced")
            st.caption("ðŸ”’ Local Enclave")
    with c4:
        with st.container(border=True):
            st.caption("FOCUS SCORE")
            st.subheader("ðŸ§  100%")
            st.caption("ðŸ”¥ Deep Work")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### ðŸŽ¯ Active Research & Task Milestones")

    tasks_df = pd.DataFrame([
        {"Task Item": "Waterborne Pathogen Surveillance Batch Analysis", "Category": "Bioinformatics Research", "Priority": "Critical", "Status": "IN PROGRESS"},
        {"Task Item": "ALX Data Analytics Portfolio Integration", "Category": "Professional Certification", "Priority": "High", "Status": "OPTIMIZED"},
        {"Task Item": "Desktop Environment Customization & UI Polish", "Category": "Workspace Customization", "Priority": "Medium", "Status": "ACTIVE"},
        {"Task Item": "Cryptographic Vault Key Rotation", "Category": "Security Engineering", "Priority": "Critical", "Status": "COMPLETED"}
    ])
    st.dataframe(tasks_df, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### ðŸ“ Quick Notes & Code Snippet Vault")
    st.text_area("Jot down research notes, terminal commands, or project ideas:", height=120, placeholder="Type notes here...")
