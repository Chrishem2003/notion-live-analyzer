import streamlit as st
import pandas as pd
from datetime import datetime
from modules.database import log_backend_event

def render_academic_portfolio_studio_panel():
    """
    Renders the Academic, CV & Portfolio Writing Studio inside Streamlit.
    """
    st.subheader("?? Academic, CV & Portfolio Writing Studio")
    st.caption("AI-powered professional drafting engine: generate tailored CV summaries, academic research reports, project portfolios, and formal cover letters.")

    # Studio Mode Selection
    studio_mode = st.selectbox(
        "Select Writing & Generation Target:",
        [
            "Professional CV & Profile Summary",
            "Academic Research Abstract & Report",
            "Project Portfolio Description",
            "Formal Cover Letter & Job Application"
        ]
    )

    st.markdown("---")

    if studio_mode == "Professional CV & Profile Summary":
        st.markdown("### ?? Professional CV & Career Summary Builder")
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name / Handle", value="Kula Chris (Chrishem)")
            field_focus = st.text_input("Core Discipline / Focus", value="Biological Sciences & Data Analytics")
        with col2:
            experience_level = st.selectbox("Experience Tier", ["Undergraduate Researcher & Student", "Junior Data Analyst", "Independent Developer & Creator"])
            target_role = st.text_input("Target Opportunity / Role", value="Bioinformatics & Data Analytics Intern")

        if st.button("? Generate Professional CV Summary"):
            log_backend_event("INFO", "User generated professional CV summary via Academic Portfolio Studio.")
            st.success("CV Summary Generated Successfully!")
            
            generated_summary = f\"\"\"
**Professional Profile: {full_name}**
* **Discipline:** {field_focus} ({experience_level})
* **Target Position:** {target_role}

**Executive Summary:**
Motivated and detail-oriented undergraduate student in the Faculty of Science with rigorous training in biological sciences, data analytics, and computational pipelines. Proven track record in developing local web applications, managing sequence data pipelines, and executing precision research tasks. Adept at combining scientific inquiry with modern software automation and secure data management.
            \"\"\"
            st.markdown(generated_summary)
            st.text_area("Copy Generated CV Text:", value=generated_summary, height=150)

    elif studio_mode == "Academic Research Abstract & Report":
        st.markdown("### ?? Academic Research Abstract & Report Generator")
        col1, col2 = st.columns(2)
        with col1:
            project_title = st.text_input("Research Title", value="Waterborne Pathogen & Antimicrobial Resistance Surveillance")
            academic_field = st.text_input("Academic Field", value="Molecular Biology & Environmental Science")
        with col2:
            methodology = st.text_input("Methodology", value="Batch Data Log Filtering & Sequence Analysis")
            institution = st.text_input("Institution", value="Muni University Faculty of Science")

        if st.button("? Generate Academic Abstract"):
            log_backend_event("INFO", "User generated academic research abstract via Studio.")
            st.success("Research Abstract Generated Successfully!")

            abstract_text = f\"\"\"
**Research Title:** {project_title}
**Institution:** {institution} ({academic_field})

**Abstract:**
This study investigates regional environmental sample distributions using {methodology}. Conducted under academic evaluation guidelines at {institution}, the research maps biological specimen markers to track resistance patterns and evaluate public health indicators. Results demonstrate robust data capture reliability and highlight critical pathways for localized pathogen surveillance.
            \"\"\"
            st.markdown(abstract_text)
            st.text_area("Copy Generated Abstract:", value=abstract_text, height=150)

    elif studio_mode == "Project Portfolio Description":
        st.markdown("### ?? Project Portfolio Showcase Builder")
        proj_name = st.text_input("Project Name", value="Enterprise Intelligence & Sovereign Workspace")
        tech_stack = st.text_input("Technologies Used", value="Python, Streamlit, SQLite, PowerShell, Docker")
        proj_desc = st.text_area("Project Highlights", value="Built a 20-module sovereign enterprise workspace featuring secure local enclaves, automated telemetry dashboards, and bioinformatics data pipelines.")

        if st.button("? Generate Portfolio Description"):
            log_backend_event("INFO", "User generated project portfolio description.")
            st.success("Portfolio Description Generated Successfully!")

            portfolio_output = f\"\"\"
### **{proj_name}**
* **Tech Stack:** {tech_stack}
* **Overview:** {proj_desc}
* **Key Achievements:**
  * Engineered a fully autonomous multi-module workspace with real-time health diagnostics and secure database logging.
  * Integrated local containerization, automated background cognitive workers, and custom data processing tools.
  * Designed for high reliability, zero data drift, and seamless cross-platform execution.
            \"\"\"
            st.markdown(portfolio_output)
            st.text_area("Copy Portfolio Markup:", value=portfolio_output, height=150)

    else:
        st.markdown("### ?? Formal Cover Letter & Application Builder")
        company_name = st.text_input("Organization / Recipient", value="Data Analytics & Research Institute")
        position_applied = st.text_input("Position Applied For", value="Research & Data Analytics Fellow")
        
        if st.button("? Generate Formal Cover Letter"):
            log_backend_event("INFO", "User generated formal cover letter.")
            st.success("Cover Letter Generated Successfully!")

            cover_letter = f\"\"\"
Dear Hiring Committee at {company_name},

I am writing to express my strong interest in the {position_applied} position. As an undergraduate student in biological sciences and data analytics at Muni University, I have cultivated a strong foundation in automated data pipeline management, research reporting, and quantitative analysis.

My academic projects and technical implementations—ranging from molecular sequence tracking to secure local workspace architecture—demonstrate my capability to deliver rigorous, high-quality results. I am eager to bring my dedication, technical aptitude, and analytical skills to your esteemed organization.

Thank you for your time and consideration. I look forward to discussing how my background aligns with your institutional goals.

Sincerely,
Kula Chris (Chrishem)
            \"\"\"
            st.markdown(cover_letter)
            st.text_area("Copy Cover Letter:", value=cover_letter, height=180)
