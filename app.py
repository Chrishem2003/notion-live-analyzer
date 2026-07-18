import os
import time
from datetime import datetime
from pathlib import Path
import base64
import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Live Notion Analyzer", layout="wide")


# (background discovery is redefined below to be robust across hosting providers)



def image_to_data_url(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    mime_map = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
        "svg": "image/svg+xml",
    }
    mime = mime_map.get(ext, "application/octet-stream")
    b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


# Make background path resolution robust across hosting providers (cwd may differ)
APP_DIR = Path(__file__).resolve().parent

def find_background_image():
    candidates = [
        APP_DIR / "background.png",
        APP_DIR / "background.jpg",
        APP_DIR / "background.jpeg",
        APP_DIR / "background.webp",
        APP_DIR / "background.gif",
        APP_DIR / "images" / "background.png",
        APP_DIR / "images" / "background.jpg",
        APP_DIR / "images" / "background.jpeg",
        APP_DIR / "images" / "background.webp",
        APP_DIR / "images" / "background.gif",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


background_path = find_background_image()
background_css = (
    "background: linear-gradient(180deg, rgba(248, 251, 255, 0.94), rgba(238, 244, 255, 0.94)), url('{image}') center/cover no-repeat;"
    if background_path
    else "background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);"
).format(image=image_to_data_url(background_path) if background_path else "")



st.markdown(
    """
    <style>
    .stApp {
        """ + background_css + """
        background-attachment: fixed;
        min-height: 100vh;
        background-size: cover;
    }
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        /* Darken/brighten veil so the background photo is visible but never fights the UI */
        background:
            linear-gradient(180deg, rgba(15, 23, 42, 0.55), rgba(15, 23, 42, 0.35)),
            radial-gradient(circle at top right, rgba(29, 78, 216, 0.28), transparent 55%),
            radial-gradient(circle at bottom left, rgba(255, 255, 255, 0.18), transparent 45%);
        pointer-events: none;
        z-index: 0;
    }

    /* Extra contrast layer to guarantee readability even on bright parts of the photo */
    .stApp::after {
        content: "";
        position: fixed;
        inset: 0;
        background: rgba(248, 251, 255, 0.20);
        pointer-events: none;
        z-index: 0;
    }

    .block-container {
        position: relative;
        z-index: 1;
        padding-top: 1.75rem !important;
        padding-bottom: 2rem !important;
        max-width: 1320px !important;
    }
    /* Make sidebar panel clearly readable even on complex photos */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(248, 251, 255, 0.96), rgba(241, 245, 249, 0.92));
        backdrop-filter: blur(16px);
        border-right: 1px solid rgba(189, 210, 255, 0.85);
        box-shadow: -12px 0 40px rgba(15, 23, 42, 0.10);
    }

    /* Reduce contrast clash on sidebar text */
    [data-testid="stSidebar"] * {
        text-shadow: none !important;
    }

    [data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-size: 1.65rem !important;
        font-weight: 800 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-weight: 700 !important;
    }
    .stPlotlyChart > div {
        border-radius: 18px;
        overflow: hidden;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
    }
    .hero-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(29, 78, 216, 0.92));
        color: white;
        padding: 1.35rem 1.5rem;
        border-radius: 22px;
        border: 1px solid rgba(255, 255, 255, 0.16);
        box-shadow: 0 18px 50px rgba(15, 23, 42, 0.25);
        backdrop-filter: blur(10px);
        margin-bottom: 1rem;
    }
    .hero-card h1 {
        color: #ffffff !important;
        margin-bottom: 0.15rem !important;
        font-size: 2rem !important;
        font-weight: 800 !important;
    }
    .hero-card p {
        color: #dbeafe !important;
        margin: 0.1rem 0 0.2rem 0 !important;
        font-size: 0.98rem !important;
    }
    .status-pill {
        display: inline-block;
        background: rgba(255,255,255,0.18);
        border: 1px solid rgba(255,255,255,0.22);
        color: #f8fafc;
        padding: 0.35rem 0.8rem;
        border-radius: 999px;
        font-size: 0.85rem;
        margin-top: 0.55rem;
        font-weight: 700;
    }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.78);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(219, 228, 244, 0.95);
        border-radius: 18px;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
        padding: 0.55rem 0.75rem;
    }
    .sidebar-card {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9));
        border: 1px solid rgba(219, 229, 248, 0.95);
        border-radius: 18px;
        padding: 0.95rem;
        margin: 0.45rem 0 0.9rem 0;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
    }
    .sidebar-card .stSubheader,
    .sidebar-card .stCaption {
        color: #0f172a !important;
    }
    .section-header {
        margin-top: 0.25rem;
        margin-bottom: 0.35rem;
    }
    .section-header h3 {
        color: #0f172a !important;
        font-size: 1.45rem !important;
        font-weight: 800 !important;
    }
    .live-badge {
        display: inline-block;
        padding: 0.35rem 0.8rem;
        border-radius: 999px;
        background: linear-gradient(135deg, #dbeafe, #bfdbfe);
        color: #1d4ed8;
        font-weight: 800;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }
    .sync-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(239, 246, 255, 0.92));
        border: 1px solid rgba(219, 229, 248, 0.95);
        border-radius: 18px;
        padding: 1rem 1.05rem;
        box-shadow: 0 14px 34px rgba(15, 23, 42, 0.1);
        margin-bottom: 1rem;
        backdrop-filter: blur(10px);
    }
    div[data-testid="stDataFrame"] {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 18px;
        overflow: hidden;
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
    }
    .stSubheader {
        color: #0f172a !important;
        font-weight: 800 !important;
    }
    .app-watermark {
        position: fixed;
        right: 1.2rem;
        bottom: 0.9rem;
        font-size: clamp(3rem, 8vw, 6rem);
        font-weight: 900;
        letter-spacing: 0.18em;
        color: rgba(15, 23, 42, 0.08);
        pointer-events: none;
        z-index: 0;
        user-select: none;
        text-transform: uppercase;
        text-shadow: 0 0 18px rgba(255, 255, 255, 0.35);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-card">
        <h1>📊 Live Notion Data Analyzer & Visualizer</h1>
        <p>This dashboard syncs in real-time with your Notion database.</p>
        <div class="status-pill">Live sync dashboard</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="app-watermark">CHRISHEM</div>', unsafe_allow_html=True)

if background_path:
    st.caption("🖼️ Background image detected and applied from the workspace.")


# 2. SECURE CONFIGURATION (Reads from Streamlit Secrets or environment variables)
def get_secret(name):
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name)


def extract_text_from_property(prop_value):
    if isinstance(prop_value, list):
        parts = []
        for item in prop_value:
            if isinstance(item, dict):
                plain_text = item.get("plain_text")
                if plain_text:
                    parts.append(plain_text)
        return "".join(parts) or "Unknown"

    if isinstance(prop_value, dict):
        if "title" in prop_value:
            return extract_text_from_property(prop_value.get("title", []))
        if "rich_text" in prop_value:
            return extract_text_from_property(prop_value.get("rich_text", []))
        if "text" in prop_value:
            return prop_value.get("text", {}).get("content", "Unknown")
        if "name" in prop_value:
            return prop_value.get("name", "Unknown")

    return str(prop_value) if prop_value is not None else "Unknown"


def extract_metric_from_property(prop_value):
    if isinstance(prop_value, dict):
        metric_value = prop_value.get("number")
        if metric_value is None:
            return 0.0
        return float(metric_value)
    return 0.0


def extract_status_from_property(prop_value):
    if isinstance(prop_value, dict):
        select_value = prop_value.get("select") or prop_value.get("status")
        if isinstance(select_value, dict):
            return select_value.get("name", "Unknown")
    return "Unknown"


def infer_notion_field_names(properties):
    title_field = None
    number_field = None
    status_field = None

    for prop_name, prop_value in properties.items():
        prop_type = prop_value.get("type") if isinstance(prop_value, dict) else None
        if prop_type == "title" and title_field is None:
            title_field = prop_name
        elif prop_type == "number" and number_field is None:
            number_field = prop_name
        elif prop_type in {"select", "status"} and status_field is None:
            status_field = prop_name

    return {
        "title": title_field,
        "number": number_field,
        "status": status_field,
    }


def get_database_options(token):
    url = "https://api.notion.com/v1/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    payload = {
        "query": "",
        "filter": {"property": "object", "value": "database"},
        "page_size": 100
    }

    databases = []

    try:
        has_more = True
        next_cursor = None

        while has_more:
            request_payload = payload.copy()
            if next_cursor:
                request_payload["start_cursor"] = next_cursor

            response = requests.post(url, json=request_payload, headers=headers)
            if response.status_code != 200:
                return databases

            data = response.json()
            for db in data.get("results", []):
                title = "".join(part.get("plain_text", "") for part in db.get("title", [])) or db["id"]
                databases.append({
                    "id": db["id"],
                    "title": title,
                    "properties": db.get("properties", {})
                })

            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")
    except Exception:
        return databases

    return databases


def discover_database_id(token):
    databases = get_database_options(token)
    best_match = None
    best_score = -1

    for db in databases:
        props = db.get("properties", {})
        score = 0

        property_types = {prop.get("type") for prop in props.values() if isinstance(prop, dict)}

        if "title" in property_types:
            score += 5
        if "number" in property_types:
            score += 5
        if {"select", "status"}.intersection(property_types):
            score += 5

        if score > best_score:
            best_score = score
            best_match = db["id"]

    return best_match


NOTION_TOKEN = get_secret("NOTION_TOKEN")
DATABASE_ID = get_secret("DATABASE_ID")
DATABASE_SOURCE = "configured"

missing_creds = []
if not NOTION_TOKEN:
    missing_creds.append("NOTION_TOKEN")

# Help diagnose “env vars ignored” issues on hosts
try:
    st.sidebar.caption(f"NOTION_TOKEN present: {bool(NOTION_TOKEN)}")
    st.sidebar.caption(f"DATABASE_ID present: {bool(DATABASE_ID)}")
except Exception:
    pass


if missing_creds:

    with st.container():
        st.error(
            "Notion credentials missing. "
            "Set the environment variables NOTION_TOKEN (required) and DATABASE_ID (optional)."
        )
        st.info("If DATABASE_ID is not set, the app will try to auto-discover a database.")
    st.stop()

if not DATABASE_ID:
    DATABASE_ID = discover_database_id(NOTION_TOKEN)
    DATABASE_SOURCE = "auto-discovered"
    if not DATABASE_ID:
        with st.container():
            st.error(
                "DATABASE_ID is missing and auto-discovery failed. "
                "Set DATABASE_ID to your Notion database id."
            )
        st.stop()


with st.sidebar:
    st.markdown("<div class='sidebar-card'>", unsafe_allow_html=True)
    st.subheader("Control Panel")
    st.caption("Live connection")

    refresh_options = {
        "Off": 0,
        "30 sec": 30,
        "60 sec": 60,
        "5 min": 300,
    }
    default_refresh_choice = st.session_state.get("refresh_choice", "30 sec")
    refresh_choice = st.selectbox(
        "Refresh cadence",
        list(refresh_options.keys()),
        index=list(refresh_options.keys()).index(default_refresh_choice) if default_refresh_choice in refresh_options else 1,
        key="refresh_choice",
    )
    refresh_seconds = refresh_options.get(refresh_choice, 30)
    st.caption(f"Current cadence: {refresh_choice}")
    st.caption("When enabled, the app reruns itself so the latest Notion updates appear automatically.")

    database_options = get_database_options(NOTION_TOKEN)
    option_ids = [db["id"] for db in database_options]
    option_names = {db["id"]: f"{db['title']} ({db['id']})" for db in database_options}

    if option_ids:
        search_term = st.text_input("Search databases", placeholder="Type a name or ID...")
        filtered_options = [
            db for db in database_options
            if not search_term or search_term.lower() in db["title"].lower() or search_term.lower() in db["id"].lower()
        ]
        filtered_ids = [db["id"] for db in filtered_options]
        filtered_names = {db["id"]: f"{db['title']} ({db['id']})" for db in filtered_options}

        if filtered_ids:
            default_index = filtered_ids.index(DATABASE_ID) if DATABASE_ID in filtered_ids else 0
            selected_db_id = st.selectbox(
                "Choose database",
                options=filtered_ids,
                index=default_index,
                format_func=lambda db_id: filtered_names.get(db_id, db_id),
            )
            DATABASE_ID = selected_db_id
            DATABASE_SOURCE = "selected in sidebar"
        else:
            st.info("No databases matched that search.")

    st.code(DATABASE_ID, language="text")
    st.caption(f"Source: {DATABASE_SOURCE}")
    st.caption(f"Visible database count: {len(database_options)}")
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🔄 Sync New Changes"):
        st.cache_data.clear()
        st.session_state["last_sync_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if "last_sync_time" not in st.session_state:
    st.session_state["last_sync_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if "next_auto_refresh_at" not in st.session_state:
    st.session_state["next_auto_refresh_at"] = time.time() + refresh_seconds

st.markdown(
    f"""
    <div class="sync-card">
        <div><strong>✅ Connected to Notion database</strong></div>
        <div class="live-badge">{DATABASE_ID}</div>
        <div style="margin-top: 0.45rem; color: #334155;">Source: {DATABASE_SOURCE}</div>
        <div style="margin-top: 0.35rem; color: #475569;">Last sync: {st.session_state['last_sync_time']}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if refresh_seconds > 0:
    current_ts = time.time()
    if current_ts >= st.session_state.get("next_auto_refresh_at", current_ts + refresh_seconds):
        st.session_state["next_auto_refresh_at"] = current_ts + refresh_seconds
        st.session_state["last_sync_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.cache_data.clear()
        if hasattr(st, "rerun"):
            st.rerun()
        else:
            st.experimental_rerun()

# 3. NOTION DATA FETCHER
def fetch_live_notion_data(token, db_id):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    rows = []
    has_more = True
    next_cursor = None
    
    while has_more:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor
            
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                error_text = response.text
                if "page, not a database" in error_text.lower() or ("provided id" in error_text.lower() and "page" in error_text.lower()):
                    discovered_db_id = discover_database_id(token)
                    if discovered_db_id and discovered_db_id != db_id:
                        st.info("A matching Notion database was found automatically. Switching to the correct database ID.")
                        db_id = discovered_db_id
                        url = f"https://api.notion.com/v1/databases/{db_id}/query"
                        response = requests.post(url, json=payload, headers=headers)
                    else:
                        st.error("The DATABASE_ID in your secrets is a Notion page ID, not a database ID. Open the target database in Notion and copy the database ID from the URL or database settings.")
                        return pd.DataFrame()

                if response.status_code != 200:
                    st.error(f"Notion API Error: Status {response.status_code} - {response.text}")
                    return pd.DataFrame()
                
            data = response.json()
            
            for page in data.get("results", []):
                props = page.get("properties", {})
                field_map = infer_notion_field_names(props)

                entity_id = extract_text_from_property(
                    props.get(field_map["title"], {}) if field_map["title"] else {}
                )
                metric_val = extract_metric_from_property(
                    props.get(field_map["number"], {}) if field_map["number"] else {}
                )
                status = extract_status_from_property(
                    props.get(field_map["status"], {}) if field_map["status"] else {}
                )

                rows.append({
                    "Entity ID": entity_id,
                    "Metric Value": float(metric_val),
                    "Upload Status": status
                })
                
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")
            
        except Exception as e:
            st.error(f"Network Connection Error: {str(e)}")
            return pd.DataFrame()
        
    return pd.DataFrame(rows)

# 4. DATA LOAD
df = fetch_live_notion_data(NOTION_TOKEN, DATABASE_ID)
st.session_state["last_sync_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 5. DASHBOARD LAYOUT
if df.empty:
    st.warning("⚠️ No data parsed yet. Check your Notion field names and API connections.")
else:
    st.markdown("<div class='section-header'><h3>Snapshot Overview</h3></div>", unsafe_allow_html=True)
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric("Total Tracked Entities", len(df))
    with kpi2:
        st.metric("Average Metric Score", f"{df['Metric Value'].mean():.2f}")
    with kpi3:
        completed = df['Upload Status'].str.contains("Sync Complete|Complete|Success", case=False, na=False).sum()
        st.metric("Total Successful Syncs", completed)

    st.markdown("---")
    viz1, viz2 = st.columns(2)
    
    with viz1:
        st.subheader("Performance Value by Entity")
        fig_bar = px.bar(
            df,
            x="Entity ID",
            y="Metric Value",
            color="Upload Status",
            text_auto=True,
            labels={"Metric Value": "Value Score", "Entity ID": "Trial ID"},
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Set2,
            height=430,
        )
        fig_bar.update_layout(
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            font=dict(color="#0f172a"),
            title_font_color="#0f172a",
            xaxis=dict(
                title=dict(text="Trial ID", font=dict(color="#0f172a")),
                tickfont=dict(color="#0f172a"),
            ),
            yaxis=dict(
                title=dict(text="Value Score", font=dict(color="#0f172a")),
                tickfont=dict(color="#0f172a"),
            ),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with viz2:
        st.subheader("Current Operational Pipeline Status")
        status_counts = df['Upload Status'].value_counts().reset_index()
        status_counts.columns = ['Upload Status', 'Count']
        fig_pie = px.pie(
            status_counts,
            values='Count',
            names='Upload Status',
            hole=0.45,
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            height=430,
        )
        fig_pie.update_layout(
            margin=dict(l=10, r=10, t=20, b=10),
            font=dict(color="#0f172a"),
            legend=dict(font=dict(color="#0f172a")),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Live Spreadsheet Record View")
    st.dataframe(df, use_container_width=True, hide_index=True)
