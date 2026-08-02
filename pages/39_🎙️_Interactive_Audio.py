"""Page 39: Hands-Free Interactive Audio Engine"""
import streamlit as st
from modules.interactive_audio_engine import render_interactive_audio_ui

st.set_page_config(page_title="Interactive Audio Engine", page_icon="🎙️", layout="wide")
render_interactive_audio_ui()

