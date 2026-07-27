import streamlit as st
from datetime import datetime
import zoneinfo

def render_ui_enhancements():
    # Smart calendar greetings & time-based styling injection
    try:
        eat_zone = zoneinfo.ZoneInfo("Africa/Nairobi")
        current_time = datetime.now(eat_zone)
    except Exception:
        current_time = datetime.now()
        
    hour = current_time.hour
    if 5 <= hour < 12:
        greeting = "Good Morning"
    elif 12 <= hour < 17:
        greeting = "Good Afternoon"
    elif 17 <= hour < 22:
        greeting = "Good Evening"
    else:
        greeting = "Late Night Research Session"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            color: #f8fafc;
        }}
        .metric-card {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 10px;
        }}
        </style>
        <div style="padding: 8px 12px; background: rgba(59, 130, 246, 0.1); border-left: 4px solid #3b82f6; border-radius: 4px; margin-bottom: 15px;">
            <span style="font-weight: 600; color: #60a5fa;">{greeting}, Kula Chris!</span> &nbsp;|&nbsp; <span style="color: #cbd5e1;">Local Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (EAT)</span>
        </div>
        """,
        unsafe_allow_html=True
    )
