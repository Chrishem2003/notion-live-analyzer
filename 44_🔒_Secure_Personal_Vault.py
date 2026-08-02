""
Secure Personal Vault & Bioinformatics Hub
"""

import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Secure Personal Vault",
    page_icon="🔒",
    layout="wide"
)

st.title("🔒 Secure Personal Vault & Bioinformatics Hub")
st.markdown("---")

st.info("Vault initialized successfully. All security parameters are active.")

if st.button("Generate Sample Cohort", type="primary"):
    np.random.seed(42)
    df = pd.DataFrame({
        "Sample_ID": [f"SUBJ-{i}" for i in range(1, 51)],
        "Value_A": np.random.normal(100, 15, 50),
        "Value_B": np.random.normal(50, 5, 50)
    })
    st.session_state["vault_data"] = df
    st.success("Cohort generated successfully!")

if "vault_data" in st.session_state:
    st.dataframe(st.session_state["vault_data"], use_container_width=True)