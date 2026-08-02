"""
Automated Feature Engineering Page — Interaction terms, polynomial features, binning, text features.
"""
import streamlit as st

st.set_page_config(page_title="Feature Engineering", page_icon="⚡", layout="wide")

from modules.page_setup import require_dependency
from modules.feature_engineer import render_feature_engineering_ui

require_dependency("sklearn.preprocessing", "⚠️ scikit-learn required. Install with: `pip install scikit-learn`")

render_feature_engineering_ui()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Feature engineering can significantly improve model performance. Start with interaction terms and polynomial features.")
