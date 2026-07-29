st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

"""
Automated Feature Engineering Page — Interaction terms, polynomial features, binning, text features.
"""
import streamlit as st

st.set_page_config(page_title="Feature Engineering", page_icon="⚡", layout="wide")

from modules.feature_engineer import render_feature_engineering_ui

try:
    from sklearn.preprocessing import PolynomialFeatures
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

if not HAS_DEPS:
    st.error("⚠️ scikit-learn required. Install with: `pip install scikit-learn`")
    st.stop()

render_feature_engineering_ui()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Feature engineering can significantly improve model performance. Start with interaction terms and polynomial features.")
