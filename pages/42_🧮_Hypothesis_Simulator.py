"""Page 42: Dynamic Hypothesis & Parameter Simulator"""
import streamlit as st
from modules.hypothesis_simulator import render_hypothesis_simulator_ui

st.set_page_config(page_title="Hypothesis Simulator", page_icon="🧮", layout="wide")
render_hypothesis_simulator_ui()

