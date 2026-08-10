"""
🔗 Integrations & External Connectivity Hub — Enterprise Grade (Premium)
Real Notion API queries, real GitHub repository/commit data, public Google Sheet CSV import,
real webhook reachability testing, real endpoint health checks, and session-derived telemetry
built from actual calls made in this session.

Changelog vs prior version — literally every integration in this hub previously faked its
result regardless of what credentials or URLs were entered:
- FIXED (was 100% fake): Notion "sync" ignored whatever token/database ID you entered, slept for
  1 second, and returned a hardcoded demo dataframe every time. It now makes a real authenticated
  call to the Notion API (`POST /v1/databases/{id}/query`) using your integration token and
  parses the real page properties returned.
- FIXED (was 100% fake): Google Sheets import ignored the URL entirely and generated random demo
  biomarker data. Writing to a sheet genuinely requires OAuth2/service-account credentials this
  environment doesn't set up, so instead of faking that too, this now does something real that
  doesn't require OAuth: it fetches the actual sheet contents via the public CSV export endpoint
  (works for any sheet shared as "Anyone with the link can view"), parses real data, and is
  explicit that write-back needs a service account it doesn't have configured.
- FIXED (was 100% fake): "Establish Git Remote Connection" declared success for literally any
  non-empty string, then displayed a static, hardcoded commit log unrelated to any real
  repository. Replaced with a real GitHub API integration — enter an owner/repo, get the actual
  repo metadata and the actual last 10 commits.
- FIXED (was 100% fake): the webhook registration console accepted any URL and always reported
  success without sending anything. It now sends a real HTTP POST test payload to the URL and
  reports the actual status code and response.
- FIXED (was 100% fake): "Registered API Endpoints" was a static table that never changed. It now
  performs real live reachability checks (HTTP GET, measured latency) against each service.
- FIXED (was 100% fake): "Live Telemetry" plotted `np.random.uniform` numbers with a fake
  timestamp axis. It now logs the *actual* latency of every real API call made in this session
  (Notion queries, GitHub calls, webhook tests, endpoint pings) and charts that real log.
- FIXED (was 100% fake): Mendeley import ignored any real account and returned 4 hardcoded fake
  citations. Full Mendeley sync needs an OAuth login flow not implemented here, so instead of
  faking it, this section now does a real DOI lookup via the free CrossRef API (same one used in
  Literature Hub) — real bibliographic data for whatever DOI you provide.
"""

import io
import re
import time

import numpy as np
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


def log_call(service: str, latency_ms: float, status):
    if "integration_call_log" not in st.session_state:
        st.session_state["integration_call_log"] = []
    st.session_state["integration_call_log"].append({
        "Timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
        "Service": service,
        "Latency (ms)": round(latency_ms, 1),
        "Status": str(status),
    })


def render_notion():
    section_header("📝 Notion API & Database Synchronization", "Real authenticated queries against the Notion API using your integration token — no simulated results.")

    col1, col2 = st.columns(2)
    with col1:
        token = st.text_input("Notion Integration Secret Token", type="password", key="notion_token_upg")
    with col2:
        database_id = st.text_input("Notion Target Database ID", placeholder="32-character hex string", key="notion_db_id_upg")

    st.caption("Create an internal integration at notion.so/my-integrations, share your target database with it, then paste the token and database ID here.")

    if not REQUESTS_AVAILABLE:
        st.error("`requests` package not available in this environment.")
        return

    if st.button("📥 Query Notion Database (Real API Call)", type="primary", key="sync_notion_upg"):
        if not (token and database_id):
            st.warning("⚠️ Please provide both the integration token and database ID.")
        else:
            with st.spinner("Querying Notion API..."):
                try:
                    t0 = time.perf_counter()
                    resp = requests.post(
                        f"https://api.notion.com/v1/databases/{database_id}/query",
                        headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"},
                        json={"page_size": 20},
                        timeout=10,
                    )
                    latency = (time.perf_counter() - t0) * 1000
                    log_call("Notion", latency, resp.status_code)

                    if resp.status_code != 200:
                        st.error(f"🚫 Notion API returned HTTP {resp.status_code}: {resp.text[:300]}")
                    else:
                        results = resp.json().get("results", [])
                        rows = []
                        for page in results:
                            row = {"Page ID": page.get("id", "")[:8], "Last Edited": page.get("last_edited_time", "")}
                            for prop_name, prop_val in page.get("properties", {}).items():
                                ptype = prop_val.get("type")
                                if ptype == "title":
                                    row[prop_name] = "".join(t.get("plain_text", "") for t in prop_val.get("title", []))
                                elif ptype == "rich_text":
                                    row[prop_name] = "".join(t.get("plain_text", "") for t in prop_val.get("rich_text", []))
                                elif ptype == "select":
                                    sel = prop_val.get("select")
                                    row[prop_name] = sel.get("name") if sel else None
                                elif ptype == "number":
                                    row[prop_name] = prop_val.get("number")
                                elif ptype == "checkbox":
                                    row[prop_name] = prop_val.get("checkbox")
                                elif ptype == "date":
                                    d = prop_val.get("date")
                                    row[prop_name] = d.get("start") if d else None
                            rows.append(row)

                        if not rows:
                            st.info("✅ Query succeeded but the database returned 0 pages.")
                        else:
                            real_df = pd.DataFrame(rows)
                            set_active_dataframe(real_df, "notion_live_query.csv")
                            st.success(f"✅ Retrieved {len(real_df)} real page(s) from Notion in {latency:.0f}ms.")
                            st.dataframe(real_df, use_container_width=True, hide_index=True)
                            render_export_buttons(real_df, base_name="notion_export")
                except Exception as e:
                    st.error(f"🚫 Request failed: {e}")


def _extract_gsheet_id(url: str):
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    return m.group(1) if m else None


def render_sheets():
    section_header("📊 Google Sheets Import", "Fetches real data from a publicly-shared sheet via its CSV export endpoint — no OAuth setup required for this direction.")

    sheet_url = st.text_input("Google Sheet URL", placeholder="https://docs.google.com/spreadsheets/d/...", key="sheets_url_upg")
    gid = st.text_input("Sheet tab GID (optional, defaults to first tab)", value="0", key="sheets_gid_upg")
    st.caption("The sheet must be shared as 'Anyone with the link can view' — this uses Google's public CSV export, which needs no API key or OAuth.")

    if not REQUESTS_AVAILABLE:
        st.error("`requests` package not available in this environment.")
        return

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Import Real Sheet Data", type="primary", key="import_sheets_upg"):
            sheet_id = _extract_gsheet_id(sheet_url) if sheet_url else None
            if not sheet_id:
                st.warning("⚠️ Could not parse a valid Google Sheet ID from that URL.")
            else:
                with st.spinner("Fetching live sheet data..."):
                    try:
                        t0 = time.perf_counter()
                        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
                        resp = requests.get(csv_url, timeout=10)
                        latency = (time.perf_counter() - t0) * 1000
                        log_call("Google Sheets", latency, resp.status_code)

                        if resp.status_code != 200:
                            st.error(f"🚫 Could not fetch sheet (HTTP {resp.status_code}) — confirm sharing is set to 'Anyone with the link can view'.")
                        else:
                            real_df = pd.read_csv(io.StringIO(resp.text))
                            set_active_dataframe(real_df, "google_sheets_imported.csv")
                            st.success(f"✅ Imported {real_df.shape[0]:,} real rows × {real_df.shape[1]} columns in {latency:.0f}ms.")
                            st.dataframe(real_df, use_container_width=True, hide_index=True)
                    except Exception as e:
                        st.error(f"🚫 Import failed: {e}")
    with col2:
        st.info("ℹ️ Writing back to a Google Sheet requires an OAuth2 or service-account credential this environment doesn't have configured — that direction isn't faked here. Use **Export Buttons** elsewhere in the app to download your data, then paste/import it into Sheets manually.")


def render_github():
    section_header("🔧 GitHub Repository Integration", "Real repository metadata and commit history via the GitHub API — public repos work with no token; private repos need a personal access token.")

    col1, col2, col3 = st.columns(3)
    with col1:
        owner = st.text_input("Repository Owner", placeholder="anthropics", key="gh_owner_upg")
    with col2:
        repo = st.text_input("Repository Name", placeholder="claude-code", key="gh_repo_upg")
    with col3:
        token = st.text_input("Personal Access Token (optional, for private repos)", type="password", key="gh_token_upg")

    if not REQUESTS_AVAILABLE:
        st.error("`requests` package not available in this environment.")
        return

    if st.button("🔧 Fetch Real Repository Data", type="primary", key="connect_git_upg"):
        if not (owner.strip() and repo.strip()):
            st.warning("⚠️ Please provide both an owner and repository name.")
        else:
            headers = {"Accept": "application/vnd.github+json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            try:
                with st.spinner(f"Querying GitHub API for {owner}/{repo}..."):
                    t0 = time.perf_counter()
                    resp = requests.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers, timeout=10)
                    latency = (time.perf_counter() - t0) * 1000
                    log_call("GitHub", latency, resp.status_code)

                if resp.status_code != 200:
                    msg = resp.json().get("message", resp.text[:200]) if "application/json" in resp.headers.get("content-type", "") else resp.text[:200]
                    st.error(f"🚫 GitHub API returned HTTP {resp.status_code}: {msg}")
                else:
                    repo_data = resp.json()
                    st.success(f"✅ Connected to real repository `{repo_data['full_name']}`.")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Stars", f"{repo_data.get('stargazers_count', 0):,}")
                    c2.metric("Forks", f"{repo_data.get('forks_count', 0):,}")
                    c3.metric("Open Issues", f"{repo_data.get('open_issues_count', 0):,}")
                    c4.metric("Default Branch", repo_data.get("default_branch", "—"))

                    commits_resp = requests.get(f"https://api.github.com/repos/{owner}/{repo}/commits", headers=headers, params={"per_page": 10}, timeout=10)
                    if commits_resp.status_code == 200:
                        commits = [{
                            "SHA": c["sha"][:7],
                            "Author": (c.get("commit", {}).get("author") or {}).get("name", "Unknown"),
                            "Message": c.get("commit", {}).get("message", "").split("\n")[0][:80],
                            "Date": (c.get("commit", {}).get("author") or {}).get("date", ""),
                        } for c in commits_resp.json()]
                        commits_df = pd.DataFrame(commits)
                        st.markdown("#### Real Recent Commit History")
                        st.dataframe(commits_df, use_container_width=True, hide_index=True)
                        render_export_buttons(commits_df, base_name=f"{repo}_commits")
                    else:
                        st.caption(f"Repo metadata retrieved; commit history unavailable (HTTP {commits_resp.status_code}).")
            except Exception as e:
                st.error(f"🚫 Request failed: {e}")


def render_api_gateway():
    section_header("🌐 API Gateway, Webhooks & Session Telemetry", "Real endpoint reachability checks, real webhook delivery tests, and telemetry built from actual calls made in this session.")

    tab_api, tab_web, tab_telem = st.tabs(["🔑 Live Endpoint Health", "📡 Webhook Test Console", "📊 Session Call Log"])

    with tab_api:
        st.markdown("#### Live Reachability Checks")
        st.caption("Sends a real HTTP request to each service and measures actual latency — not a static table.")
        endpoints = {
            "Notion API": "https://api.notion.com/v1/users/me",
            "GitHub API": "https://api.github.com",
            "Open-Meteo Weather API": "https://api.open-meteo.com/v1/forecast?latitude=0&longitude=0&current_weather=true",
            "CrossRef API": "https://api.crossref.org/works?rows=1",
            "World Bank Open Data": "https://api.worldbank.org/v2/country/US?format=json",
        }
        if st.button("🔍 Run Live Health Checks", type="primary", key="run_endpoint_checks"):
            if not REQUESTS_AVAILABLE:
                st.error("`requests` package not available.")
            else:
                rows = []
                for name, url in endpoints.items():
                    try:
                        t0 = time.perf_counter()
                        resp = requests.get(url, timeout=6)
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
        st.caption("Sends a real HTTP POST with a test payload to the URL you provide and reports the actual response.")
        webhook_url = st.text_input("Destination Webhook Endpoint URL", placeholder="https://your-endpoint.example.com/webhook", key="webhook_url_upg")
        event_trigger = st.multiselect("Event Types to Include in Test Payload", ["Dataset Updated", "Pipeline Execution Complete", "Anomaly Detected", "Report Compiled"], default=["Dataset Updated"], key="webhook_events_upg")

        if st.button("📡 Send Real Test Payload", type="primary", key="register_webhook_upg"):
            if not webhook_url.strip():
                st.warning("⚠️ Please provide a valid webhook URL.")
            elif not REQUESTS_AVAILABLE:
                st.error("`requests` package not available.")
            else:
                payload = {"event": "test_ping", "subscribed_events": event_trigger, "sent_at": pd.Timestamp.now().isoformat()}
                try:
                    t0 = time.perf_counter()
                    resp = requests.post(webhook_url, json=payload, timeout=8)
                    latency = (time.perf_counter() - t0) * 1000
                    log_call("Webhook Test", latency, resp.status_code)
                    if resp.status_code < 400:
                        st.success(f"✅ Webhook responded with HTTP {resp.status_code} in {latency:.0f}ms.")
                    else:
                        st.warning(f"⚠️ Webhook responded with HTTP {resp.status_code} in {latency:.0f}ms.")
                    st.code(resp.text[:500] or "(empty response body)", language="text")
                except Exception as e:
                    log_call("Webhook Test", 0, f"error: {type(e).__name__}")
                    st.error(f"🚫 Delivery failed: {e}")

    with tab_telem:
        st.markdown("#### Session Call Log")
        st.caption("Every real API call made in this hub during this session, with its actual measured latency — not simulated data.")
        log = st.session_state.get("integration_call_log", [])
        if not log:
            st.info("ℹ️ No calls logged yet — use the Notion, GitHub, Sheets, or Webhook tools above, or run the Live Endpoint Health check.")
        else:
            log_df = pd.DataFrame(log)
            st.dataframe(log_df, use_container_width=True, hide_index=True)
            if PLOTLY_AVAILABLE and len(log_df) > 1:
                fig = px.line(log_df.reset_index(), x="index", y="Latency (ms)", color="Service", markers=True, template="plotly_dark", height=320)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=20, b=0), xaxis_title="Call Sequence")
                st.plotly_chart(fig, use_container_width=True)
            render_export_buttons(log_df, base_name="session_call_log")
            if st.button("🗑️ Clear Log", key="clear_call_log"):
                st.session_state["integration_call_log"] = []
                st.rerun()


def render_reference_lookup():
    section_header("📚 Reference Lookup (DOI → CrossRef)", "Real bibliographic lookup by DOI via the free CrossRef API. Full Mendeley account sync would need an OAuth login flow not implemented here — this does something real instead of faking that connection.")

    doi_input = st.text_input("DOI", placeholder="10.1038/s41586-021-03819-2", key="doi_lookup_input")

    if st.button("📚 Look Up DOI", type="primary", key="lookup_doi_btn"):
        if not doi_input.strip():
            st.warning("Enter a DOI.")
        elif not REQUESTS_AVAILABLE:
            st.error("`requests` package not available.")
        else:
            try:
                t0 = time.perf_counter()
                resp = requests.get(
                    f"https://api.crossref.org/works/{doi_input.strip()}",
                    timeout=8,
                    headers={"User-Agent": "ChrishemPlatform-IntegrationsHub/1.0 (mailto:research@example.com)"},
                )
                latency = (time.perf_counter() - t0) * 1000
                log_call("CrossRef DOI Lookup", latency, resp.status_code)

                if resp.status_code != 200:
                    st.error(f"🚫 DOI not found or CrossRef returned HTTP {resp.status_code}.")
                else:
                    item = resp.json()["message"]
                    title = (item.get("title") or ["Untitled"])[0]
                    authors = ", ".join(f"{a.get('given','')} {a.get('family','')}" for a in item.get("author", []))
                    journal = (item.get("container-title") or ["—"])[0]
                    st.success("✅ Real record retrieved from CrossRef.")
                    st.markdown(f"**Title:** {title}")
                    st.markdown(f"**Authors:** {authors or 'n/a'}")
                    st.markdown(f"**Journal:** {journal}")
                    st.markdown(f"**DOI:** {item.get('DOI', doi_input)}")
                    st.markdown(f"**Citation Count:** {item.get('is-referenced-by-count', 0)}")
            except Exception as e:
                st.error(f"🚫 Lookup failed: {e}")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()

    setup_page("Integrations Hub", "🔗", initial_sidebar_state="expanded")

    hero_card(
        "🔗 Integrations & External Connectivity Hub — Premium Suite",
        "Real integration platform featuring authenticated Notion queries, public Google Sheet import, real GitHub repository data, real webhook delivery testing, live endpoint health checks, and real DOI lookup via CrossRef.",
        badge_text="INTEGRATIONS HUB • PREMIUM SUITE",
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