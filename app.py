import os
import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Live Notion Analyzer", layout="wide")
st.title("📊 Live Notion Data Analyzer & Visualizer")
st.markdown("This dashboard syncs in real-time with your Notion database.")

# 2. SECURE CONFIGURATION (Reads from Streamlit Secrets)
NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
DATABASE_ID = st.secrets["DATABASE_ID"]

# 3. NOTION DATA FETCHER
def fetch_live_notion_data(token, db_id):
    url = f"https://notion.com{db_id}/query"
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
                st.error(f"Notion API Error: Status {response.status_code} - {response.text}")
                return pd.DataFrame()
                
            data = response.json()
            
            for page in data.get("results", []):
                props = page.get("properties", {})
                
                title_list = props.get("Entity ID", {}).get("title", [])
                entity_id = title_list.get("text", {}).get("content", "Unknown") if title_list else "Unknown"
                
                metric_val = props.get("Metric Value", {}).get("number", 0.0)
                if metric_val is None:
                    metric_val = 0.0
                
                status_obj = props.get("Upload Status", {}).get("select") or props.get("Upload Status", {}).get("status")
                status = status_obj.get("name", "Unknown") if status_obj else "Unknown"
                
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

# 4. REFRESH CONTROLS
col_btn, col_empty = st.columns(2)
with col_btn:
    if st.button("🔄 Sync New Changes"):
        st.cache_data.clear()

df = fetch_live_notion_data(NOTION_TOKEN, DATABASE_ID)

# 5. DASHBOARD LAYOUT
if df.empty:
    st.warning("⚠️ No data parsed yet. Check your Notion field names and API connections.")
else:
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
            template="plotly_white"
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
            hole=0.4,
            template="plotly_white"
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Live Spreadsheet Record View")
    st.dataframe(df, use_container_width=True)
