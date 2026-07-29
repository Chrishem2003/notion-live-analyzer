st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

"""Page 39: Hands-Free Interactive Audio Engine"""
import streamlit as st
from modules.interactive_audio_engine import render_interactive_audio_ui

st.set_page_config(page_title="Interactive Audio Engine", page_icon="🎙️", layout="wide")
render_interactive_audio_ui()

