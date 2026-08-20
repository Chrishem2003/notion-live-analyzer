import streamlit as st
import pandas as pd
import numpy as np

def init_session_state():
    if "df" not in st.session_state:
        st.session_state.df = None
    if "dataset_name" not in st.session_state:
        st.session_state.dataset_name = "None"

def get_active_dataframe():
    init_session_state()
    return st.session_state.df

def set_active_dataframe(df, name="Custom Dataset"):
    init_session_state()
    st.session_state.df = df
    st.session_state.dataset_name = name

def dataset_summary():
    df = get_active_dataframe()
    if df is not None:
        return {"rows": df.shape[0], "cols": df.shape[1], "name": st.session_state.dataset_name}
    return {"rows": 0, "cols": 0, "name": "No Dataset Loaded"}

def generate_sample_dataset():
    np.random.seed(42)
    data = {
        "ID": range(1, 101),
        "Category": np.random.choice(["Alpha", "Beta", "Gamma"], 100),
        "Value": np.random.randn(100).round(2),
        "Score": np.random.randint(50, 100, 100)
    }
    df = pd.DataFrame(data)
    set_active_dataframe(df, "Sample Dataset")
    return df
