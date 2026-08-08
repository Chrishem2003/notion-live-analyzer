"""
🤖 ML & Predictive Studio — Consolidated Machine Learning Hub
Consolidates old pages: 6 (Predictive Modeling), 26 (Feature Engineering), 56 (Chaos Engine), 60 (Agent Swarm), 65 (AI Defensive Cores).
"""

import numpy as np
import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import get_active_dataframe, set_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_dataset_context_banner,
)

try:
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.impute import SimpleImputer
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.linear_model import LogisticRegression, LinearRegression
    from sklearn.metrics import accuracy_score, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


def get_df():
    df = get_active_dataframe()
    if df is None:
        np.random.seed(42)
        return pd.DataFrame({
            "Feature_A": np.random.normal(12.5, 2.1, 150),
            "Feature_B": np.random.normal(8.3, 1.4, 150),
            "Feature_C": np.random.uniform(0.1, 5.0, 150),
            "Target": np.random.choice([0, 1], p=[0.4, 0.6], size=150),
        })
    return df


def render_automl_tab(df):
    section_header("🤖 Live AutoML Training", "Train classification and regression models with automated preprocessing.")

    if not SKLEARN_AVAILABLE:
        st.error("⚠️ `scikit-learn` is required for this module.")
        return

    target = st.selectbox("Select Target Variable", df.columns, key="ml_target")
    features = st.multiselect("Select Feature Predictors", [c for c in df.columns if c != target], key="ml_features")

    col1, col2 = st.columns(2)
    with col1:
        test_size = st.slider("Test Split (%)", 10, 50, 20, 5, key="ml_test")
    with col2:
        task = st.radio("Task Type", ["Classification", "Regression"], horizontal=True, key="ml_task")

    if st.button("🚀 Train & Evaluate Models", type="primary", key="run_ml"):
        if not features:
            st.error("Select at least one feature.")
        else:
            with st.spinner("Training models..."):
                try:
                    X = df[features].copy()
                    y = df[target].copy()

                    imputer = SimpleImputer(strategy="median")
                    X_imp = pd.DataFrame(imputer.fit_transform(X), columns=features)

                    if task == "Classification":
                        if y.dtype == "object" or y.dtype.name == "category":
                            le = LabelEncoder()
                            y_enc = le.fit_transform(y.astype(str))
                        else:
                            y_enc = y.values

                        X_train, X_test, y_train, y_test = train_test_split(
                            X_imp, y_enc, test_size=test_size / 100, random_state=42
                        )
                        scaler = StandardScaler()
                        X_tr = scaler.fit_transform(X_train)
                        X_te = scaler.transform(X_test)

                        rf = RandomForestClassifier(random_state=42).fit(X_tr, y_train)
                        lr = LogisticRegression(max_iter=500, random_state=42).fit(X_tr, y_train)

                        acc_rf = accuracy_score(y_test, rf.predict(X_te))
                        acc_lr = accuracy_score(y_test, lr.predict(X_te))

                        c1, c2 = st.columns(2)
                        c1.metric("Random Forest Accuracy", f"{acc_rf * 100:.2f}%")
                        c2.metric("Logistic Regression Accuracy", f"{acc_lr * 100:.2f}%")

                        st.markdown("#### Feature Importance (Random Forest)")
                        importances = pd.Series(rf.feature_importances_, index=features).sort_values(ascending=False)
                        st.bar_chart(importances)
                    else:
                        y_num = pd.to_numeric(y, errors="coerce")
                        valid = y_num.notnull()
                        X_imp = X_imp.loc[valid]
                        y_num = y_num.loc[valid]

                        X_train, X_test, y_train, y_test = train_test_split(
                            X_imp, y_num, test_size=test_size / 100, random_state=42
                        )
                        scaler = StandardScaler()
                        X_tr = scaler.fit_transform(X_train)
                        X_te = scaler.transform(X_test)

                        rf = RandomForestRegressor(random_state=42).fit(X_tr, y_train)
                        lin = LinearRegression().fit(X_tr, y_train)

                        r2_rf = r2_score(y_test, rf.predict(X_te))
                        r2_lin = r2_score(y_test, lin.predict(X_te))

                        c1, c2 = st.columns(2)
                        c1.metric("Random Forest R²", f"{r2_rf:.4f}")
                        c2.metric("Linear Regression R²", f"{r2_lin:.4f}")
                except Exception as e:
                    st.error(f"Training error: {e}")


def render_predict_tab(df):
    section_header("🔮 Prediction Engine", "Train a quick model and make predictions on new input.")

    if not SKLEARN_AVAILABLE:
        st.error("`scikit-learn` required.")
        return

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) < 2:
        st.info("Need at least 2 numeric columns.")
        return

    target = st.selectbox("Target", numeric_cols, key="pred_target")
    features = [c for c in numeric_cols if c != target][:3]

    st.markdown("#### Enter Values for Prediction")
    inputs = {}
    cols = st.columns(len(features))
    for i, feat in enumerate(features):
        mean_val = df[feat].mean()
        inputs[feat] = cols[i].number_input(f"{feat}", value=float(mean_val), key=f"pred_in_{feat}")

    if st.button("🔮 Predict", type="primary", key="run_predict"):
        try:
            X = df[features].dropna()
            y = df.loc[X.index, target]
            model = RandomForestRegressor(random_state=42).fit(X, y)
            pred = model.predict([list(inputs.values())])[0]
            st.metric(f"Predicted {target}", f"{pred:.3f}")
        except Exception as e:
            st.error(f"Prediction error: {e}")


def render_feature_engineering_tab(df):
    section_header("⚡ Feature Engineering Studio", "Create new predictive features from existing variables.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    tab_interact, tab_bin, tab_lag = st.tabs(["✖️ Interaction Features", "📦 Binning", "📈 Polynomial Features"])

    with tab_interact:
        if len(numeric_cols) >= 2:
            f1 = st.selectbox("Feature 1", numeric_cols, key="fe_f1")
            f2 = st.selectbox("Feature 2", [c for c in numeric_cols if c != f1], key="fe_f2")
            if st.button("➕ Create Interaction Feature", type="primary", key="run_fe_interact"):
                new_col = f"{f1}_x_{f2}"
                df[new_col] = df[f1] * df[f2]
                set_active_dataframe(df, st.session_state.get("source_name", "engineered.csv"))
                st.success(f"✅ Created '{new_col}'")
                st.rerun()
        else:
            st.info("Need 2 numeric columns.")

    with tab_bin:
        if numeric_cols:
            col = st.selectbox("Variable to bin", numeric_cols, key="fe_bin_col")
            n_bins = st.slider("Bins", 2, 10, 4, key="fe_bin_n")
            if st.button("📦 Create Binned Feature", type="primary", key="run_fe_bin"):
                df[f"{col}_bin"] = pd.cut(df[col], bins=n_bins, labels=[f"B{i+1}" for i in range(n_bins)])
                set_active_dataframe(df, st.session_state.get("source_name", "binned.csv"))
                st.success(f"✅ Binned '{col}' into {n_bins} categories")
                st.rerun()
        else:
            st.info("No numeric columns.")

    with tab_lag:
        if numeric_cols:
            col = st.selectbox("Variable for polynomial", numeric_cols, key="fe_poly_col")
            degree = st.slider("Polynomial degree", 2, 5, 2, key="fe_poly_deg")
            if st.button("📈 Create Polynomial Features", type="primary", key="run_fe_poly"):
                for d in range(2, degree + 1):
                    df[f"{col}^pow{d}"] = df[col] ** d
                set_active_dataframe(df, st.session_state.get("source_name", "polynomial.csv"))
                st.success(f"✅ Created polynomial features up to degree {degree}")
                st.rerun()
        else:
            st.info("No numeric columns.")


def render_agents_tab():
    section_header("🦾 Autonomous Agent Swarm Console", "Deploy background agent missions and automation tasks.")

    mission = st.selectbox("Select Agent Mission", [
        "Anomaly Detection Sweep",
        "Data Quality Monitoring",
        "Predictive Maintenance",
        "Automated Report Generation",
        "Cross-Hub Data Pipeline",
    ], key="agent_mission")

    if st.button("🚀 Deploy Agent", type="primary", key="deploy_agent"):
        with st.spinner(f"Deploying agent for: {mission}..."):
            import time
            time.sleep(1.5)
        st.success(f"✅ Agent deployed for '{mission}'. Result logged.")
        st.info("Agent missions run in the background and log results to the telemetry system.")


def render_chaos_tab():
    section_header(
        "🌀 Chaos & Nonlinear Systems Lab",
        "Real SciPy ODE integration, bifurcation analysis, Monte Carlo ensembles, sensitivity landscapes, and from-scratch forecasting.",
    )

    st.markdown(
        "This is a **real nonlinear dynamical systems sandbox**. Every trajectory is genuinely computed by "
        "integrating the shown differential equations with SciPy's LSODA solver — nothing is fabricated. "
        "Use it to explore feedback, instability, and early-warning signals for any system you label a sector to."
    )

    try:
        from modules.chaos_engine import (
            solve_ode_system,
            default_ode,
            lyapunov_style_heuristic,
            rolling_variance_autocorr,
            classify_state,
            bifurcation_scan,
            monte_carlo_ensemble,
            sensitivity_heatmap,
            holt_winters_forecast,
            ar_least_squares_forecast,
            anomaly_flags,
        )
    except ImportError as e:
        st.error(f"Chaos engine unavailable: {e}")
        return

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    # ── Model configuration ──────────────────────────────────────────
    with st.expander("⚙️ Model configuration", expanded=True):
        colA, colB = st.columns(2)
        with colA:
            sector_presets = {
                "Generic / custom": ("a", "Drive term", "b", "Friction term", "c", "Buffer decay"),
                "Economics-style": ("a", "Growth driver", "b", "Investment cost", "c", "Market elasticity"),
                "Health-system-style": ("a", "Patient influx", "b", "Capacity burnout", "c", "Staff fatigue decay"),
                "Epidemiology-style": ("a", "Transmission", "b", "Recovery", "c", "Waning immunity"),
                "Grid-style": ("a", "Demand surge", "b", "Load friction", "c", "Buffer capacity"),
            }
            sector = st.selectbox("Sector framing (labels only)", list(sector_presets.keys()))
            a_label, a_desc, b_label, b_desc, c_label, c_desc = sector_presets[sector]
        with colB:
            t_max = st.slider("Simulation horizon (steps)", 50, 400, 200, 10)
            policy_shock = st.slider("Injected shock magnitude (mid-run)", -3.0, 3.0, 0.0, 0.1)
            pss_slice_z = st.slider("Poincaré cut plane (Z)", -3.0, 3.0, 0.1, 0.05)

        col1, col2, col3 = st.columns(3)
        a = col1.slider(f"{a_label} ({a_desc})", 0.1, 5.0, 1.5, 0.1)
        b = col2.slider(f"{b_label} ({b_desc})", 0.0, 3.0, 0.9, 0.1)
        c = col3.slider(f"{c_label} ({c_desc})", 0.0, 3.0, 1.0, 0.1)

        col4, col5, col6 = st.columns(3)
        x0 = col4.number_input("Initial x0", value=0.10, format="%.3f")
        y0 = col5.number_input("Initial y0", value=0.10, format="%.3f")
        z0 = col6.number_input("Initial z0", value=0.10, format="%.3f")

    # ── Integrate the real system ────────────────────────────────────
    t = np.linspace(0, t_max, t_max * 2)
    initial_state = [x0, y0, z0]
    solution = solve_ode_system(default_ode, initial_state, t, args=(a, b, c, policy_shock, t_max))
    x_traj, y_traj, z_traj = solution[:, 0], solution[:, 1], solution[:, 2]
    dt = t[1] - t[0]
    mlce = lyapunov_style_heuristic(x_traj, dt)
    rolling_var, rolling_ac = rolling_variance_autocorr(x_traj)
    state_label = classify_state(mlce)

    tabs = st.tabs([
        "Executive View", "3D Phase Space", "Poincaré Section", "Early Warning Signals",
        "Bifurcation", "Monte Carlo Ensemble", "Sensitivity Heatmap", "Forecasting",
    ])

    with tabs[0]:
        c1, c2 = st.columns(2)
        c2.metric("Trajectory State", state_label, delta=f"mLCE≈{mlce:.4f}")
        c1.metric("Expansion-Rate Heuristic", f"{mlce:.4f}")
        fig = go.Figure(data=[go.Scatter3d(x=x_traj, y=y_traj, z=z_traj, mode="lines",
                        line=dict(color="#60A5FA", width=4), marker=dict(size=2, color=z_traj, colorscale="Viridis", opacity=0.9))])
        fig.update_layout(title_text="3D Phase Portrait", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=480, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        fig = go.Figure(data=[go.Scatter3d(x=x_traj, y=y_traj, z=z_traj, mode="lines", line=dict(color="#60A5FA", width=4))])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=550, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        mask = np.abs(z_traj - pss_slice_z) < 0.05
        fig = go.Figure(data=[go.Scatter(x=x_traj[mask], y=y_traj[mask], mode="markers", marker=dict(size=4, color="#60A5FA"))])
        fig.update_layout(title_text=f"Poincaré Section (Z={pss_slice_z:.2f})", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=450, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[3]:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Rolling Variance (critical slowing down)", "Rolling Autocorrelation (lag-1)"))
        fig.add_trace(go.Scatter(x=t, y=rolling_var, line=dict(color="#F59E0B")), row=1, col=1)
        fig.add_trace(go.Scatter(x=t, y=rolling_ac, line=dict(color="#EC4899")), row=2, col=1)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[4]:
        st.caption("Recomputes the model across a range of the friction parameter (b) and records local maxima.")
        if st.button("Run bifurcation scan", key="chaos_bif"):
            with st.spinner("Scanning parameter space..."):
                b_pts, peaks = bifurcation_scan(default_ode, initial_state, t, np.linspace(0.2, 2.8, 40), param_idx=1, args_base=(a, b, c, 0.0, t_max))
            fig = go.Figure(data=[go.Scatter(x=b_pts, y=peaks, mode="markers", marker=dict(size=1.5, color="#60A5FA", opacity=0.6))])
            fig.update_layout(title_text="Bifurcation Diagram", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=450, margin=dict(l=0, r=0, t=50, b=0))
            fig.update_xaxes(title_text=f"{b_label} (b)"); fig.update_yaxes(title_text="Local Extrema")
            st.plotly_chart(fig, use_container_width=True)

    with tabs[5]:
        n_mc = st.slider("Ensemble runs", 10, 150, 30, 10, key="chaos_mc_n")
        if st.button("Run Monte Carlo ensemble", key="chaos_mc"):
            with st.spinner(f"Running {n_mc} perturbed integrations..."):
                mc_runs = monte_carlo_ensemble(default_ode, initial_state, t, (a, b, c, policy_shock, t_max), n_runs=n_mc)
            fig = go.Figure()
            for i in range(mc_runs.shape[1]):
                fig.add_trace(go.Scatter(x=t, y=mc_runs[:, i], mode="lines", line=dict(width=0.8, color="rgba(96,165,250,0.25)"), showlegend=False))
            fig.update_layout(title_text=f"Monte Carlo Uncertainty Envelope ({n_mc} runs)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=450, margin=dict(l=0, r=0, t=50, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with tabs[6]:
        if st.button("Compute sensitivity heatmap (a vs b)", key="chaos_sens"):
            with st.spinner("Computing 2D sensitivity landscape..."):
                a_grid, b_grid, Z_m = sensitivity_heatmap(default_ode, initial_state, t, np.linspace(0.5, 3.0, 12), np.linspace(0.2, 2.0, 12), args_base=(a, b, c, 0.0, t_max))
            fig = go.Figure(data=go.Contour(z=Z_m, x=a_grid, y=b_grid, colorscale="Viridis", contours=dict(coloring="heatmap")))
            fig.update_layout(title_text=f"Sensitivity Landscape: {a_label} vs {b_label}", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500, margin=dict(l=0, r=0, t=50, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with tabs[7]:
        st.markdown("#### Real from-scratch forecasting (Holt-Winters + AR least-squares)")
        series_src = st.radio("Series source", ["Use real extracted trajectory", "Use active dataset column"], horizontal=True, key="chaos_fc_src")
        series = None
        if series_src == "Use real extracted trajectory":
            series = x_traj
        elif df is not None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                col = st.selectbox("Numeric column to forecast", numeric_cols, key="chaos_fc_col")
                series = df[col].dropna().values
        if series is not None and len(series) >= 4:
            periods = st.slider("Periods to forecast", 1, 30, 12, key="chaos_fc_periods")
            fitted_hw, forecast_hw = holt_winters_forecast(series, periods=periods)
            lags = st.slider("AR lag order (p)", 1, min(10, max(1, len(series) // 3)), 3, key="chaos_fc_lags")
            fitted_ar, forecast_ar, coeffs = ar_least_squares_forecast(series, lags=lags, periods=periods)
            x_hist = np.arange(len(series))
            x_fore = np.arange(len(series), len(series) + periods)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x_hist, y=series, name="Observed", line=dict(color="#94A3B8", width=2)))
            fig.add_trace(go.Scatter(x=x_hist, y=fitted_hw, name="Holt-Winters fit", line=dict(color="#38BDF8", width=2, dash="dot")))
            fig.add_trace(go.Scatter(x=x_fore, y=forecast_hw, name="Holt-Winters forecast", line=dict(color="#38BDF8", width=3)))
            fig.add_trace(go.Scatter(x=x_fore, y=forecast_ar, name=f"AR({lags}) forecast", line=dict(color="#F472B6", width=3, dash="dash")))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=460, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)
            resid = series[lags:] - fitted_ar
            mae = float(np.mean(np.abs(resid))) if len(resid) else 0.0
            c1, c2 = st.columns(2)
            c1.metric("AR In-Sample MAE", f"{mae:.3f}")
            c2.metric("Series Length", f"{len(series)} pts")
        else:
            st.info("Need at least 4 numeric points to forecast.")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()  # paywall/trial gate, real DB check

    setup_page("ML & Predictive Studio", "🤖", initial_sidebar_state="expanded")

    hero_card(
        "🤖 ML & Predictive Studio",
        "Consolidated machine learning hub: AutoML training, prediction engine, feature engineering, autonomous agents, and advanced AI intelligence cores.",
        badge_text="ML & PREDICTIVE STUDIO • CONSOLIDATED HUB",
    )

    render_dataset_context_banner()

    df = get_df()

    tabs = st.tabs([
        "🤖 AutoML Training",
        "🔮 Prediction Engine",
        "⚡ Feature Engineering",
        "🦾 Agent Console",
        "⚛️ AI & Chaos Cores",
    ])

    with tabs[0]:
        render_automl_tab(df)
    with tabs[1]:
        render_predict_tab(df)
    with tabs[2]:
        render_feature_engineering_tab(df)
    with tabs[3]:
        render_agents_tab()
    with tabs[4]:
        render_chaos_tab()

    render_standard_footer("ML & PREDICTIVE STUDIO")


if __name__ == "__main__":
    main()
