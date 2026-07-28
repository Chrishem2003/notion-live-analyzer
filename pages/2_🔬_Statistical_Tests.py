import streamlit as st
import pandas as pd
from scipy import stats

def render_normality_test_section(df: pd.DataFrame):
    """
    Renders the normality test section, computes descriptive and test statistics,
    and displays the comparison data frame cleanly without syntax errors.
    """
    st.subheader("Normality Test & Statistical Diagnostics")
    
    # Select numeric columns for the test
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    
    if not numeric_cols:
        st.warning("No numeric columns available in the dataset for normality testing.")
        return

    selected_col = st.selectbox("Select Column for Normality Analysis", numeric_cols, key="normality_col_select")
    
    if st.button("Run Shapiro-Wilk Test", key="run_normality_btn"):
        clean_data = df[selected_col].dropna()
        
        if len(clean_data) < 3:
            st.error("Insufficient data points (minimum 3 required) to execute the Shapiro-Wilk test.")
        else:
            stat, p_value = stats.shapiro(clean_data)
            
            # Constructing comparison DataFrame
            comp_data = {
                "Metric": ["Test Statistic", "P-Value", "Sample Size", "Distribution Shape"],
                "Value": [
                    f"{stat:.4f}",
                    f"{p_value:.4e}",
                    len(clean_data),
                    "Normal (Gaussian)" if p_value > 0.05 else "Non-Normal"
                ]
            }
            comp_df = pd.DataFrame(comp_data)
            
            st.write(f"### Results for: `{selected_col}`")
            st.dataframe(comp_df, use_container_width=True, hide_index=True)
            
            if p_value > 0.05:
                st.success("Conclusion: Fail to reject the null hypothesis. The data looks approximately normally distributed.")
            else:
                st.info("Conclusion: Reject the null hypothesis. The data deviates significantly from a normal distribution.")

# Example implementation usage within an app structure:
if __name__ == "__main__":
    st.title("Data Intelligence Engine")
    
    # Dummy data generation for testing standalone execution
    import numpy as np
    np.random.seed(42)
    sample_data = pd.DataFrame({
        "Feature_A": np.random.normal(loc=0, scale=1, size=100),
        "Feature_B": np.random.exponential(scale=2, size=100)
    })
    
    render_normality_test_section(sample_data)