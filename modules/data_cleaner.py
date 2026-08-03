import security_guard

import streamlit as st
import pandas as pd
from modules.database import log_backend_event

def render_data_cleaner():
    """
    Renders an interactive dataset cleaning and transformation utility.
    """
    st.subheader(" Automated Dataset Cleaner & Transformer")
    st.caption("Upload raw tabular data to clean null values, normalize columns, and export filtered results.")

    uploaded_file = st.file_uploader("Upload CSV Dataset for Cleaning", type=["csv"], key="cleaner_file_upload")

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("### Original Dataset Preview", df.head())

            st.markdown("### Cleaning Options")
            col1, col2 = st.columns(2)
            
            with col1:
                drop_duplicates = st.checkbox("Remove Duplicate Rows", value=True)
                fill_nulls = st.selectbox("Handle Missing Values", ["None", "Drop Nulls", "Fill with Zero", "Fill with Mean"])

            with col2:
                normalize_cols = st.checkbox("Normalize Column Names (Lowercase & Snake Case)", value=True)

            if st.button("Process Dataset"):
                processed_df = df.copy()

                if normalize_cols:
                    processed_df.columns = [str(col).strip().lower().replace(" ", "_") for col in processed_df.columns]

                if drop_duplicates:
                    processed_df = processed_df.drop_duplicates()

                if fill_nulls == "Drop Nulls":
                    processed_df = processed_df.dropna()
                elif fill_nulls == "Fill with Zero":
                    processed_df = processed_df.fillna(0)
                elif fill_nulls == "Fill with Mean":
                    numeric_cols = processed_df.select_dtypes(include='number').columns
                    processed_df[numeric_cols] = processed_df[numeric_cols].fillna(processed_df[numeric_cols].mean())

                st.success(f"Dataset successfully cleaned! Rows remaining: {len(processed_df)}")
                st.write("### Cleaned Dataset Preview", processed_df.head())

                csv_bytes = processed_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=" Download Cleaned Dataset (CSV)",
                    data=csv_bytes,
                    file_name="cleaned_dataset_export.csv",
                    mime="text/csv"
                )
                log_backend_event("INFO", "Processed and cleaned uploaded dataset successfully.")
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
    else:
        st.info("Awaiting dataset upload. Drop a CSV file above to begin cleaning.")
