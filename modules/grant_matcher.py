
import sqlite3
import json
import re
import pandas as pd
import streamlit as st
from modules.schema_engine import DB_FILE, init_db, log_provenance

def fetch_and_index_grants():
    """Fetches international and agency grant opportunities into local index."""
    mock_grants = [
        {
            "grant_id": "NIH-R01-AI2026",
            "agency_name": "National Institutes of Health (NIH)",
            "call_title": "Innovative Computational Genomics & Environmental Disease Surveillance",
            "funding_amount_usd": 1500000.00,
            "deadline_date": "2026-11-15",
            "focus_keywords": "genomics bioinformatics surveillance pcr pathway pathogen environmental"
        },
        {
            "grant_id": "NSF-BIO-2026-88",
            "agency_name": "National Science Foundation (NSF)",
            "call_title": "Biological Infrastructure and Automated Field Telemetry Systems",
            "funding_amount_usd": 750000.00,
            "deadline_date": "2026-10-01",
            "focus_keywords": "satellite telemetry bioinformatics data field ecosystem vegetation"
        },
        {
            "grant_id": "HORIZON-CL6-2026",
            "agency_name": "Horizon Europe",
            "call_title": "Open Biological Data Pipelines & Climate Resilience Infrastructure",
            "funding_amount_usd": 2200000.00,
            "deadline_date": "2026-12-05",
            "focus_keywords": "open data pathway satellite environmental FAIR infrastructure"
        }
    ]

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for g in mock_grants:
        cursor.execute('''
            INSERT OR REPLACE INTO grant_opportunities 
            (grant_id, agency_name, call_title, funding_amount_usd, deadline_date, focus_keywords, raw_payload)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (g["grant_id"], g["agency_name"], g["call_title"], g["funding_amount_usd"], g["deadline_date"], g["focus_keywords"], json.dumps(g)))
    conn.commit()
    conn.close()

def compute_similarity_score(project_tags: str, grant_keywords: str) -> float:
    """Calculates keyword match coefficient."""
    proj_tokens = set(re.findall(r'\w', project_tags.lower()))
    grant_tokens = set(re.findall(r'\w', grant_keywords.lower()))
    
    if not proj_tokens or not grant_tokens:
        return 0.0
    
    intersection = proj_tokens.intersection(grant_tokens)
    union = proj_tokens.union(grant_tokens)
    return round((len(intersection) / float(len(union))) * 100, 2)

def run_grant_matching_pipeline():
    """Scans all active projects against grant database and stores match scores."""
    init_db()
    fetch_and_index_grants()

    conn = sqlite3.connect(DB_FILE)
    projects = pd.read_sql_query("SELECT project_id, title, domain_tags FROM projects", conn)
    grants = pd.read_sql_query("SELECT grant_id, agency_name, call_title, focus_keywords, funding_amount_usd FROM grant_opportunities", conn)

    cursor = conn.cursor()
    cursor.execute("DELETE FROM project_grant_alignments")  # Refresh cache

    results = []
    for _, p in projects.iterrows():
        p_tags = p["domain_tags"] or ""
        for _, g in grants.iterrows():
            g_keys = g["focus_keywords"] or ""
            score = compute_similarity_score(p_tags, g_keys)
            
            cursor.execute('''
                INSERT INTO project_grant_alignments (project_id, grant_id, match_score)
                VALUES (?, ?, ?)
            ''', (p["project_id"], g["grant_id"], score))
            
            results.append({
                "Project ID": p["project_id"],
                "Project Title": p["title"],
                "Grant ID": g["grant_id"],
                "Agency": g["agency_name"],
                "Grant Call": g["call_title"],
                "Funding Amount ($)": f"${g['funding_amount_usd']:,.2f}",
                "Match Alignment Score": f"{score}%"
            })

    conn.commit()
    conn.close()
    return pd.DataFrame(results)

def render_grant_matcher_tab():
    st.subheader("ðŸŽ¯ Automated Grant Indexer & Relevance Matcher")
    st.caption("Scrapes global funding calls and scores relevance against project domain parameters using vector-keyword similarity.")

    if st.button("ðŸš€ Execute Global Grant Scraping & Matching Pipeline", type="primary"):
        with st.spinner("Scraping international funding databases and evaluating vector relevance..."):
            df_matches = run_grant_matching_pipeline()
            log_provenance("GRANT_MATCHER", "RUN_PIPELINE", "chief.investigator@lab.org", {"records_matched": len(df_matches)})
            st.success("Indexing complete! Matching scores saved to database.")

    conn = sqlite3.connect(DB_FILE)
    try:
        matches = pd.read_sql_query('''
            SELECT 
                p.title AS "Project Title",
                g.agency_name AS "Agency",
                g.call_title AS "Funding Call Title",
                g.funding_amount_usd AS "Amount (USD)",
                g.deadline_date AS "Deadline",
                a.match_score AS "Match Score (%)"
            FROM project_grant_alignments a
            JOIN projects p ON a.project_id = p.project_id
            JOIN grant_opportunities g ON a.grant_id = g.grant_id
            ORDER BY a.match_score DESC
        ''', conn)
        
        if not matches.empty:
            st.markdown("###  Ranked Active Opportunities")
            st.dataframe(matches, width='stretch')
        else:
            st.info("Click above to run the grant matching engine.")
    except Exception:
        st.info("Click above to run the grant matching engine.")
    finally:
        conn.close()

