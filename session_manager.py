"""
CHRISHEM Unified Session Manager â€” central data state management.
Ensures datasets flow seamlessly across all hub pages (Data Studio â†’ Statistics â†’ ML â†’ Visualization â†’ Export).
"""

import hashlib
import json
import sqlite3
import datetime

import numpy as np
import pandas as pd
import streamlit as st


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# SESSION STATE KEYS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
DATA_KEYS = ["uploaded_df", "active_df", "working_df", "working_transform_df", "notion_df"]

ALIASES = {
    "active_df": ["uploaded_df", "working_df", "working_transform_df", "notion_df"],
    "working_df": ["uploaded_df", "active_df", "working_transform_df", "notion_df"],
}


def init_session():
    """Initialize all default session state keys."""
    defaults = {
        "theme_mode": "dark",
        "user_identity": {"name": "Analyst", "role": "Data Analyst", "is_admin": False},
        "dataset_registry": {},
        "analysis_history": [],
        "data_source": "none",
        "source_name": "dataset.csv",
        "transform_log": [],
        "admin_logs": ["[INIT] Unified CHRISHEM Platform initialized."],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def get_active_dataframe():
    """
    Retrieve the first available dataframe from session state.
    Priority: active_df > uploaded_df > working_df > working_transform_df > notion_df
    """
    for key in DATA_KEYS:
        df = st.session_state.get(key)
        if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
            return df
    return None


def set_active_dataframe(df: pd.DataFrame, source_name: str = "dataset.csv"):
    """Set the active dataset across all standard session keys."""
    st.session_state["active_df"] = df
    st.session_state["uploaded_df"] = df
    st.session_state["working_df"] = df.copy()
    st.session_state["data_source"] = "uploaded" if source_name != "notion" else "notion"
    st.session_state["source_name"] = source_name
    _register_dataset(df, source_name)


def _register_dataset(df: pd.DataFrame, source_name: str):
    """Track dataset metadata in the registry for audit purposes."""
    if df is None or df.empty:
        return
    checksum = hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()[:16]
    registry = st.session_state.get("dataset_registry", {})
    registry[checksum] = {
        "source": source_name,
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "timestamp": datetime.datetime.now().isoformat(),
    }
    st.session_state["dataset_registry"] = registry


def dataset_summary():
    """Return a dict summarizing the active dataset for the sidebar HUD."""
    df = get_active_dataframe()
    if df is None:
        return None
    num_cols = len(df.select_dtypes(include=[np.number]).columns)
    cat_cols = len(df.select_dtypes(include=["object", "category"]).columns)
    missing = int(df.isnull().sum().sum())
    return {
        "rows": len(df),
        "cols": len(df.columns),
        "numeric": num_cols,
        "categorical": cat_cols,
        "missing": missing,
        "source": st.session_state.get("source_name", "unknown"),
        "checksum": hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()[:12],
    }


def log_analysis(title: str, category: str, content: str):
    """Append an analysis record to session history and SQLite vault."""
    history = st.session_state.get("analysis_history", [])
    history.append({
        "title": title,
        "category": category,
        "timestamp": datetime.datetime.now().isoformat(),
        "content": content,
    })
    st.session_state["analysis_history"] = history

    try:
        conn = _get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO saved_analyses (title, timestamp, category, content) VALUES (?, ?, ?, ?)",
            (title, datetime.datetime.now().isoformat(), category, content),
        )
        conn.commit()
    except Exception:
        pass


def _get_db():
    """Open (and initialize) the sovereign database connection."""
    conn = sqlite3.connect("sovereign_apex_engine.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            timestamp TEXT,
            category TEXT,
            content TEXT
        )
    """)
    conn.commit()
    return conn


def generate_sample_dataset(kind: str = "clinical") -> pd.DataFrame:
    """Generate curated sample datasets for demos and tutorials."""
    np.random.seed(42)
    if kind == "clinical":
        return pd.DataFrame({
            "Patient_ID": [f"PT-{i:04d}}" for i in range(1, 151)],
            "Age": np.random.randint(22, 78, 150),
            "Gender": np.random.choice(["Male", "Female"], 150),
            "Weight_kg": np.round(np.random.normal(74, 14, 150), 1),
            "Height_cm": np.round(np.random.normal(170, 9, 150), 1),
            "Systolic_BP": np.random.randint(105, 170, 150),
            "Diastolic_BP": np.random.randint(70, 105, 150),
            "Total_Cholesterol": np.random.randint(160, 275, 150),
            "Fasting_Glucose": np.random.randint(80, 150, 150),
            "Treatment_Group": np.random.choice(["Placebo", "Low Dose", "High Dose"], 150),
        })
    elif kind == "marketing":
        return pd.DataFrame({
            "Customer_ID": [f"CUST-{i:05d}}" for i in range(1, 201)],
            "Age": np.random.randint(18, 65, 200),
            "Region": np.random.choice(["North", "South", "East", "West"], 200),
            "Annual_Income": np.round(np.random.uniform(25000, 150000, 200), 2),
            "Spending_Score": np.round(np.random.uniform(1, 100, 200), 1),
            "Loyalty_Tier": np.random.choice(["Bronze", "Silver", "Gold", "Platinum"], 200),
        })
    elif kind == "sales":
        return pd.DataFrame({
            "Order_ID": [f"ORD-{i:05d}}" for i in range(1, 301)],
            "Date": pd.date_range(end=datetime.date.today(), periods=300, freq="D"),
            "Product_Category": np.random.choice(["Electronics", "Apparel", "Groceries", "Furniture"], 300),
            "Units_Sold": np.random.randint(1, 50, 300),
            "Unit_Price": np.round(np.random.uniform(5, 500, 300), 2),
            "Region": np.random.choice(["North America", "Europe", "Asia", "Africa"], 300),
        })
    elif kind == "genomic":
        return pd.DataFrame({
            "Gene_ID": [f"GENE-{i:04d}}" for i in range(1, 101)],
            "Expression_Level": np.round(np.random.normal(12.5, 3.5, 100), 2),
            "Protein_Density": np.round(np.random.uniform(0.1, 8.0, 100), 2),
            "Mutation_Count": np.random.randint(0, 15, 100),
            "Pathway_Type": np.random.choice(["Metabolic", "Signaling", "Structural"], 100),
        })
    elif kind == "survey":
        return pd.DataFrame({
            "Respondent_ID": [f"RESP-{i:04d}}" for i in range(1, 251)],
            "Age_Group": np.random.choice(["18-25", "26-35", "36-45", "46-60", "60+"], 250),
            "Satisfaction_Score": np.random.randint(1, 6, 250),
            "NPS_Category": np.random.choice(["Detractor", "Passive", "Promoter"], 250),
            "Feedback_Length_Chars": np.random.randint(10, 500, 250),
        })
    else:  # research cohort
        return pd.DataFrame({
            "Subject_ID": [f"SUBJ-{2000 + i}}" for i in range(250)],
            "Age": np.random.randint(18, 75, size=250),
            "Biomarker_A": np.round(np.random.normal(190.0, 30.0, size=250), 1),
            "Biomarker_B": np.round(np.random.normal(98.0, 15.0, size=250), 1),
            "Risk_Category": np.random.choice(["Low", "Moderate", "High"], size=250),
        })


def render_sidebar_data_hud():
    """
    Render a compact dataset summary card in the sidebar.
    Shows active source, shape, and quick actions.
    """
    summary = dataset_summary()
    st.sidebar.markdown('<div class="chris-hr"></div>', unsafe_allow_html=True)
    st.sidebar.markdown("### ðŸ“Š Active Dataset")

    if summary is None:
        st.sidebar.warning("No dataset loaded")
        if st.sidebar.button("ðŸŽ² Load Sample Data", use_container_width=True):
            set_active_dataframe(generate_sample_dataset(), "sample_research_cohort.csv")
            st.rerun()
        return

    st.sidebar.markdown(
        f"""
        <div style="background:#0b1321; border:1px solid #1e293b; border-radius:10px; padding:0.8rem;">
            <div style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase; font-weight:700;">{summary['source']}</div>
            <div style="font-size:1.1rem; font-weight:800; color:#00f2fe; margin:0.2rem 0;">{summary['rows']:,} rows Ã— {summary['cols']} cols</div>
            <div style="font-size:0.8rem; color:#cbd5e1;">
                ðŸ”¢ {summary['numeric']} numeric | ðŸ·ï¸ {summary['categorical']} categorical | âš ï¸ {summary['missing']:,} missing
            </div>
            <div style="font-size:0.7rem; color:#64748b; font-family:monospace; margin-top:0.3rem;">SHA: {summary['checksum']}...</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.sidebar.button("ðŸ—‘ï¸ Clear Dataset", use_container_width=True):
        for key in DATA_KEYS:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state["data_source"] = "none"
        st.rerun()

