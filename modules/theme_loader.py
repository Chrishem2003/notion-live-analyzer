import streamlit as st

def apply_custom_theme():
    """
    Injects custom neon-glassmorphism CSS styling across the workspace.
    """
    st.markdown(
        """
        <style>
            /* Global Background & Typography */
            .stApp {
                background: linear-gradient(135deg, #0B0F19 0%, #131C2E 100%);
                color: #E2E8F0;
            }
            
            /* Sidebar Styling */
            [data-testid="stSidebar"] {
                background-color: #0E1626;
                border-right: 1px solid rgba(0, 255, 102, 0.2);
            }
            
            /* Card & Container Polish */
            div.stMarkdown container, div.stForm {
                background: rgba(19, 28, 46, 0.7);
                border: 1px solid rgba(0, 255, 102, 0.15);
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            }

            /* Custom Buttons */
            .stButton > button {
                background: linear-gradient(135deg, #00FF66 0%, #00CC52 100%);
                color: #0B0F19;
                font-weight: 700;
                border: none;
                border-radius: 8px;
                padding: 0.6rem 1.2rem;
                box-shadow: 0 4px 14px rgba(0, 255, 102, 0.4);
                transition: all 0.3s ease;
            }
            .stButton > button:hover {
                background: linear-gradient(135deg, #1aff75 0%, #00ff66 100%);
                box-shadow: 0 6px 20px rgba(0, 255, 102, 0.6);
                transform: translateY(-2px);
            }

            /* Metrics */
            [data-testid="stMetricValue"] {
                color: #00FF66 !important;
                font-weight: 800;
            }

            /* Tables */
            [data-testid="stDataFrame"] {
                border: 1px solid rgba(0, 255, 102, 0.2);
                border-radius: 8px;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
