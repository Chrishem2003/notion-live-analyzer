import streamlit as st

st.set_page_config(
    page_title="Enterprise Science & Analytics Suite",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Workspace Landing Dashboard
st.title("🔬 Enterprise Science & Data Analytics Suite")
st.caption("Welcome to your central workspace. Select a module from the sidebar navigation menu to launch a workspace tool.")

st.markdown("---")

# Quick Access Metrics
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("System Engine", "v2.0 Master", "Operational")
with m2:
    st.metric("Active Modules", "50+ Loaded", "Healthy")
with m3:
    st.metric("Local Storage", "Partition Migrated", "Secondary Drive")
with m4:
    st.metric("Zero-Trust Vault", "Encrypted", "AES-256 / Post-Quantum")

st.markdown("---")

st.subheader("🚀 Quick Launch Hub")
col_a, col_b = st.columns(2)

with col_a:
    with st.container(border=True):
        st.markdown("### 📁 File & Sequence Analyzer")
        st.write("Process bio-informatics sequence data, raw streams, and structured files.")
    
    with st.container(border=True):
        st.markdown("### 🏥 Healthcare & Clinical Analytics")
        st.write("Access regional surveillance datasets, pathogen mapping, and clinical telemetry.")

with col_b:
    with st.container(border=True):
        st.markdown("### 🔒 Secure Personal Vault")
        st.write("Access your zero-knowledge encrypted vault, KMS key store, and steganography hub.")
    
    with st.container(border=True):
        st.markdown("### 🤖 AI Insights & Literature Engine")
        st.write("Query vector embeddings, hypothesis models, and research synthesis engines.")

st.info("💡 Tip: Use the left sidebar to navigate directly to any tool or analyzer page.")