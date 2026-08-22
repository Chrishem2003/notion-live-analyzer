"""
CHRISHEM Unified Navigation Engine — role-based hub routing + global command search.
Defines the 11 consolidated hubs and their tool inventory.
"""

import streamlit as st

# ═══════════════════════════════════════════════════════════════════════
# HUB REGISTRY — THE SINGLE SOURCE OF TRUTH FOR NAVIGATION
# ═══════════════════════════════════════════════════════════════════════
HUBS = [
    {
        "id": "home",
        "icon": "🏠",
        "name": "Home Dashboard",
        "page": "pages/1_🏠_Home_Dashboard.py",
        "role": "all",
        "description": "System overview, quick access, saved analyses, live telemetry.",
        "tools": ["System Health", "Saved Analyses Vault", "Quick Access", "Live Telemetry"],
    },
    {
        "id": "data",
        "icon": "📁",
        "name": "Data Studio",
        "page": "pages/2_📁_Data_Studio.py",
        "role": "all",
        "description": "Ingest, inspect, clean, transform, simulate, and manage datasets.",
        "tools": [
            "File Ingestion", "Variable Editor", "Data Quality Audit",
            "Transform & Scrub", "Data Simulator", "Chart Data Extractor",
            "Merge & Combine",
        ],
    },
    {
        "id": "statistics",
        "icon": "📊",
        "name": "Statistics Studio",
        "page": "pages/3_📊_Statistics_Studio.py",
        "role": "all",
        "description": "Hypothesis testing, ANOVA, regression, power analysis, causal & Bayesian inference.",
        "tools": [
            "Parametric Tests", "Non-Parametric Tests", "Regression",
            "Categorical Analysis", "Causal Inference", "Bayesian Analysis",
            "Power & Sample Size", "Resampling & Bootstrap", "SPSS Suite",
            "Sensitivity Analysis",
        ],
    },
    {
        "id": "ml",
        "icon": "🤖",
        "name": "ML & Predictive Studio",
        "page": "pages/4_🤖_ML_Predictive_Studio.py",
        "role": "all",
        "description": "Automated machine learning, feature engineering, AI insights & anomaly detection.",
        "tools": [
            "AutoML Trainer", "Feature Engineering", "AI Insights",
            "Anomaly Detection", "Neural Forecasting", "Model Comparison",
        ],
    },
    {
        "id": "visualization",
        "icon": "📈",
        "name": "Visualization Studio",
        "page": "pages/5_📈_Visualization_Studio.py",
        "role": "all",
        "description": "Chart builder, dashboard canvas, presentations, and network graphs.",
        "tools": [
            "Chart Builder", "Dashboard Canvas", "Presentation Deck",
            "Network Graphs", "Chart Data Extractor", "Executive Reports",
        ],
    },
    {
        "id": "nlp",
        "icon": "💬",
        "name": "AI & NLP Studio",
        "page": "pages/6_💬_AI_NLP_Studio.py",
        "role": "all",
        "description": "Text mining, sentiment analysis, NL queries, research synthesis, audio engine.",
        "tools": [
            "Text Analysis", "Sentiment Scoring", "N-Gram Mining",
            "NL Query", "Research Synthesizer", "Interactive Audio",
            "Word Clouds",
        ],
    },
    {
        "id": "literature",
        "icon": "📚",
        "name": "Literature & Publishing Hub",
        "page": "pages/7_📚_Literature_Publishing_Hub.py",
        "role": "all",
        "description": "Literature search, meta-analysis, APA formatting, citations, grants, references.",
        "tools": [
            "Literature Search", "Meta-Analysis", "APA 7th Studio",
            "Citation Inspector", "Grant Formatter", "Reference Manager",
            "Publication Tables", "Research Gap Finder", "Hypothesis Bridge",
        ],
    },
    {
        "id": "domain",
        "icon": "🔬",
        "name": "Domain Analytics Hub",
        "page": "pages/8_🔬_Domain_Analytics_Hub.py",
        "role": "all",
        "description": "Specialized analytics: clinical, GIS, research quality, localization, protocols.",
        "tools": [
            "Clinical Analytics", "GIS Spatial", "Research Quality",
            "Global Localization", "Lab Protocols", "Global Radar",
            "Research Gap Solver",
        ],
    },
    {
        "id": "integrations",
        "icon": "🔗",
        "name": "Integrations Hub",
        "page": "pages/9_🔗_Integrations_Hub.py",
        "role": "all",
        "description": "Connect external systems: Notion, Google Sheets, Git, APIs, databases.",
        "tools": [
            "Notion Sync", "Google Sheets", "Git & Version Control",
            "External APIs", "Database Bridges", "Webhooks",
        ],
    },
    {
        "id": "admin",
        "icon": "🛡️",
        "name": "Admin & Security Center",
        "page": "pages/10_🛡️_Admin_Security_Center.py",
        "role": "admin",
        "description": "Settings, diagnostics, security vault, audit compliance, licensing, telemetry.",
        "tools": [
            "System Settings", "Diagnostics & Health", "Security Vault",
            "Audit & Compliance", "Licensing & Access", "Admin Billing",
            "Telemetry & Webhooks", "AI Defensive Cores",
        ],
    },
    {
        "id": "collaboration",
        "icon": "🤝",
        "name": "Collaboration & Portfolio",
        "page": "pages/11_🤝_Collaboration_Portfolio.py",
        "role": "all",
        "description": "Project collaboration, application pipeline, agent swarms, academic portfolio.",
        "tools": [
            "Project Collaboration", "Application Pipeline",
            "Agent Swarm Console", "Academic Portfolio", "Grant Writing",
        ],
    },
    {
        "id": "forensics",
        "icon": "🕵️",
        "name": "Forensics Intelligence",
        "page": "pages/12_🕵️_Forensics_Intelligence.py",
        "role": "all",
        "description": "Digital evidence lab, metadata & EXIF extraction, steganography detection, phishing analysis, chain-of-custody.",
        "tools": [
            "Digital Evidence Lab", "Metadata & EXIF Forensics",
            "Steganography Detector", "Phishing Analyzer", "Chain-of-Custody Vault",
            "File Hashing & Carving",
        ],
    },
    {
        "id": "converter",
        "icon": "🔄",
        "name": "Universal Converter",
        "page": "pages/13_🔄_Universal_Converter.py",
        "role": "all",
        "description": "Convert formats, encodings, reshape data, units, coordinates, and extract PDFs.",
        "tools": [
            "Format Converter", "Encoding Converter", "Data Reshaper",
            "Unit Converter", "Coordinate Converter", "PDF Extractor",
        ],
    },
    {
        "id": "threat",
        "icon": "🛡️",
        "name": "Threat & Scanner Suite",
        "page": "pages/14_🛡️_Threat_Scanner_Suite.py",
        "role": "all",
        "description": "PII/secret scanning, live CVE, malware signatures, integrity monitoring, port scanning, threat intelligence, incident playbooks.",
        "tools": [
            "PII & Secret Scanner", "Live CVE Scanner", "Malware Signature Scan",
            "File Integrity Monitor", "Port Scanner", "Threat Intelligence",
            "Incident Playbooks",
        ],
    },
    {
        "id": "mission",
        "icon": "🌍",
        "name": "Global Mission Control",
        "page": "pages/15_🌍_Global_Mission_Control.py",
        "role": "all",
        "description": "Live global health feed, real-time climate telemetry, impact scorecard, problem-solver registry.",
        "tools": [
            "Live Health Feed", "Climate Telemetry", "Global Impact Scorecard",
            "Problem Solver Registry", "Mission Telemetry",
        ],
    },
]


def get_user_role():
    """Get the current user's role for RBAC filtering."""
    identity = st.session_state.get("user_identity", {})
    return identity.get("role", "Data Analyst")


def is_admin():
    """Check if current user has admin privileges."""
    role = get_user_role()
    return "admin" in role.lower() or "sovereign" in role.lower() or "owner" in role.lower() or "superuser" in role.lower()


def visible_hubs():
    """Return hubs accessible to the current user."""
    if is_admin():
        return HUBS
    return [h for h in HUBS if h.get("role") != "admin"]


def render_sidebar_navigation():
    """
    Render the unified sidebar navigation menu with tool discovery.
    Returns the selected hub ID.
    """
    hubs = visible_hubs()

    st.sidebar.markdown("### 🧭 Navigation Hub")
    nav_labels = [f"{h['icon']} {h['name']}" for h in hubs]

    # Preserve selection across reruns
    if "nav_selection" not in st.session_state:
        st.session_state["nav_selection"] = nav_labels[0]

    selection = st.sidebar.radio(
        "Select Workspace",
        options=nav_labels,
        label_visibility="collapsed",
    )
    st.session_state["nav_selection"] = selection

    # Find selected hub
    selected = next((h for h in hubs if f"{h['icon']} {h['name']}" == selection), hubs[0])

    # Tool discovery under selected hub
    with st.sidebar.expander(f"🔍 {selected['name']} Tools", expanded=False):
        for tool in selected["tools"]:
            st.markdown(f"- {tool}")

    return selected


def render_global_command_search():
    """
    Render a global tool search box that helps users find any tool across hubs.
    """
    st.sidebar.markdown('<div class="chris-hr"></div>', unsafe_allow_html=True)
    st.sidebar.markdown("### 🔎 Command Search")
    query = st.sidebar.text_input("Search all tools...", placeholder="e.g., ANOVA, sentiment, git")

    if query and len(query.strip()) >= 2:
        query_lower = query.strip().lower()
        results = []
        for hub in HUBS:
            for tool in hub["tools"]:
                if query_lower in tool.lower():
                    results.append((hub["icon"], hub["name"], tool))

        if results:
            with st.sidebar.expander(f"Found {len(results)} tool(s)", expanded=True):
                for hub_icon, hub_name, tool in results[:8]:
                    st.markdown(f"{hub_icon} **{hub_name}** → `{tool}`")
        else:
            st.sidebar.caption("No matching tools found.")


def render_sidebar_footer():
    """Render the standard sidebar footer."""
    st.sidebar.markdown('<div class="chris-hr"></div>', unsafe_allow_html=True)
    st.sidebar.caption("SYSTEM STATUS")
    st.sidebar.success("[OK] Operational")
    st.sidebar.info("[SECURE] Sovereign Enclave")


# ═══════════════════════════════════════════════════════════════════════
# HOME QUICK-ACCESS CARDS
# ═══════════════════════════════════════════════════════════════════════
def hub_quick_access_cards():
    """Render quick-access cards for all hubs (used on Home Dashboard)."""
    hubs = visible_hubs()
    cols = st.columns(3)
    for idx, hub in enumerate(hubs):
        with cols[idx % 3]:
            st.markdown(
                f"""
                <div class="chris-card" style="cursor:pointer; min-height:120px;">
                    <div style="font-size:1.8rem;">{hub['icon']}</div>
                    <div style="font-size:1.05rem; font-weight:800; color:#00f2fe; margin:0.3rem 0;">{hub['name']}</div>
                    <div style="font-size:0.8rem; color:#94a3b8;">{hub['description']}</div>
                    <div style="font-size:0.7rem; color:#64748b; margin-top:0.4rem; font-family:monospace;">{len(hub['tools'])} tools</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

