st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

"""Page 42: Dynamic Hypothesis & Parameter Simulator"""
import streamlit as st
from modules.hypothesis_simulator import render_hypothesis_simulator_ui

st.set_page_config(page_title="Hypothesis Simulator", page_icon="🧮", layout="wide")
render_hypothesis_simulator_ui()

