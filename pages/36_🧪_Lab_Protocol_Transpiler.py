"""Page 36: Theoretical-to-Practical Protocol Transpiler"""
import streamlit as st
from modules.lab_protocol_transpiler import render_lab_protocol_transpiler_ui

st.set_page_config(page_title="Lab Protocol Transpiler", page_icon="🧪", layout="wide")
render_lab_protocol_transpiler_ui()

