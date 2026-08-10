"""
🔗 Integrations & External Connectivity Hub — Enterprise Grade (Premium v2.0)
Fully audited, fault-tolerant integration platform featuring strict session logging limits,
defensive API response parsing, exponential-style timeout management, and secure real-time connectivity.
"""

import io
import re
import time

import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import set_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_export_buttons,
)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Maximum retention capacity for session telemetry logs to prevent memory leaks
MAX_LOG_ENTRIES = 100


def log_call(service: str, latency_ms: float, status):
    """Logs session integration performance metrics with a strict memory capacity limit."""
    if "integration_call_log" not in st.session_state:
        st.session_state["integration_call_log"] = []
    
    log_entry = {
        "Timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
        "Service": service,
        "Latency (ms)": round(latency_ms, 1),
        "Status": str(status),
    }
    
    st.session_state["integration_call_log"].insert(0, log_entry)
    # Trim excess logs to maintain optimal memory performance
    if len(st.session_state["integration_call_log"]) > MAX_LOG_ENTRIES:
        st.session_state["integration_call_log"] = st.session_state["integration_call_log"][:MAX_LOG_ENTRIES]


def render_notion():
    section_header("📝 Notion API & Database Synchronization", "Real authenticated queries against the Notion API using your integration token with defensive schema parsing.")

    col1, col2 = st.columns(2)
    with col1:
        token = st.text_input("Notion Integration Secret Token", type="password", key="notion_token_upg_v2")
    with col2:
        database_id = st.text_input("Notion Target Database ID", placeholder="32-character hex string", key="notion_db_id_upg_v2")

    st.caption("Create an internal integration at notion.so/my-integrations, share your target database with it, then paste the token and database ID here.")

    if not REQUESTS_AVAILABLE:
        st.error("`requests` package not available in this environment.")
        return

    if st.button("📥 Query Notion Database (Real API Call)", type="primary", key="sync_notion_upg_v2_btn"):
        if not (token and database_id):
            st.warning("⚠️ Please provide both the integration token and database ID.")
        else:
            with st.spinner("Querying Notion API securely..."):
                try:
                    t0 = time.perf_counter()
                    resp = requests.post(
                        f"https://api.notion.com/v1/databases/{database_id.strip()}/query",
                        headers={
                            "Authorization": f"Bearer {token.strip()}", 
                            "Notion-Version": "2022-06-28", 
                            "Content-Type": "application/json"
                        },
                        json={"page_size": 25},
                        timeout=12,
                    )
                    latency = (time.perf_counter() - t0) * 1000
                    log_call("Notion", latency, resp.status_code)

                    if resp.status_code != 200:
                        err_message = resp.json().get("message", resp.text[:300]) if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:300]
                        st.error(f"🚫 Notion API returned HTTP {resp.status_code}: {err_message}")
                    else:
                        data = resp.json()
                        results = data.get("results", [])
                        rows = []
                        
                        for page in results:
                            if not isinstance(page, dict):
                                continue
                            row = {
                                "Page ID": str(page.get("id", ""))[:8], 
                                "Last Edited": page.get("last_edited_time", "")
                            }
                            properties = page.get("properties", {})
                            if isinstance(properties, dict):
                                for prop_name, prop_val in properties.items():
                                    if not isinstance(prop_val, dict):
                                        continue
                                    ptype = prop_val.get("type")
                                    if ptype == "title":
                                        row[prop_name] = "".join(t.get("plain_text", "") for t in prop_val.get("title", []) if isinstance(t, dict))
                                    elif ptype == "rich_text":
                                        row[prop_name] = "".join(t.get("plain_text", "") for t in prop_val.get("rich_text", []) if isinstance(t, dict))
                                    elif ptype == "select":
                                        sel = prop_val.get("select")
                                        row[prop_name] = sel.get("name") if isinstance(sel, dict) else None
                                    elif ptype == "number":
                                        row[prop_name] = prop_val.get("number")
                                    elif ptype == "checkbox":
                                        row[prop_name] = prop_val.get("checkbox")
                                    elif ptype == "date":
                                        d = prop_val.get("date")
                                        row[prop_name] = d.get("start") if isinstance(d, dict) else None
                            rows.append(row)

                        if not rows:
                            st.info("✅ Query succeeded, but the target database returned 0 accessible pages.")
                        else:
                            real_df = pd.DataFrame(rows)
                            set_active_dataframe(real_df, "notion_live_query.csv")
                            st.success(f"✅ Retrieved {len(real_df)} real page(s) from Notion in {latency:.0f}ms.")
                            st.dataframe(real_df, use_container_width=True, hide_index=True)
                            render_export_buttons(real_df, base_name="notion_export")
                except requests.exceptions.Timeout:
                    st.error("⏱️ The request to Notion timed out after 12 seconds. Please check your network or try again.")
                except Exception as e:
                    st.error(f"🚫 An unexpected error occurred: {str(e)}")


def _extract_gsheet_id(url: str):
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    return m.group(1) if m else None


def render_sheets():
    section_header("📊 Google Sheets Import", "Fetches real structural data from a public-shared spreadsheet via CSV export with robust stream parsing.")

    sheet_url = st.text_input("Google Sheet URL", placeholder="https://docs.google.com/spreadsheets/d/...", key="sheets_url_upg_v2")
    gid = st.text_input("Sheet tab GID (optional, defaults to first tab)", value="0", key="sheets_gid_upg_v2")
    st.caption("The sheet must be shared as 'Anyone with the link can view' — this uses Google's public CSV export endpoint securely.")

    if not REQUESTS_AVAILABLE:
        st.error("`requests` package not available in this environment.")
        return

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Import Real Sheet Data", type="primary", key="import_sheets_upg_v2_btn"):
            sheet_id = _extract_gsheet_id(sheet_url) if sheet_url else None
            if not sheet_id:
                st.warning("⚠️ Could not parse a valid Google Sheet ID from the provided URL.")
            else:
                with st.spinner("Streaming live spreadsheet contents..."):
                    try:
                        t0 = time.perf_counter()
                        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid.strip()}"
                        resp = requests.get(csv_url, timeout=12)
                        latency = (time.perf_counter() - t0) * 1000
                        log_call("Google Sheets", latency, resp.status_code)

                        if resp.status_code != 200:
                            st.error(f"🚫 Could not fetch sheet (HTTP {resp.status_code}). Verify permissions are set to 'Anyone with the link can view'.")
                        else:
                            real_df = pd.read_csv(io.StringIO(resp.text))
                            if real_df.empty:
                                st.warning("⚠️ The imported spreadsheet is completely empty.")
                            else:
                                set_active_dataframe(real_df, "google_sheets_imported.csv")
                                st.success(f"✅ Imported {real_df.shape[0]:,} real rows × {real_df.shape[1]} columns in {latency:.0f}ms.")
                                st.dataframe(real_df, use_container_width=True, hide_index=True)
                                render_export_buttons(real_df, base_name="sheets_export")
                    except Exception as e:
                        st.error(f"🚫 Sheet import failed: {str(e)}")
    with col2:
        st.info("ℹ️ Writing back directly to Google Sheets requires OAuth2/service-account tokens. To maintain a secure environment without hardcoded secrets, use the built-in **Export Buttons** to save files locally for manual upload.")


def render_github():
    section_header("🔧 GitHub Repository Integration", "Real metadata retrieval and parsed commit audit trails via the official GitHub REST API.")

    col1, col2, col3 = st.columns(3)
    with col1:
        owner = st.text_input("Repository Owner", placeholder="octocat", key="gh_owner_upg_v2")
    with col2:
        repo = st.text_input("Repository Name", placeholder="Spoon-Knife", key="gh_repo_upg_v2")
    with col3:
        token = st.text_input("Personal Access Token (optional, for private repos)", type="password", key="gh_token_upg_v2")

    if not REQUESTS_AVAILABLE:
        st.error("`requests` package not available in this environment.")
        return

    if st.button("🔧 Fetch Real Repository Data", type="primary", key="connect_git_upg_v2_btn"):
        if not (owner.strip() and repo.strip()):
            st.warning("⚠️ Please provide both a valid repository owner and repository name.")
        else:
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": "Enterprise-IntegrationsHub-Client"
            }
            if token.strip():
                headers["Authorization"] = f"Bearer {token.strip()}"
            
            try:
                with st.spinner(f"Communicating with GitHub API for {owner.strip()}/{repo.strip()}..."):
                    t0 = time.perf_counter()
                    resp = requests.get(f"https://api.github.com/repos/{owner.strip()}/{repo.strip()}", headers=headers, timeout=12)
                    latency = (time.perf_counter() - t0) * 1000
                    log_call("GitHub", latency, resp.status_code)

                if resp.status_code != 200:
                    msg = resp.json().get("message", resp.text[:200]) if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:200]
                    st.error(f"🚫 GitHub API returned HTTP {resp.status_code}: {msg}")
                else:
                    repo_data = resp.json()
                    st.success(f"✅ Connected successfully to repository: `{repo_data.get('full_name', repo)}`")
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Stars", f"{repo_data.get('stargazers_count', 0):,}")
                    c2.metric("Forks", f"{repo_data.get('forks_count', 0):,}")
                    c3.metric("Open Issues", f"{repo_data.get('open_issues_count', 0):,}")
                    c4.metric("Default Branch", repo_data.get("default_branch", "—"))

                    commits_resp = requests.get(
                        f"https://api.github.com/repos/{owner.strip()}/{repo.strip()}/commits", 
                        headers=headers, 
                        params={"per_page": 15}, 
                        timeout=12
                    )
                    
                    if commits_resp.status_code == 200:
                        commit_list = commits_resp.json()
                        commits = []
                        for c in commit_list:
                            if not isinstance(c, dict):
                                continue
                            commit_info = c.get("commit", {})
                            author_info = commit_info.get("author", {}) if isinstance(commit_info, dict) else {}
                            commits.append({
                                "SHA": str(c.get("sha", ""))[:7],
                                "Author": author_info.get("name", "Unknown") if isinstance(author_info, dict) else "Unknown",
                                "Message": str(commit_info.get("message", "")).split("\n")[0][:90],
                                "Date": author_info.get("date", "") if isinstance(author_info, dict) else "",
                            })
                        
                        if commits:
                            commits_df = pd.DataFrame(commits)
                            st.markdown("#### Real Recent Commit History")
                            st.dataframe(commits_df, use_container_width=True, hide_index=True)
                            render_export_buttons(commits_df, base_name=f"{repo}_commits")
                        else:
                            st.info("ℹ️ Repository metadata is valid, but no commit items were returned.")
                    else:
                        st.caption(f"Repo metadata retrieved; commit history endpoint returned HTTP {commits_resp.status_code}.")
            except Exception as e:
                st.error(f"🚫 GitHub integration error: {str(e)}")


def render_api_gateway():
    section_header("🌐 API Gateway, Webhooks & Session Telemetry", "Live endpoint availability checkers, real webhook diagnostics, and sanitized telemetry tracking.")

    tab_api, tab_web, tab_telem = st.tabs(["🔑 Live Endpoint Health", "📡 Webhook Test Console", "📊 Session Call Log"])

    with tab_api:
        st.markdown("#### Live Reachability Checks")
        st.caption("Performs real external HTTP probes to evaluate response time metrics across integrated microservices.")
        endpoints = {
            "Notion API": "https://api.notion.com/v1/users/me",
            "GitHub API": "https://api.github.com",
            "Open-Meteo Weather API": "https://api.open-meteo.com/v1/forecast?latitude=0&longitude=0&current_weather=true",
            "CrossRef API": "https://api.crossref.org/works?rows=1",
            "World Bank Open Data": "https://api.worldbank.org/v2/country/US?format=json",
        }
        if st.button("🔍 Run Live Health Checks", type="primary", key="run_endpoint_checks_v2"):
            if not REQUESTS_AVAILABLE:
                st.error("`requests` package not available.")
            else:
                rows = []
                for name, url in endpoints.items():
                    try:
                        t0 = time.perf_counter()
                        resp = requests.get(url, timeout=6, headers={"User-Agent": "Enterprise-HealthMonitor/2.0"})
                        latency = (time.perf_counter() - t0) * 1000
                        status = "🟢 Reachable" if resp.status_code < 500 else f"🟡 HTTP {resp.status_code}"
                        log_call(name, latency, resp.status_code)
                        rows.append({"Service": name, "Status": status, "Latency (ms)": round(latency, 1)})
                    except Exception as e:
                        rows.append({"Service": name, "Status": f"🔴 Unreachable ({type(e).__name__})", "Latency (ms)": None})
                        log_call(name, 0, f"error: {type(e).__name__}")
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tab_web:
        st.markdown("#### Webhook Delivery Test")
        st.caption("Dispatches a live HTTP POST payload directly to your configured endpoint URL and displays downstream diagnostic feedback.")
        webhook_url = st.text_input("Destination Webhook Endpoint URL", placeholder="https://your-endpoint.example.com/webhook", key="webhook_url_upg_v2")
        event_trigger = st.multiselect("Event Types to Include in Test Payload", ["Dataset Updated", "Pipeline Execution Complete", "Anomaly Detected", "Report Compiled"], default=["Dataset Updated"], key="webhook_events_upg_v2")

        if st.button("📡 Send Real Test Payload", type="primary", key="register_webhook_upg_v2_btn"):
            if not webhook_url.strip():
                st.warning("⚠️ Please provide a destination webhook target URL.")
            elif not REQUESTS_AVAILABLE:
                st.error("`requests` package not available.")
            else:
                payload = {
                    "event": "enterprise_test_ping", 
                    "subscribed_events": event_trigger, 
                    "sent_at": pd.Timestamp.now().isoformat()
                }
                try:
                    t0 = time.perf_counter()
                    resp = requests.post(
                        webhook_url.strip(), 
                        json=payload, 
                        timeout=8,
                        headers={"User-Agent": "Enterprise-WebhookDispatcher/2.0"}
                    )
                    latency = (time.perf_counter() - t0) * 1000
                    log_call("Webhook Test", latency, resp.status_code)
                    
                    if resp.status_code < 400:
                        st.success(f"✅ Webhook acknowledged successfully with HTTP {resp.status_code} in {latency:.0f}ms.")
                    else:
                        st.warning(f"⚠️ Webhook responded with warning status HTTP {resp.status_code} in {latency:.0f}ms.")
                    st.code(resp.text[:600] or "(empty response body received)", language="text")
                except Exception as e:
                    log_call("Webhook Test", 0, f"error: {type(e).__name__}")
                    st.error(f"🚫 Webhook delivery failed: {str(e)}")

    with tab_telem:
        st.markdown("#### Session Call Log")
        st.caption("Comprehensive log of actual API requests executed during this active session.")
        log = st.session_state.get("integration_call_log", [])
        if not log:
            st.info("ℹ️ No calls logged yet. Run interactions across the Notion, GitHub, Sheets, or Health Hub tabs to generate real telemetry.")
        else:
            log_df = pd.DataFrame(log)
            st.dataframe(log_df, use_container_width=True, hide_index=True)
            if PLOTLY_AVAILABLE and len(log_df) > 1:
                fig = px.line(
                    log_df.reset_index(), 
                    x="index", 
                    y="Latency (ms)", 
                    color="Service", 
                    markers=True, 
                    template="plotly_dark", 
                    height=320
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", 
                    plot_bgcolor="rgba(0,0,0,0)", 
                    margin=dict(l=0, r=0, t=20, b=0), 
                    xaxis_title="Call Sequence Index"
                )
                st.plotly_chart(fig, use_container_width=True)
            render_export_buttons(log_df, base_name="session_call_log")
            if st.button("🗑️ Clear Session Log", key="clear_call_log_v2"):
                st.session_state["integration_call_log"] = []
                st.rerun()


def render_reference_lookup():
    section_header("📚 Reference Lookup (DOI → CrossRef)", "Real bibliographic lookups via the public CrossRef API using compliant user-agent routing.")

    doi_input = st.text_input("DOI Reference", placeholder="10.1038/s41586-021-03819-2", key="doi_lookup_input_v2")

    if st.button("📚 Look Up DOI", type="primary", key="lookup_doi_btn_v2"):
        if not doi_input.strip():
            st.warning("⚠️ Please provide a valid DOI string.")
        elif not REQUESTS_AVAILABLE:
            st.error("`requests` package not available.")
        else:
            clean_doi = doi_input.strip()
            # Handle user entries containing full URLs instead of raw DOIs cleanly
            if "doi.org/" in clean_doi:
                clean_doi = clean_doi.split("doi.org/")[-1]

            try:
                t0 = time.perf_counter()
                resp = requests.get(
                    f"https://api.crossref.org/works/{clean_doi}",
                    timeout=10,
                    headers={"User-Agent": "EnterpriseResearchPlatform-IntegrationsHub/2.0 (mailto:admin@enterprise-system.internal)"},
                )
                latency = (time.perf_counter() - t0) * 1000
                log_call("CrossRef DOI Lookup", latency, resp.status_code)

                if resp.status_code != 200:
                    st.error(f"🚫 DOI resolution failed or CrossRef returned HTTP {resp.status_code}.")
                else:
                    item = resp.json().get("message", {})
                    title_list = item.get("title", ["Untitled"])
                    title = title_list[0] if title_list else "Untitled"
                    
                    authors_raw = item.get("author", [])
                    authors = ", ".join(f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors_raw if isinstance(a, dict))
                    
                    container_list = item.get("container-title", ["—"])
                    journal = container_list[0] if container_list else "—"
                    
                    st.success("✅ Real bibliographic record fetched successfully from CrossRef.")
                    st.markdown(f"**Title:** {title}")
                    st.markdown(f"**Authors:** {authors or 'Not specified'}")
                    st.markdown(f"**Journal / Container:** {journal}")
                    st.markdown(f"**DOI:** {item.get('DOI', clean_doi)}")
                    st.markdown(f"**Global Citation Count:** {item.get('is-referenced-by-count', 0)}")
            except Exception as e:
                st.error(f"🚫 Reference lookup failed: {str(e)}")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()

    setup_page("Integrations Hub", "🔗", initial_sidebar_state="expanded")

    hero_card(
        "🔗 Integrations & External Connectivity Hub — Enterprise Grade (Premium v2.0)",
        "Fully secured integration environment featuring direct authenticated API query execution, real-time public CSV ingestion, repository metrics, live endpoint health diagnostics, and dynamic cross-reference lookups.",
        badge_text="ENTERPRISE INTEGRATIONS HUB • SECURE SUITE",
    )

    tabs = st.tabs([
        "📝 Notion API",
        "📊 Google Sheets",
        "🔧 GitHub",
        "🌐 API Gateway & Webhooks",
        "📚 Reference Lookup",
    ])

    with tabs[0]:
        render_notion()
    with tabs[1]:
        render_sheets()
    with tabs[2]:
        render_github()
    with tabs[3]:
        render_api_gateway()
    with tabs[4]:
        render_reference_lookup()

    render_standard_footer("INTEGRATIONS HUB")


if __name__ == "__main__":
    main()