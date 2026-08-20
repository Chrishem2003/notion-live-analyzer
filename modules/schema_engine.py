
import sqlite3
import json
import hashlib
from datetime import datetime
import pandas as pd
import streamlit as st

DB_FILE = "research_os.db"

def init_db():
    """Initializes relational tables for Unified Research Schema."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Table 1: Projects
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            project_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            principal_investigator TEXT NOT NULL,
            domain_tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Table 2: Grant Opportunities
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grant_opportunities (
            grant_id TEXT PRIMARY KEY,
            agency_name TEXT NOT NULL,
            call_title TEXT NOT NULL,
            funding_amount_usd REAL,
            deadline_date DATE,
            focus_keywords TEXT,
            raw_payload JSON
        );
    ''')

    # Table 3: Literature & Datasets
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS research_artifacts (
            artifact_id TEXT PRIMARY KEY,
            project_id TEXT,
            artifact_type TEXT CHECK(artifact_type IN ('Paper', 'FASTA', 'PDB', 'Satellite', 'Inventory')),
            uri_or_doi TEXT NOT NULL,
            metadata_json JSON,
            FOREIGN KEY (project_id) REFERENCES projects (project_id) ON DELETE CASCADE
        );
    ''')

    # Table 4: Project-Grant Alignments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_grant_alignments (
            alignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            grant_id TEXT NOT NULL,
            match_score REAL NOT NULL,
            status TEXT DEFAULT 'Unreviewed',
            FOREIGN KEY (project_id) REFERENCES projects (project_id) ON DELETE CASCADE,
            FOREIGN KEY (grant_id) REFERENCES grant_opportunities (grant_id) ON DELETE CASCADE
        );
    ''')

    # Table 5: FAIR Provenance Audit Log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS provenance_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            user_id TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sha256_hash TEXT NOT NULL
        );
    ''')

    conn.commit()
    conn.close()

def seed_sample_project():
    """Seeds default active project if table is empty."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM projects")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO projects (project_id, title, principal_investigator, domain_tags)
            VALUES (?, ?, ?, ?)
        ''', ("PRJ-2026-001", "Genomic & Environmental Surveillance System", "Kula Chris", "genomics,bioinformatics,satellite,pcr,pathway,surveillance"))
        conn.commit()
    conn.close()

def log_provenance(entity_id: str, action: str, user: str, payload_data: dict) -> str:
    """Computes SHA-256 hash and logs activity to database."""
    stamp = datetime.utcnow().isoformat()
    raw_str = f"{entity_id}:{action}:{user}:{stamp}:{json.dumps(payload_data, sort_keys=True)}"
    sha256 = hashlib.sha256(raw_str.encode('utf-8')).hexdigest()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO provenance_logs (entity_id, action_type, user_id, sha256_hash)
        VALUES (?, ?, ?, ?)
    ''', (entity_id, action, user, sha256))
    conn.commit()
    conn.close()
    return sha256

def render_schema_engine_tab():
    st.subheader("ðŸ—„ï¸ ResearchOS Unified Database Schema Explorer")
    st.caption("Live relational database architecture orchestrating research artifacts, projects, and provenance logs.")

    init_db()
    seed_sample_project()

    conn = sqlite3.connect(DB_FILE)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 📋 Active Research Projects")
        projects_df = pd.read_sql_query("SELECT * FROM projects", conn)
        st.dataframe(projects_df, use_container_width=True)

        st.markdown("### ðŸ“‚ Research Artifacts Ingested")
        artifacts_df = pd.read_sql_query("SELECT * FROM research_artifacts", conn)
        st.dataframe(artifacts_df, use_container_width=True)

    with col2:
        st.markdown("### ðŸ”’ Cryptographic Provenance Ledger")
        provenance_df = pd.read_sql_query("SELECT * FROM provenance_logs ORDER BY timestamp DESC LIMIT 10", conn)
        st.dataframe(provenance_df, use_container_width=True)

        st.markdown("### ðŸ’¡ Register New Project Artifact")
        with st.form("artifact_form"):
            art_id = st.text_input("Artifact ID", value="ART-909")
            proj_id = st.text_input("Project ID Target", value="PRJ-2026-001")
            art_type = st.selectbox("Type", ["Paper", "FASTA", "PDB", "Satellite", "Inventory"])
            uri = st.text_input("URI / DOI / Identifier", value="10.1038/s41587-026-001")
            submitted = st.form_submit_button("Register Artifact")
            if submitted:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO research_artifacts (artifact_id, project_id, artifact_type, uri_or_doi, metadata_json)
                    VALUES (?, ?, ?, ?, ?)
                ''', (art_id, proj_id, art_type, uri, json.dumps({"status": "verified"})))
                conn.commit()
                hash_val = log_provenance(art_id, "REGISTER_ARTIFACT", "chief.investigator@lab.org", {"uri": uri})
                st.success(f"Artifact registered successfully! Provenance Hash: `{hash_val[:16]}...`")
                st.rerun()

    conn.close()
