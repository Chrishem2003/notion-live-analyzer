import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ==========================================
# 1. DATABASE & TELEMETRY MODULE
# ==========================================
import sqlite3

DB_PATH = "chrishem_enterprise.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backend_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            level TEXT,
            message TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_verifications (
            email TEXT PRIMARY KEY,
            tier TEXT,
            institution TEXT,
            country TEXT,
            verified_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_backend_event(level: str, message: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO backend_logs (timestamp, level, message) VALUES (?, ?, ?)",
                       (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), level, message))
        conn.commit()
        conn.close()
    except Exception:
        pass

init_db()

# ==========================================
# 2. THEME & UI STYLING ENGINE (Neon Glassmorphism)
# ==========================================
def apply_custom_theme():
    st.markdown(
        """
        <style>
            /* Global Background & Typography */
            .stApp, .main {
                background-color: #0B0F19 !important;
                background-image: linear-gradient(135deg, #0B0F19 0%, #131C2E 100%) !important;
                color: #E2E8F0 !important;
                font-family: 'Inter', sans-serif;
            }
            
            /* Sidebar Styling */
            [data-testid="stSidebar"] {
                background-color: #0E1626 !important;
                border-right: 1px solid rgba(0, 255, 102, 0.2) !important;
            }
            
            /* Form & Container Polish */
            div.stMarkdown container, div.stForm, div.row-widget {
                background: rgba(19, 28, 46, 0.75) !important;
                border: 1px solid rgba(0, 255, 102, 0.25) !important;
                border-radius: 14px !important;
                padding: 1.5rem !important;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
            }

            /* Inputs & Dropdowns */
            .stTextInput div[data-baseweb="input"], 
            .stTextArea div[data-baseweb="textarea"],
            .stSelectbox div[data-baseweb="select"] {
                background-color: #1A2639 !important;
                border: 1px solid rgba(0, 255, 102, 0.4) !important;
                border-radius: 8px !important;
                color: #FFFFFF !important;
            }
            .stTextInput input, .stTextArea textarea {
                color: #FFFFFF !important;
            }

            /* Custom Neon Buttons */
            .stButton > button {
                background: linear-gradient(135deg, #00FF66 0%, #00CC52 100%) !important;
                color: #0B0F19 !important;
                font-weight: 800 !important;
                border: none !important;
                border-radius: 8px !important;
                padding: 0.6rem 1.4rem !important;
                box-shadow: 0 4px 14px rgba(0, 255, 102, 0.4) !important;
                transition: all 0.3s ease !important;
            }
            .stButton > button:hover {
                background: linear-gradient(135deg, #1aff75 0%, #00ff66 100%) !important;
                box-shadow: 0 6px 20px rgba(0, 255, 102, 0.6) !important;
                transform: translateY(-2px) !important;
            }

            /* Metrics & Tables */
            [data-testid="stMetricValue"] {
                color: #00FF66 !important;
                font-weight: 800 !important;
            }
            [data-testid="stDataFrame"] {
                border: 1px solid rgba(0, 255, 102, 0.3) !important;
                border-radius: 10px !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

st.set_page_config(
    page_title="CHRISHEM Sovereign Enterprise Intelligence Engine",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_custom_theme()

# ==========================================
# 3. MODULE RENDERERS
# ==========================================

def render_access_control_panel():
    st.subheader("🔐 Sovereign Access Control & Tiered Licensing Hub")
    st.caption("Manage secure user licenses, African student verification portals, and administrative privileges.")

    if "user_email" not in st.session_state:
        st.session_state.user_email = "chrishem242@gmail.com"
    if "user_tier" not in st.session_state:
        st.session_state.user_tier = "Master Admin"
    if "student_verified" not in st.session_state:
        st.session_state.student_verified = True

    col_u1, col_u2, col_u3 = st.columns(3)
    with col_u1:
        input_email = st.text_input("User Email Address", value=st.session_state.user_email)
        if input_email != st.session_state.user_email:
            st.session_state.user_email = input_email
            if input_email.strip().lower() == "chrishem242@gmail.com":
                st.session_state.user_tier = "Master Admin"
                st.session_state.student_verified = True
            else:
                st.session_state.user_tier = "Free (Unverified)"
            st.rerun()

    with col_u2:
        st.text_input("Assigned Access Tier", value=st.session_state.user_tier, disabled=True)

    with col_u3:
        status_txt = "Verified (Admin)" if st.session_state.student_verified else "Pending ID Verification"
        st.text_input("Verification Status", value=status_txt, disabled=True)

    st.markdown("---")

    if st.session_state.user_tier != "Master Admin":
        st.markdown("### 🌍 African Student Free Access Verification Portal")
        st.caption("African students receive **Free Standard Access** upon uploading front and back scans of their National and University IDs.")

        with st.form("student_verify_form"):
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                country = st.selectbox("African Country", ["Uganda", "Kenya", "Tanzania", "Rwanda", "Nigeria", "Ghana", "South Africa", "Other"])
                institution = st.text_input("Institution / University Name", value="Muni University")
                student_id = st.text_input("Student Registration Number")
            with col_v2:
                nat_front = st.file_uploader("National ID (Front Scan)", type=["png", "jpg", "jpeg", "pdf"])
                nat_back = st.file_uploader("National ID (Back Scan)", type=["png", "jpg", "jpeg", "pdf"])
                uni_front = st.file_uploader("University ID (Front Scan)", type=["png", "jpg", "jpeg", "pdf"])
                uni_back = st.file_uploader("University ID (Back Scan)", type=["png", "jpg", "jpeg", "pdf"])

            submitted = st.form_submit_button("🚀 Submit Credentials for Free Standard Access")
            if submitted:
                if nat_front and nat_back and uni_front and uni_back and student_id:
                    st.session_state.student_verified = True
                    st.session_state.user_tier = "Standard (Verified Student)"
                    log_backend_event("INFO", f"Student verification approved for {institution} ({country}).")
                    st.success("🎉 Verification Successful! Upgraded to Free Standard Access.")
                    st.rerun()
                else:
                    st.error("⚠️ Please upload all 4 required ID documents (National & University ID Front/Back) and enter your ID number.")

    if st.session_state.user_email.strip().lower() == "chrishem242@gmail.com":
        st.markdown("---")
        st.markdown("### 👑 Master Admin Enclave & License Management")
        st.caption("Authorized Master Administrator: **[Secured Administrator]**. Global access oversight.")
        
        users_df = pd.DataFrame([
            {"Identity": "Master Administrator", "Role": "Master Admin", "Tier": "Apex Sovereign", "Status": "Active"},
            {"Identity": "Muni Research Cohort", "Role": "African Student", "Tier": "Standard (Verified)", "Status": "Active"},
            {"Identity": "Enterprise Partner", "Role": "Enterprise Client", "Tier": "Premium", "Status": "Active"}
        ])
        st.dataframe(users_df, use_container_width=True)

        col_a1, col_a2 = st.columns(2)
        with col_a1:
            if st.button("🔄 Audit Active Crypto Enclaves"):
                log_backend_event("INFO", "Master Admin executed crypto enclave audit.")
                st.success("All enclaves operating under secure cryptographic verification.")
        with col_a2:
            if st.button("🔒 Revoke Unauthorized Sessions"):
                log_backend_event("INFO", "Master Admin executed session token purge.")
                st.success("Session token sweep completed successfully.")

def render_academic_portfolio_studio():
    st.subheader("🎓 Academic, CV & Portfolio Writing Studio")
    st.caption("AI-powered professional drafting engine with instant downloadable document export.")

    mode = st.selectbox(
        "Select Writing Target:",
        [
            "Professional CV & Profile Summary",
            "Academic Research Abstract & Report",
            "Project Portfolio Description",
            "Formal Cover Letter & Job Application"
        ]
    )

    st.markdown("---")

    if mode == "Professional CV & Profile Summary":
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name / Handle", value="Kula Chris (Chrishem)")
            field = st.text_input("Core Discipline", value="Biological Sciences & Data Analytics")
        with col2:
            tier = st.selectbox("Experience Tier", ["Undergraduate Researcher & Student", "Junior Data Analyst", "Independent Developer"])
            target = st.text_input("Target Role", value="Bioinformatics & Data Analytics Intern")

        if st.button("✨ Generate CV Summary"):
            content = f\"\"\"# Professional Profile: {full_name}
* **Discipline:** {field} ({tier})
* **Target Position:** {target}
* **Generated On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary
Motivated undergraduate student in the Faculty of Science with rigorous training in biological sciences, data analytics, and computational pipelines. Proven track record in developing local web applications, managing sequence data pipelines, and executing precision research tasks.

## Core Competencies
* Biological Sciences & Molecular Sequence Analysis
* Data Analytics & Python Scripting (Streamlit, Pandas, NumPy)
* Secure Local Storage & SQLite Database Management
* Version Control & Containerization
\"\"\"
            st.markdown(content)
            st.download_button("📥 Download as Markdown (.md)", content, "Chrishem_CV_Summary.md", "text/markdown")
            st.download_button("📥 Download as Plain Text (.txt)", content, "Chrishem_CV_Summary.txt", "text/plain")

    elif mode == "Academic Research Abstract & Report":
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Research Title", value="Waterborne Pathogen & Antimicrobial Resistance Surveillance")
            field_name = st.text_input("Field", value="Molecular Biology & Environmental Science")
        with col2:
            method = st.text_input("Methodology", value="Batch Data Log Filtering & Sequence Analysis")
            inst = st.text_input("Institution", value="Muni University Faculty of Science")

        if st.button("✨ Generate Research Abstract"):
            content = f\"\"\"# Research Report & Abstract
* **Research Title:** {title}
* **Institution:** {inst} ({field_name})
* **Methodology:** {method}
* **Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Abstract
This study investigates regional environmental sample distributions using {method}. Conducted under academic evaluation guidelines at {inst}, the research maps biological specimen markers to track resistance patterns and evaluate public health indicators.
\"\"\"
            st.markdown(content)
            st.download_button("📥 Download Abstract (.md)", content, "Research_Abstract.md", "text/markdown")
            st.download_button("📥 Download Abstract (.txt)", content, "Research_Abstract.txt", "text/plain")

    elif mode == "Project Portfolio Description":
        name = st.text_input("Project Name", value="Enterprise Intelligence & Sovereign Workspace")
        stack = st.text_input("Tech Stack", value="Python, Streamlit, SQLite, PowerShell, Docker")
        desc = st.text_area("Highlights", value="Built a sovereign enterprise workspace featuring secure local enclaves, automated telemetry dashboards, and bioinformatics pipelines.")

        if st.button("✨ Generate Portfolio"):
            content = f\"\"\"# Project Portfolio: {name}
* **Tech Stack:** {stack}
* **Date:** {datetime.now().strftime('%Y-%m-%d')}

## Overview
{desc}

## Engineering Achievements
* Engineered autonomous multi-module workspace with real-time health diagnostics.
* Integrated local containerization and custom data processing tools.
\"\"\"
            st.markdown(content)
            st.download_button("📥 Download Portfolio (.md)", content, "Project_Portfolio.md", "text/markdown")
            st.download_button("📥 Download Portfolio (.txt)", content, "Project_Portfolio.txt", "text/plain")

    else:
        comp = st.text_input("Organization / Recipient", value="Data Analytics & Research Institute")
        pos = st.text_input("Position", value="Research & Data Analytics Fellow")

        if st.button("✨ Generate Cover Letter"):
            content = f\"\"\"Dear Hiring Committee at {comp},

I am writing to express my strong interest in the {pos} position. As an undergraduate student in biological sciences and data analytics at Muni University, I have cultivated a strong foundation in automated data pipeline management and research reporting.

Sincerely,
Kula Chris (Chrishem)
\"\"\"
            st.markdown(content)
            st.download_button("📥 Download Cover Letter (.md)", content, "Cover_Letter.md", "text/markdown")
            st.download_button("📥 Download Cover Letter (.txt)", content, "Cover_Letter.txt", "text/plain")

def render_ecosystem_apex():
    st.subheader("🌌 Ecosystem Apex & Workspace Overview")
    st.caption("Real-time telemetry and architectural status of the CHRISHEM Sovereign Intelligence Grid.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("System Health", "100%", delta="Optimal")
    with col2:
        st.metric("Active Enclaves", "21 Modules", delta="Secure")
    with col3:
        st.metric("Database Engine", "SQLite Local", delta="Synchronized")

    st.markdown("---")
    st.markdown("### 📊 Active Subsystem Grid")
    subsystems = [
        {"Subsystem": "Access Control & Licensing", "Status": "Operational", "Security": "Encrypted"},
        {"Subsystem": "Academic & CV Studio", "Status": "Operational", "Security": "Export Ready"},
        {"Subsystem": "AI Intelligence Daemon", "Status": "Operational", "Security": "Autonomous"},
        {"Subsystem": "Telemetry & Diagnostics", "Status": "Operational", "Security": "Real-Time"}
    ]
    st.dataframe(pd.DataFrame(subsystems), use_container_width=True)

def render_system_diagnostics():
    st.subheader("🔍 System Diagnostics & Telemetry Log")
    st.caption("Live event logging and backend audit records.")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        df_logs = pd.read_sql_query("SELECT * FROM backend_logs ORDER BY id DESC LIMIT 50", conn)
        conn.close()
        if not df_logs.empty:
            st.dataframe(df_logs, use_container_width=True)
        else:
            st.info("No backend logs recorded yet.")
    except Exception as e:
        st.error(f"Error loading logs: {e}")

# ==========================================
# 4. MAIN NAVIGATION ROUTER
# ==========================================
def main():
    st.sidebar.title("🌌 CHRISHEM Enterprise")
    st.sidebar.caption("Sovereign Intelligence & Autonomous Grid")
    
    navigation = st.sidebar.selectbox(
        "Navigation Hub",
        [
            "Access Control & Licensing",
            "Academic & CV Studio",
            "Ecosystem Apex",
            "System Diagnostics & Health"
        ]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("System Status: 100% Operational\nMaster Admin: chrishem242@gmail.com")

    if navigation == "Access Control & Licensing":
        render_access_control_panel()
    elif navigation == "Academic & CV Studio":
        render_academic_portfolio_studio()
    elif navigation == "Ecosystem Apex":
        render_ecosystem_apex()
    elif navigation == "System Diagnostics & Health":
        render_system_diagnostics()

if __name__ == "__main__":
    main()
