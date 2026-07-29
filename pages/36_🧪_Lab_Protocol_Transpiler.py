st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

"""Page 36: Theoretical-to-Practical Protocol Transpiler"""
import streamlit as st
from modules.lab_protocol_transpiler import render_lab_protocol_transpiler_ui

st.set_page_config(page_title="Lab Protocol Transpiler", page_icon="🧪", layout="wide")
render_lab_protocol_transpiler_ui()

