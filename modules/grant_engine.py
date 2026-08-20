
import streamlit as st

def generate_grant_sections(topic: str, agency: str, background_context: str, specific_goals: str) -> dict:
    """Structures research insights into agency-compliant grant formats."""
    if agency == "NIH (R01/R21)":
        return {
            "Specific Aims": f"### Specific Aims\n\n**Overall Objective:** Elucidate the mechanisms underlying **{topic}**.\n\n**Central Hypothesis:** Targeted modulation of active pathways will reveal novel functional interactions.\n\n* **Aim 1:** Characterize structural variance and sequence activity under baseline conditions.\n* **Aim 2:** Evaluate therapeutic response metrics via automated bio-analytics pipelines.\n* **Aim 3:** Validate long-term biological outcomes across target models.",
            "Significance": f"### Significance\n\n**Public Health Impact:** Addressing **{topic}** fills a critical knowledge gap in modern research.\n\n* **Unmet Need:** Existing pipelines lack real-time data synthesis capabilities.\n* **Scientific Gain:** This work establishes new baseline metrics for the broader scientific community.",
            "Innovation": f"### Innovation\n\nThis project integrates multi-omics data, WebGL structural rendering, and cryptographic FAIR audit trails into an automated platform."
        }
    elif agency == "NSF":
        return {
            "Intellectual Merit": f"### Intellectual Merit\n\nThis project advances fundamental knowledge in **{topic}** by deploying computational frameworks and open-source analytical pipelines.",
            "Broader Impacts": f"### Broader Impacts\n\n* **Curriculum Integration:** Workflows will be integrated into university computational biology modules.\n* **Open Data:** All code, datasets, and execution logs will be published under open-access FAIR standards."
        }
    else:
        return {
            "Excellence": f"### Section 1: Excellence\n\n**Objectives:** Establish state-of-the-art analytical workflows for **{topic}** across multidisciplinary domains.",
            "Impact": f"### Section 2: Impact\n\n**Outcomes:** Accelerates research productivity, enhances data reproducibility, and streamlines institutional cross-collaboration.",
            "Implementation": f"### Section 3: Implementation\n\n* **Work Package 1:** Multi-Omics Data Ingestion\n* **Work Package 2:** Structural & Environmental Validation\n* **Work Package 3:** Policy Translation & Open Access"
        }

def render_grant_engine_tab():
    st.subheader("ðŸ“„ Automated AI Grant Proposal Drafter")
    st.caption("Transform research summaries and data findings into agency-compliant funding proposals.")

    col1, col2 = st.columns([1, 1.8])

    with col1:
        st.markdown("### Proposal Parameters")
        project_title = st.text_input("Project / Proposal Title", value="Targeted Analysis of Biological Systems")
        funding_agency = st.selectbox("Funding Agency Standard", ["NIH (R01/R21)", "NSF", "Horizon Europe"], index=0)
        
        st.markdown("---")
        bg_context = st.text_area("Key Background & Findings", value="Recent research highlights critical structural variations driving functional pathways.", height=100)
        specific_goals = st.text_area("Primary Research Goals", value="Develop an end-to-end computational pipeline for rapid target validation.", height=90)
        
        generate_btn = st.button("ðŸš€ Draft Proposal Structure", type="primary", use_container_width=True)

    with col2:
        st.markdown("### Generated Draft Output")
        
        if generate_btn or "grant_draft" in st.session_state:
            if generate_btn:
                st.session_state["grant_draft"] = generate_grant_sections(project_title, funding_agency, bg_context, specific_goals)
            
            draft = st.session_state["grant_draft"]
            full_text = f"# Grant Proposal Draft: {project_title}\n\n**Agency Standard:** {funding_agency}\n\n---\n\n"
            
            for section_name, section_content in draft.items():
                with st.expander(section_name, expanded=True):
                    st.markdown(section_content)
                full_text = f"{section_content}\n\n---\n\n"

            st.download_button(
                label="📥 Download Proposal (.MD)",
                data=full_text,
                file_name=f"Grant_Proposal_{funding_agency.replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True
            )
        else:
            st.info("Configure parameters on the left and click **Draft Proposal Structure**.")
