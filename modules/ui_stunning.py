"""
World-Class Enterprise UI Styling & Typography Engine
Enforces high-contrast, eye-friendly design standards across all Streamlit pages.
"""
import streamlit as st

def apply_stunning_styles():
    """Injects global CSS to fix contrast, eliminate eye strain, and professionalize UI components."""
    st.markdown("""
    <style>
        /* Global Typography & Contrast Enhancements */
        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #1e293b; /* Deep slate for maximum readability on light backgrounds */
        }

        /* Main Container Background */
        .stApp {
            background-color: #f8fafc;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e2e8f0;
        }

        /* High-Contrast Headings */
        h1, h2, h3, h4, h5, h6 {
            color: #0f172a !important;
            font-weight: 700 !important;
            letter-spacing: -0.025em;
        }

        /* Readable Paragraphs & Text */
        p, span, label, .stMarkdown {
            color: #334155 !important;
            font-size: 1rem;
            line-height: 1.6;
        }

        /* Professional Card Containers */
        .stMetric, div[data-testid="stVerticalBlock"] > div[style*="border"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        }

        /* Button Styling */
        .stButton > button {
            background-color: #2563eb;
            color: #ffffff;
            font-weight: 600;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            border: none;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            transition: all 0.2s ease-in-out;
        }
        .stButton > button:hover {
            background-color: #1d4ed8;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        /* Input Fields & Selectboxes */
        .stTextInput input, .stSelectbox select, .stNumberInput input {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
        }

        /* Dataframes & Tables */
        dataframe, table {
            background-color: #ffffff !important;
            color: #1e293b !important;
        }
    </style>
    """, unsafe_allow_html=True)
