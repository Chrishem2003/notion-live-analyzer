
"""
World-Class Enterprise UI Styling & Typography Engine (Deep Component Dark Mode)
Forces crystal-clear contrast across all Streamlit pages, widgets, tables, and text blocks.
"""
import streamlit as st

def apply_stunning_styles():
    """Injects universal CSS overrides to guarantee absolute text clarity on every page."""
    st.markdown("""
    <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #262B33 !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #EDEFF2 !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #EDEFF2 !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #262B33 !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #b5790e !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #4fb8a6 !important;
        font-weight: 700 !important;
    }
        /* 1. Global App Background & Text */
        .stApp, [data-testid="stViewToolbar"], header {
            background-color: #0b0f19 !important;
            color: #EDEFF2 !important;
        }

        /* 2. Sidebar Complete Dark Overhaul */
        [data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
            background-color: #171B23 !important;
            color: #EDEFF2 !important;
            border-right: 1px solid #1f2937 !important;
        }
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stMarkdown {
            color: #e2e8f0 !important;
        }

        /* 3. Universal Headings & Paragraphs */
        h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: #ffffff !important;
        }
        p, span, label, div, .stMarkdown, .stText {
            color: #A8B0BC !important;
        }

        /* 4. Streamlit Cards, Containers & Metrics */
        div[data-testid="stVerticalBlock"] > div, div.element-container {
            color: #EDEFF2 !important;
        }
        .stMetric {
            background-color: #171B23 !important;
            border: 1px solid #1f2937 !important;
            padding: 1rem;
            border-radius: 10px;
        }
        div[data-testid="stMetricValue"] {
            color: #4fb8a6 !important;
        }
        div[data-testid="stMetricLabel"] {
            color: #6B7280 !important;
        }

        /* 5. Input Fields, Selectboxes & Text Inputs */
        .stTextInput input, .stSelectbox select, .stNumberInput input, textarea {
            background-color: #1f2937 !important;
            color: #ffffff !important;
            border: 1px solid #374151 !important;
            border-radius: 8px !important;
        }
        .stSelectbox div[data-baseweb="select"] {
            background-color: #1f2937 !important;
            color: #ffffff !important;
        }

        /* 6. Tables & DataFrames */
        dataframe, table, [data-testid="stTable"] {
            background-color: #171B23 !important;
            color: #EDEFF2 !important;
        }
        thead tr th {
            background-color: #1f2937 !important;
            color: #ffffff !important;
        }
        tbody tr td {
            background-color: #171B23 !important;
            color: #e2e8f0 !important;
        }

        /* 7. Tabs & Sub-Navigation Headers */
        .stTabs [data-baseweb="tab-list"] {
            background-color: #0b0f19 !important;
        }
        .stTabs [data-baseweb="tab"] {
            color: #6B7280 !important;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            color: #4fb8a6 !important;
            border-bottom-color: #4fb8a6 !important;
        }
    </style>
    """, unsafe_allow_html=True)

