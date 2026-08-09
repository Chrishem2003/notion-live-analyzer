def inject_global_dropdown_fix():
    import streamlit as st
    st.markdown("""
        <style>
            /* 1. Main select box container */
            div[data-baseweb="select"] > div {
                background-color: #1e293b !important;
                color: #f8fafc !important;
            }
            
            /* 2. Floating popover menu container (Fixes white/invisible options box) */
            div[data-baseweb="popover"], div[data-baseweb="menu"], ul[data-baseweb="menu"] {
                background-color: #1e293b !important;
                border: 1px solid #334155 !important;
            }

            /* 3. Individual options inside the dropdown list */
            div[data-baseweb="option"], li[data-baseweb="option"] {
                background-color: #1e293b !important;
                color: #f8fafc !important;
            }

            /* 4. Hover state for dropdown options */
            div[data-baseweb="option"]:hover, li[data-baseweb="option"]:hover {
                background-color: #334155 !important;
                color: #ffffff !important;
            }

            /* 5. Selected option highlight */
            div[data-baseweb="option"][aria-selected="true"], li[data-baseweb="option"][aria-selected="true"] {
                background-color: #0f172a !important;
                color: #38bdf8 !important;
            }
            
            /* 6. Multi-select tags if used */
            span[data-baseweb="tag"] {
                background-color: #334155 !important;
                color: #f8fafc !important;
            }
        </style>
    """, unsafe_allow_html=True)