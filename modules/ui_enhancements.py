import streamlit as st
from datetime import datetime
import zoneinfo

def render_ui_enhancements():
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
        """
        <style>
        /* Import Inter & Outfit Typography */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700&display=swap');

        /* Global Theme & Luxurious Palette */
        .stApp {
            background: radial-gradient(circle at 10% 20%, #090d16 0%, #030712 90%);
            color: #f3f4f6;
            font-family: 'Inter', sans-serif;
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: 'Outfit', sans-serif !important;
            letter-spacing: -0.025em;
        }

        /* Glassmorphism Containers */
        div.stMarkdownContainer, .element-container, div[data-testid="stVerticalBlock"] > div {
            backdrop-filter: blur(12px);
        }

        /* Top-notch Sidebar Stylings */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b1329 0%, #030712 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        /* Metrics & Cards Styling */
        div[data-testid="stMetric"] {
            background: rgba(17, 24, 39, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.08);
            padding: 18px;
            border-radius: 14px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
        }
        div[data-testid="stMetric"]:hover {
            border-color: rgba(59, 130, 246, 0.4);
            box-shadow: 0 10px 30px -5px rgba(59, 130, 246, 0.15);
        }

        /* Custom Buttons */
        .stButton > button {
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            color: #ffffff;
            border: none;
            font-weight: 600;
            padding: 0.6rem 1.2rem;
            border-radius: 10px;
            box-shadow: 0 4px 14px rgba(59, 130, 246, 0.35);
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5);
        }

        /* Tabs Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: rgba(15, 23, 42, 0.6);
            padding: 6px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }
        .stTabs [data-baseweb="tab"] {
            height: 40px;
            border-radius: 8px;
            color: #94a3b8;
            font-weight: 500;
            border: none !important;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 18px; background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%); border: 1px solid rgba(59, 130, 246, 0.2); border-left: 5px solid #3b82f6; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 8px 20px rgba(0,0,0,0.2);">
            <div>
                <span style="font-family: 'Outfit', sans-serif; font-weight: 700; font-size: 1.05rem; color: #60a5fa;">{greeting}, Kula Chris</span>
                <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 2px;">Autonomous Research Intelligence Suite Active</div>
            </div>
            <div style="text-align: right; font-family: monospace; font-size: 0.85rem; color: #cbd5e1; background: rgba(0,0,0,0.3); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);">
                {current_time.strftime('%Y-%m-%d %H:%M:%S')} EAT
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
