import streamlit as st

def apply_custom_theme():
    """
    Injects custom neon-glassmorphism CSS styling with aggressive overrides
    to prevent white-on-white text and ensure maximum clarity.
    """
    st.markdown(
        """
        <style>
            /* Force Global Background & Typography */
            .stApp, .main {
                background-color: #0B0F19 !important;
                background-image: linear-gradient(135deg, #0B0F19 0%, #131C2E 100%) !important;
                color: #E2E8F0 !important;
            }
            
            /* Sidebar Styling */
            [data-testid="stSidebar"] {
                background-color: #0E1626 !important;
                border-right: 1px solid rgba(0, 255, 102, 0.2) !important;
            }
            
            /* Fix Text Inputs, Text Areas, and Number Inputs */
            .stTextInput div[data-baseweb="input"], 
            .stTextArea div[data-baseweb="textarea"],
            .stNumberInput div[data-baseweb="input"] {
                background-color: #1A2639 !important;
                border: 1px solid rgba(0, 255, 102, 0.4) !important;
                border-radius: 6px !important;
            }
            .stTextInput input, .stTextArea textarea, .stNumberInput input {
                color: #FFFFFF !important;
                background-color: transparent !important;
            }

            /* Fix Selectboxes (Dropdowns) */
            .stSelectbox div[data-baseweb="select"] {
                background-color: #1A2639 !important;
                color: #FFFFFF !important;
                border: 1px solid rgba(0, 255, 102, 0.4) !important;
            }
            
            /* Fix DataFrames and Tables */
            [data-testid="stDataFrame"] {
                background-color: #131C2E !important;
                border: 1px solid rgba(0, 255, 102, 0.2);
            }
            .stDataFrame th, .stDataFrame td {
                color: #E2E8F0 !important;
                background-color: #131C2E !important;
            }

            /* Card & Container Polish */
            div.stMarkdown container, div.stForm {
                background: rgba(19, 28, 46, 0.8) !important;
                border: 1px solid rgba(0, 255, 102, 0.2) !important;
                border-radius: 12px !important;
                padding: 1.5rem !important;
            }

            /* Custom Buttons */
            .stButton > button {
                background: linear-gradient(135deg, #00FF66 0%, #00CC52 100%) !important;
                color: #0B0F19 !important;
                font-weight: 700 !important;
                border: none !important;
                border-radius: 8px !important;
            }
            .stButton > button:hover {
                background: linear-gradient(135deg, #1aff75 0%, #00ff66 100%) !important;
                transform: translateY(-2px);
            }

            /* Metrics Text Visibility */
            [data-testid="stMetricValue"] {
                color: #00FF66 !important;
                font-weight: 800 !important;
            }
            [data-testid="stMetricLabel"] {
                color: #A0AEC0 !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
