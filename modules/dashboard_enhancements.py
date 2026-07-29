"""
Dashboard Enhancements Module
Provides smart search filters, metric banners, caching helpers, and export suites.
"""
import streamlit as st
import pandas as pd
import json
import time

def render_metric_banner(metrics_dict):
    """Renders a clean executive summary metric banner."""
    cols = st.columns(len(metrics_dict))
    for col, (label, data) in zip(cols, metrics_dict.items()):
        with col:
            val = data.get("value", 0)
            delta = data.get("delta", None)
            st.metric(label=label, value=val, delta=delta)
    st.markdown("---")

def smart_search_filter(df: pd.DataFrame, search_cols=None) -> pd.DataFrame:
    """Provides a global smart search and filter bar for dataframes."""
    if df.empty:
        return df
        
    search_query = st.text_input("🔍 Global Smart Search", "", placeholder="Type to filter across records...")
    if not search_query:
        return df
        
    if search_cols is None:
        search_cols = df.columns.tolist()
        
    # Filter rows where any target column contains the search query (case-insensitive)
    mask = False
    for col in search_cols:
        if col in df.columns:
            mask = mask | df[col].astype(str).str.contains(search_query, case=False, na=False)
            
    filtered_df = df[mask]
    st.caption(f"Showing {len(filtered_df)} of {len(df)} matching records.")
    return filtered_df

def render_export_suite(df: pd.DataFrame, file_prefix: "notion_export"):
    """Provides one-click export options for CSV and JSON formats."""
    if df.empty:
        return
        
    st.subheader("📥 Export Options")
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download as CSV",
            data=csv_data,
            file_name=f"{file_prefix}_{int(time.time())}.csv",
            mime="text/csv"
        )
        
    with col2:
        json_data = df.to_json(orient="records", indent=2)
        st.download_button(
            label="Download as JSON",
            data=json_data,
            file_name=f"{file_prefix}_{int(time.time())}.json",
            mime="application/json"
        )

def cached_notion_fetcher(fetch_func, *args, **kwargs):
    """Wrapper to cache Notion API calls with a manual clear option."""
    @st.cache_data(ttl=600, show_spinner=False)
    def _cached_call(*a, **kw):
        return fetch_func(*a, **kw)
    return _cached_call(*args, **kwargs)
