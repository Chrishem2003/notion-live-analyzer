"""
World-Class Enterprise UI Styling & Typography Engine (Dark Mode Optimized)
Eliminates eye strain with soft charcoal backgrounds, high-contrast typography, and premium card styling.
"""
import streamlit as st

def apply_stunning_styles():
    """Injects global CSS to enforce a sleek, eye-soothing dark mode across all pages."""
    st.markdown("""
    <style>
        /* Global Typography & Deep Charcoal Background */
        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #f1f5f9 !important; /* Soft bright white for crystal-clear readability */
        }

        /* App Main Background - Deep Slate/Charcoal to stop blinding glare */
        .stApp {
            background-color: #0f172a !important;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #1e293b !important;
            border-right: 1px solid #334155 !important;
        }

        /* High-Contrast Headings */
        h1, h2, h3, h4, h5, h6 {
            color: #ffffff !important;
            font-weight: 700 !important;
            letter-spacing: -0.025em;
        }

        /* Readable Paragraphs & Text */
        p, span, label, .stMarkdown {
            color: #cbd5e1 !important;
            font-size: 1rem;
            line-height: 1.6;
        }

        /* Professional Card Containers */
        .stMetric, div[data-testid="stVerticalBlock"] > div[style*="border"], div.element-container {
            color: #f1f5f9 !important;
        }
        
        div[data-testid="stMetricValue"] {
            color: #38bdf8 !important; /* Vibrant cyan accent for metrics */
        }

        /* Button Styling */
        .stButton > button {
            background-color: #2563eb !important;
            color: #ffffff !important;
            font-weight: 600;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            border: none;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            transition: all 0.2s ease-in-out;
        }
        .stButton > button:hover {
            background-color: #1d4ed8 !important;
            box-shadow: 0 6px 8px -1px rgba(0, 0, 0, 0.3);
        }

        /* Input Fields & Selectboxes */
        .stTextInput input, .stSelectbox select, .stNumberInput input {
            background-color: #1e293b !important;
            color: #ffffff !important;
            border: 1px solid #475569 !important;
            border-radius: 8px !important;
        }

        /* Dataframes & Tables */
        dataframe, table {
            background-color: #1e293b !important;
            color: #f1f5f9 !important;
        }
    </style>
    """, unsafe_allow_html=True)
