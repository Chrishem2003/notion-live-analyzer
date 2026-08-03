
"""
Data Simulator  generate synthetic research data with specified parameters.
Useful for teaching, testing, power analysis, and simulations.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
import random


class DataSimulator:
    """Generate synthetic research datasets."""

    @staticmethod
    def simulate_survey_data(
        n_respondents: int = 100,
        n_questions: int = 10,
        scale_type: str = "likert5",
        add_demographics: bool = True,
        seed: int = 42,
    ) -> pd.DataFrame:
        """Simulate survey data with Likert-scale questions and demographics."""
        np.random.seed(seed)
        random.seed(seed)

        data = {}

        # Demographics
        if add_demographics:
            data['ID'] = [f"R{str(i).zfill(4)}" for i in range(1, n_respondents  1)]
            data['Age'] = np.random.normal(35, 12, n_respondents).astype(int).clip(18, 85)
            data['Gender'] = np.random.choice(['Male', 'Female', 'Non-binary', 'Prefer not to say'],
                                               size=n_respondents, p=[0.48, 0.48, 0.03, 0.01])
            data['Education'] = np.random.choice(
                ['High School', 'Associate', 'Bachelor', 'Master', 'Doctorate', 'Other'],
                size=n_respondents, p=[0.20, 0.15, 0.35, 0.20, 0.07, 0.03]
            )
            data['Income_Level'] = np.random.choice(
                ['Low', 'Lower-Middle', 'Middle', 'Upper-Middle', 'High'],
                size=n_respondents, p=[0.15, 0.25, 0.35, 0.18, 0.07]
            )

        # Scale definition
        if scale_type == "likert5":
            scale_values = [1, 2, 3, 4, 5]
            scale_labels = {
                1: 'Strongly Disagree', 2: 'Disagree', 3: 'Neutral',
                4: 'Agree', 5: 'Strongly Agree'
            }
        elif scale_type == "likert7":
            scale_values = list(range(1, 8))
            scale_labels = {
                1: 'Strongly Disagree', 2: 'Disagree', 3: 'Somewhat Disagree',
                4: 'Neutral', 5: 'Somewhat Agree', 6: 'Agree', 7: 'Strongly Agree'
            }
        elif scale_type == "binary":
            scale_values = [0, 1]
            scale_labels = {0: 'No', 1: 'Yes'}
        elif scale_type == "continuous":
            scale_values = None
            scale_labels = {}

        # Generate questions with varied distributions
        question_prefixes = [
            "I am satisfied with", "I find it easy to", "I frequently use",
            "The quality of", "I would recommend", "The importance of",
            "I feel confident about", "The effectiveness of", "I enjoy",
            "The system supports", "I believe that", "The value of",
        ]

        for i in range(n_questions):
            prefix = random.choice(question_prefixes)
            topic = random.choice([
                "the service.", "the product.", "my work.", "my team.",
                "the training.", "the process.", "the tools.", "communication.",
                "support.", "outcomes.", "resources.", "technology."
            ])
            q_name = f"Q{i1}"
            q_label = f"{prefix} {topic}"

            if scale_type == "continuous":
                # Normal distribution with slight skew
                base = np.random.normal(50, 15, n_respondents)
                # Add item-specific effect
                effect = np.random.normal(0, 5)
                data[q_name] = np.round(base  effect, 1).clip(0, 100)
            else:
                # Add correlation structure (first item correlates with demographics)
                if i == 0 and add_demographics:
                    prob = 0.3  (data['Age'] - 18) / (85 - 18) * 0.4
                    data[q_name] = np.array([
                        np.random.choice(scale_values, p=_likert_probs(prob_val, scale_values))
                        for prob_val in prob
                    ])
                else:
                    probs = np.random.dirichlet(np.ones(len(scale_values)) * 2)
                    data[q_name] = np.random.choice(scale_values, size=n_respondents, p=probs)

        df = pd.DataFrame(data)

        # Add metadata
        st.session_state["simulation_metadata"] = {
            "type": "survey",
            "n": n_respondents,
            "questions": n_questions,
            "scale": scale_type,
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        return df

    @staticmethod
    def simulate_experimental_data(
        n_per_group: int = 30,
        n_groups: int = 3,
        effect_size: float = 0.5,
        has_pre_post: bool = True,
        add_covariate: bool = True,
        seed: int = 42,
    ) -> pd.DataFrame:
        """Simulate experimental data with groups, pre/post measures, and covariates."""
        np.random.seed(seed)
        random.seed(seed)

        rows = []
        group_names = ['Control', 'Treatment A', 'Treatment B', 'Treatment C', 'Treatment D'][:n_groups]

        for group_idx, group_name in enumerate(group_names):
            for i in range(n_per_group):
                subject_id = f"S{group_name[0]}{str(i1).zfill(3)}"

                # Pre-test (baseline)
                pre_test = np.random.normal(50, 10)

                # Treatment effect
                if group_name == 'Control':
                    effect = 0
                else:
                    effect = effect_size * 10 * (1  0.1 * group_idx)

                # Post-test with effect
                post_test = pre_test  effect  np.random.normal(0, 5)

                # Covariate (e.g., age, baseline measure)
                covariate = np.random.normal(0, 1) if add_covariate else None

                row = {
                    'Subject_ID': subject_id,
                    'Group': group_name,
                    'Group_Code': group_idx,
                    'Pre_Test': round(pre_test, 1),
                    'Post_Test': round(post_test, 1),
                    'Change_Score': round(post_test - pre_test, 1),
                }

                if add_covariate:
                    row['Covariate'] = round(covariate, 2) if covariate is not None else 0

                rows.append(row)

        df = pd.DataFrame(rows)

        st.session_state["simulation_metadata"] = {
            "type": "experimental",
            "n_per_group": n_per_group,
            "n_groups": n_groups,
            "effect_size": effect_size,
            "has_pre_post": has_pre_post,
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        return df

    @staticmethod
    def simulate_correlational_data(
        n_observations: int = 100,
        n_variables: int = 5,
        correlation_strength: float = 0.3,
        add_noise: bool = True,
        seed: int = 42,
    ) -> pd.DataFrame:
        """Simulate correlational data with specified correlation structure."""
        np.random.seed(seed)

        # Create correlation matrix
        corr_matrix = np.eye(n_variables)
        for i in range(n_variables):
            for j in range(i  1, n_variables):
                if random.random() < 0.4:  # 40% chance of correlation
                    corr_matrix[i, j] = correlation_strength  random.uniform(-0.2, 0.2)
                    corr_matrix[j, i] = corr_matrix[i, j]
                    corr_matrix[i, j] = np.clip(corr_matrix[i, j], -0.9, 0.9)
                    corr_matrix[j, i] = corr_matrix[i, j]

        # Ensure positive definite
        eigvals = np.linalg.eigvals(corr_matrix)
        if np.min(eigvals) <= 0:
            corr_matrix = np.eye(n_variables) * 0.1

        # Generate multivariate normal data
        mean = np.zeros(n_variables)
        data = np.random.multivariate_normal(mean, corr_matrix, size=n_observations)

        # Add noise
        if add_noise:
            noise = np.random.normal(0, 0.5, data.shape)
            data = data  noise

        # Convert to DataFrame
        var_names = [f"Var_{i1}" for i in range(n_variables)]
        df = pd.DataFrame(data, columns=var_names)
        df = df.round(2)

        st.session_state["simulation_metadata"] = {
            "type": "correlational",
            "n": n_observations,
            "variables": n_variables,
            "correlation_strength": correlation_strength,
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        return df

    @staticmethod
    def simulate_time_series_data(
        n_periods: int = 100,
        trend: float = 0.1,
        seasonality: bool = True,
        seasonality_period: int = 12,
        noise_level: float = 1.0,
        start_date: str = "2023-01-01",
        freq: str = "D",
        seed: int = 42,
    ) -> pd.DataFrame:
        """Simulate time series data with trend, seasonality, and noise."""
        np.random.seed(seed)

        dates = pd.date_range(start=start_date, periods=n_periods, freq=freq)
        t = np.arange(n_periods)

        # Trend component
        trend_component = trend * t

        # Seasonality component
        if seasonality:
            season_component = 5 * np.sin(2 * np.pi * t / seasonality_period)
            season_component = 2 * np.sin(4 * np.pi * t / seasonality_period)
        else:
            season_component = 0

        # Noise component
        noise = np.random.normal(0, noise_level, n_periods)

        # Combined
        values = 50  trend_component  season_component  noise
        # Cumulative sum for non-stationary feel
        values = np.cumsum(values - values.mean()) / 10  100

        # Additional variables
        predictor1 = 0.5 * values  np.random.normal(0, 2, n_periods)
        predictor2 = 0.3 * values  np.random.normal(0, 3, n_periods)  0.1 * t

        df = pd.DataFrame({
            'Date': dates,
            'Value': round(values, 2),
            'Predictor_1': round(predictor1, 2),
            'Predictor_2': round(predictor2, 2),
            'Trend': round(trend_component, 2),
            'Seasonality': round(season_component, 2) if seasonality else 0,
        })

        st.session_state["simulation_metadata"] = {
            "type": "time_series",
            "n": n_periods,
            "trend": trend,
            "seasonality": seasonality,
            "freq": freq,
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        return df

    @staticmethod
    def simulate_longitudinal_data(
        n_subjects: int = 50,
        n_timepoints: int = 4,
        effect_size: float = 0.5,
        n_groups: int = 2,
        seed: int = 42,
    ) -> pd.DataFrame:
        """Simulate longitudinal/repeated measures data."""
        np.random.seed(seed)
        random.seed(seed)

        rows = []
        group_names = ['Control', 'Treatment'][:n_groups]

        for subj in range(1, n_subjects  1):
            group = group_names[subj % n_groups]
            base_score = np.random.normal(50, 10)

            for tp in range(1, n_timepoints  1):
                time_effect = tp * 2  # Natural increase over time

                if group == 'Treatment':
                    treatment_effect = effect_size * 10 * tp / n_timepoints
                else:
                    treatment_effect = 0

                score = base_score  time_effect  treatment_effect  np.random.normal(0, 5)

                rows.append({
                    'Subject_ID': f"S{str(subj).zfill(3)}",
                    'Time': tp,
                    'Group': group,
                    'Score': round(score, 1),
                })

        df = pd.DataFrame(rows)

        st.session_state["simulation_metadata"] = {
            "type": "longitudinal",
            "n_subjects": n_subjects,
            "n_timepoints": n_timepoints,
            "effect_size": effect_size,
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        return df


# â”€â”€â”€ Helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _likert_probs(base_prob: float, scale_values: List[int]) -> List[float]:
    """Generate skewed Likert probabilities based on base probability."""
    n = len(scale_values)
    probs = np.ones(n) * (1 - base_prob) / (n - 1)
    probs[0] = base_prob
    for i in range(1, n - 1):
        if i == n // 2:
            probs[i] = probs[i] * 0.5  base_prob * 0.3
    probs = probs / probs.sum()
    return probs.tolist()


# â”€â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def render_data_simulator_ui() -> pd.DataFrame:
    """Render the data simulator UI."""
    st.markdown("## ðŸŽ² Data Simulator")
    st.markdown("*Generate synthetic research datasets for teaching, testing, and simulation*")

    sim_type = st.radio(
        "Select data type to simulate",
        options=["Survey Data", "Experimental Data", "Correlational Data",
                 "Time Series Data", "Longitudinal Data"],
        horizontal=True,
        key="sim_type"
    )

    result_df = None

    if sim_type == "Survey Data":
        st.subheader("ðŸ“‹ Survey Data Simulation")

        col1, col2 = st.columns(2)
        with col1:
            n_resp = st.number_input("Number of respondents", min_value=10, max_value=10000, value=100, step=10, key="sim_survey_n")
            n_qs = st.number_input("Number of questions", min_value=1, max_value=50, value=10, step=1, key="sim_survey_q")
        with col2:
            scale = st.selectbox("Scale type", options=["likert5", "likert7", "binary", "continuous"],
                                 format_func=lambda x: {"likert5": "Likert 5-point", "likert7": "Likert 7-point",
                                                        "binary": "Binary (Yes/No)", "continuous": "Continuous 0-100"}[x],
                                 key="sim_survey_scale")
            add_demo = st.checkbox("Include demographics", value=True, key="sim_survey_demo")

        if st.button("ðŸŽ² Generate Survey Data", type="primary"):
            with st.spinner(f"Generating {n_resp} survey responses..."):
                result_df = DataSimulator.simulate_survey_data(
                    int(n_resp), int(n_qs), scale, add_demo
                )
            st.success(f"âœ… Generated {len(result_df)} rows Ã— {len(result_df.columns)} columns")

    elif sim_type == "Experimental Data":
        st.subheader("ðŸ§ª Experimental Data Simulation")

        col1, col2 = st.columns(2)
        with col1:
            n_group = st.number_input("Subjects per group", min_value=5, max_value=500, value=30, step=5, key="sim_exp_n")
            n_groups = st.number_input("Number of groups", min_value=2, max_value=5, value=2, step=1, key="sim_exp_groups")
        with col2:
            effect = st.slider("Effect size (Cohen's d)", 0.0, 2.0, 0.5, 0.1, key="sim_exp_effect")
            add_cov = st.checkbox("Include covariate", value=True, key="sim_exp_cov")

        if st.button("ðŸŽ² Generate Experimental Data", type="primary"):
            with st.spinner("Generating experimental data..."):
                result_df = DataSimulator.simulate_experimental_data(
                    int(n_group), int(n_groups), effect, add_covariate=add_cov
                )
            st.success(f"âœ… Generated {len(result_df)} rows Ã— {len(result_df.columns)} columns")

    elif sim_type == "Correlational Data":
        st.subheader("ðŸ”— Correlational Data Simulation")

        col1, col2 = st.columns(2)
        with col1:
            n_obs = st.number_input("Number of observations", min_value=10, max_value=5000, value=100, step=10, key="sim_corr_n")
            n_vars = st.number_input("Number of variables", min_value=2, max_value=20, value=5, step=1, key="sim_corr_vars")
        with col2:
            corr_strength = st.slider("Average correlation strength", 0.0, 0.9, 0.3, 0.05, key="sim_corr_r")
            add_noise = st.checkbox("Add noise", value=True, key="sim_corr_noise")

        if st.button("ðŸŽ² Generate Correlational Data", type="primary"):
            with st.spinner("Generating correlated variables..."):
                result_df = DataSimulator.simulate_correlational_data(
                    int(n_obs), int(n_vars), corr_strength, add_noise
                )
            st.success(f"âœ… Generated {len(result_df)} rows Ã— {len(result_df.columns)} columns")

            # Show correlation matrix
            st.subheader(" Correlation Matrix")
            corr = result_df.corr().round(3)
            import plotly.express as px
            fig = px.imshow(corr, text_auto=True, aspect='auto',
                           color_continuous_scale='RdBu_r', zmin=-1, zmax=1,
                           title="Simulated Correlation Matrix")
            st.plotly_chart(fig, use_container_width=True)

    elif sim_type == "Time Series Data":
        st.subheader("ðŸ“ˆ Time Series Data Simulation")

        col1, col2 = st.columns(2)
        with col1:
            n_periods = st.number_input("Number of time periods", min_value=10, max_value=1000, value=100, step=10, key="sim_ts_n")
            trend_val = st.slider("Trend strength", 0.0, 1.0, 0.1, 0.05, key="sim_ts_trend")
        with col2:
            use_season = st.checkbox("Add seasonality", value=True, key="sim_ts_season")
            noise_lvl = st.slider("Noise level", 0.1, 5.0, 1.0, 0.1, key="sim_ts_noise")

        if st.button("ðŸŽ² Generate Time Series Data", type="primary"):
            with st.spinner("Generating time series..."):
                result_df = DataSimulator.simulate_time_series_data(
                    int(n_periods), trend=trend_val, seasonality=use_season, noise_level=noise_lvl
                )
            st.success(f"âœ… Generated {len(result_df)} rows Ã— {len(result_df.columns)} columns")

    elif sim_type == "Longitudinal Data":
        st.subheader(" Longitudinal Data Simulation")

        col1, col2 = st.columns(2)
        with col1:
            n_subj = st.number_input("Number of subjects", min_value=10, max_value=500, value=50, step=5, key="sim_long_n")
            n_tp = st.number_input("Time points", min_value=2, max_value=10, value=4, step=1, key="sim_long_tp")
        with col2:
            effect_long = st.slider("Treatment effect size", 0.0, 2.0, 0.5, 0.1, key="sim_long_effect")
            n_grp = st.number_input("Number of groups", min_value=1, max_value=3, value=2, step=1, key="sim_long_groups")

        if st.button("ðŸŽ² Generate Longitudinal Data", type="primary"):
            with st.spinner("Generating longitudinal data..."):
                result_df = DataSimulator.simulate_longitudinal_data(
                    int(n_subj), int(n_tp), effect_long, int(n_grp)
                )
            st.success(f"âœ… Generated {len(result_df)} rows Ã— {len(result_df.columns)} columns")

    # Display result if generated
    if result_df is not None and not result_df.empty:
        st.subheader("ðŸ“‹ Preview")
        st.dataframe(result_df.head(20), use_container_width=True, hide_index=True)

        # Info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rows", len(result_df))
        with col2:
            st.metric("Columns", len(result_df.columns))
        with col3:
            st.metric("Memory", f"{result_df.memory_usage(deep=True).sum() / 1024:.1f} KB")

        # Export
        st.subheader("ðŸ“¥ Use or Export")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(" Use for Analysis", type="primary", use_container_width=True):
                st.session_state["active_df"] = result_df
                st.session_state["data_source"] = "simulated"
                st.success("âœ… Data loaded into active dataset! Go to other pages to analyze.")
        with col2:
            csv = result_df.to_csv(index=False).encode('utf-8')
            import base64
            b64 = base64.b64encode(csv).decode()
            st.markdown(f'<a href="data:text/csv;base64,{b64}" download="simulated_data.csv">ðŸ“¥ Download CSV</a>',
                       unsafe_allow_html=True)

        # Simulation metadata
        metadata = st.session_state.get("simulation_metadata", {})
        if metadata:
            with st.expander("ðŸ“‹ Simulation Parameters"):
                for k, v in metadata.items():
                    st.markdown(f"**{k.replace('_', ' ').title()}**: {v}")

    return result_df or pd.DataFrame()

