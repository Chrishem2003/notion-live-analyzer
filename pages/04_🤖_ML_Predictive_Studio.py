import io
import os
import sys
import pickle
import hashlib
import numpy as np
import pandas as pd
import scipy.stats as sps
import streamlit as st

# Ensure root path accessibility
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Core ML Libraries Initialization
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
    from sklearn.preprocessing import StandardScaler, LabelEncoder, PolynomialFeatures
    from sklearn.impute import SimpleImputer
    from sklearn.ensemble import (
        RandomForestClassifier,
        RandomForestRegressor,
        GradientBoostingClassifier,
        GradientBoostingRegressor,
    )
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import accuracy_score, r2_score, mean_squared_error, roc_auc_score
    from sklearn.feature_selection import SelectKBest, f_classif, f_regression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Module Fallback Wrappers
def setup_page(title, icon, initial_sidebar_state="expanded"):
    st.set_page_config(page_title=title, page_icon=icon, layout="wide", initial_sidebar_state=initial_sidebar_state)

def render_standard_footer(title):
    st.markdown("---")
    st.caption(f"© Enterprise AI Engine — {title}}")

def hero_card(title, subtitle, badge_text):
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 1.5rem; border-radius: 10px; border: 1px solid #334155; margin-bottom: 1.5rem;">
            <span style="background-color: #3b82f6; color: white; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.75rem; font-weight: bold;">{badge_text}</span>
            <h2 style="color: white; margin-top: 0.5rem; margin-bottom: 0.25rem;">{title}</h2>
            <p style="color: #94a3b8; font-size: 0.95rem; margin: 0;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def section_header(title, subtitle):
    st.markdown(f"### {title}}")
    st.markdown(f"*{subtitle}}*")

def render_dataset_context_banner():
    pass

def render_export_buttons(df_export, base_name="data_export"):
    csv = df_export.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Export (CSV)", data=csv, file_name=f"{base_name}}.csv", mime="text/csv")

def get_active_dataframe():
    return st.session_state.get("active_df", None)

def set_active_dataframe(df, source_name="dataset.csv"):
    st.session_state["active_df"] = df
    st.session_state["source_name"] = source_name

PARAM_GRIDS = {
    "Random Forest": {"n_estimators": [100, 200], "max_depth": [None, 10, 20]},
    "Gradient Boosting": {"n_estimators": [100, 150], "learning_rate": [0.05, 0.1]},
    "Logistic Regression": {"C": [0.1, 1.0, 10.0]},
    "Ridge Regression": {"alpha": [0.1, 1.0, 10.0]},
}

def get_df():
    df = get_active_dataframe()
    if df is None:
        np.random.seed(42)
        df = pd.DataFrame({
            "Feature_A": np.random.normal(12.5, 2.1, 200),
            "Feature_B": np.random.normal(8.3, 1.4, 200),
            "Feature_C": np.random.uniform(0.1, 5.0, 200),
            "Category_X": np.random.choice(["Type 1", "Type 2", "Type 3"], 200),
            "Target": np.random.choice([0, 1], p=[0.4, 0.6], size=200),
        })
        set_active_dataframe(df, "synthetic_default.csv")
    return df

def _build_model_registry(task: str) -> dict:
    if task == "Classification":
        return {
            "Random Forest": RandomForestClassifier(random_state=42),
            "Gradient Boosting": GradientBoostingClassifier(random_state=42),
            "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        }
    return {
        "Random Forest": RandomForestRegressor(random_state=42),
        "Gradient Boosting": GradientBoostingRegressor(random_state=42),
        "Ridge Regression": Ridge(random_state=42),
    }

def _serialize_pipeline(bundle: dict) -> bytes:
    buf = io.BytesIO()
    if JOBLIB_AVAILABLE:
        joblib.dump(bundle, buf)
    else:
        pickle.dump(bundle, buf)
    return buf.getvalue()

def _deserialize_pipeline(raw_bytes: bytes) -> dict:
    buf = io.BytesIO(raw_bytes)
    if JOBLIB_AVAILABLE:
        return joblib.load(buf)
    return pickle.load(buf)

def render_automl_tab(df):
    section_header("🤖 Advanced AutoML & Hyperparameter Studio", "Train, tune, cross-validate, and evaluate production-ready machine learning pipelines.")

    if not SKLEARN_AVAILABLE:
        st.error("⚠️ `scikit-learn` is required to run machine learning workflows.")
        return

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        st.warning("No numeric features available for processing.")
        return

    target = st.selectbox("Select Target Variable", df.columns, key="ml_target")
    available_features = [c for c in df.columns if c != target]
    features = st.multiselect("Select Feature Predictors", available_features, default=available_features[:min(4, len(available_features))], key="ml_features")

    col1, col2, col3 = st.columns(3)
    with col1:
        test_size = st.slider("Test Split (%)", 10, 50, 20, 5, key="ml_test")
    with col2:
        task = st.radio("Task Type", ["Classification", "Regression"], horizontal=True, key="ml_task")
    with col3:
        cv_folds = st.slider("Cross-Validation Folds", 3, 10, 5, key="ml_cv")

    tune = st.checkbox("🔧 Enable Hyperparameter Tuning (GridSearchCV)", value=False, key="ml_tune")

    models = _build_model_registry(task)
    selected_models = st.multiselect("Select Algorithms to Evaluate", list(models.keys()), default=list(models.keys()), key="ml_algos")

    if st.button("🚀 Run AutoML & Cross-Validation Suite", type="primary", key="run_ml"):
        if not features:
            st.error("Select at least one feature.")
            return
        if not selected_models:
            st.error("Select at least one algorithm.")
            return
        if task == "Regression" and not pd.api.types.is_numeric_dtype(pd.to_numeric(df[target], errors="coerce")):
            st.error(f"⛔ Target `{target}}` cannot be converted to numeric values for regression.")
            return

        with st.spinner("Processing pipeline transformations and training models..."):
            try:
                X_raw = df[features].copy()
                X_encoded = pd.get_dummies(X_raw, drop_first=True)
                y_raw = df[target].copy()

                label_encoder = None
                if task == "Classification":
                    if y_raw.dtype == "object" or str(y_raw.dtype) == "category" or y_raw.dtype == "bool":
                        label_encoder = LabelEncoder()
                        y_processed = label_encoder.fit_transform(y_raw.astype(str))
                    else:
                        y_processed = y_raw.values
                    scoring = "accuracy"
                else:
                    y_num = pd.to_numeric(y_raw, errors="coerce")
                    valid_mask = y_num.notnull()
                    if valid_mask.sum() < 10:
                        st.error("⛔ Less than 10 valid non-null target samples available.")
                        return
                    X_encoded = X_encoded.loc[valid_mask]
                    y_processed = y_num.loc[valid_mask].values
                    scoring = "r2"

                X_train, X_test, y_train, y_test = train_test_split(X_encoded, y_processed, test_size=test_size / 100, random_state=42)

                imputer = SimpleImputer(strategy="median")
                X_tr_imp = imputer.fit_transform(X_train)
                X_te_imp = imputer.transform(X_test)

                scaler = StandardScaler()
                X_tr = scaler.fit_transform(X_tr_imp)
                X_te = scaler.transform(X_te_imp)

                results = []
                trained_models = {}
                best_name, best_score, best_model = None, -np.inf, None

                for name in selected_models:
                    base_model = models[name]
                    best_params_note = "default"

                    if tune and name in PARAM_GRIDS:
                        grid = GridSearchCV(base_model, PARAM_GRIDS[name], cv=cv_folds, scoring=scoring, n_jobs=-1)
                        grid.fit(X_tr, y_train)
                        model = grid.best_estimator_
                        cv_mean, cv_std = grid.best_score_, np.nan
                        best_params_note = str(grid.best_params_)
                    else:
                        cv_scores = cross_val_score(base_model, X_tr, y_train, cv=cv_folds, scoring=scoring)
                        cv_mean, cv_std = cv_scores.mean(), cv_scores.std()
                        model = base_model
                        model.fit(X_tr, y_train)

                    y_pred = model.predict(X_te)

                    if task == "Classification":
                        test_metric = accuracy_score(y_test, y_pred)
                        auc_str = "N/A"
                        if hasattr(model, "predict_proba"):
                            try:
                                y_proba = model.predict_proba(X_te)
                                if len(np.unique(y_test)) == 2:
                                    auc_str = f"{roc_auc_score(y_test, y_proba[:, 1]):.4f}}"
                                else:
                                    auc_str = f"{roc_auc_score(y_test, y_proba, multi_class='ovr'):.4f}}"
                            except Exception:
                                pass
                        results.append({
                            "Algorithm": name,
                            "CV Accuracy": f"{cv_mean * 100:.2f}}%" + (f" (±{cv_std*100:.2f}}%)" if not np.isnan(cv_std) else ""),
                            "Test Accuracy": f"{test_metric * 100:.2f}}%",
                            "ROC-AUC": auc_str,
                            "Params": best_params_note,
                        })
                    else:
                        test_metric = r2_score(y_test, y_pred)
                        test_rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                        results.append({
                            "Algorithm": name,
                            "CV R²": f"{cv_mean:.4f}}" + (f" (±{cv_std:.4f}})" if not np.isnan(cv_std) else ""),
                            "Test R²": f"{test_metric:.4f}}",
                            "Test RMSE": f"{test_rmse:.4f}}",
                            "Params": best_params_note,
                        })

                    trained_models[name] = model
                    if test_metric > best_score:
                        best_score, best_name, best_model = test_metric, name, model

                res_df = pd.DataFrame(results)
                st.markdown("#### 📊 Model Performance Leaderboard")
                st.dataframe(res_df, use_container_width=True, hide_index=True)
                st.success(f"✅ Optimal Algorithm: **{best_name}}** (Test Metric Score: {best_score:.4f}})")

                if "Random Forest" in trained_models and hasattr(trained_models["Random Forest"], "feature_importances_"):
                    st.markdown("#### 🔍 Feature Importances (Random Forest)")
                    importances = pd.Series(trained_models["Random Forest"].feature_importances_, index=X_encoded.columns).sort_values(ascending=False)
                    st.bar_chart(importances)

                st.session_state["ml_active_pipeline"] = {
                    "model": best_model,
                    "imputer": imputer,
                    "scaler": scaler,
                    "feature_columns": list(X_encoded.columns),
                    "raw_features": features,
                    "task": task,
                    "target": target,
                    "label_encoder": label_encoder,
                    "algorithm": best_name,
                    "test_score": float(best_score),
                    "trained_at": pd.Timestamp.now().isoformat(),
                }

            except Exception as e:
                st.error(f"Training Exception: {e}}")

    pipeline = st.session_state.get("ml_active_pipeline")
    if pipeline:
        st.markdown("---")
        st.markdown("#### 💾 Model Persistence & Export")
        c1, c2 = st.columns(2)
        with c1:
            st.caption(f"Active Model: **{pipeline['algorithm']}}** ({pipeline['task']}}, target=`{pipeline['target']}}`, score={pipeline['test_score']:.4f}})")
            raw_bytes = _serialize_pipeline(pipeline)
            st.download_button(
                "⬇️ Export Trained Pipeline (.pkl)",
                data=raw_bytes,
                file_name=f"ml_pipeline_{pipeline['algorithm'].lower().replace(' ', '_')}}.pkl",
                mime="application/octet-stream",
                key="dl_pipeline",
            )
        with c2:
            uploaded_pipeline = st.file_uploader("📤 Import Trained Pipeline (.pkl)", type=["pkl"], key="upload_pipeline")
            if uploaded_pipeline is not None and st.button("Load Pipeline", key="load_pipeline"):
                try:
                    loaded = _deserialize_pipeline(uploaded_pipeline.getvalue())
                    st.session_state["ml_active_pipeline"] = loaded
                    st.success(f"✅ Pipeline Loaded: {loaded.get('algorithm', 'Unknown')}} ({loaded.get('task', 'Unknown')}})")
                    st.rerun()
                except Exception as e:
                    st.error(f"Pipeline Deserialization Failed: {e}}")

def render_predict_tab(df):
    section_header("🔮 Interactive Prediction Engine", "Generate real-time inferences using the persisted model pipeline.")

    if not SKLEARN_AVAILABLE:
        st.error("`scikit-learn` required.")
        return

    pipeline = st.session_state.get("ml_active_pipeline")
    if not pipeline:
        st.warning("⚠️ Active pipeline non-existent. Train a model in **AutoML & Training** tab to execute predictions.")
        return

    model, imputer, scaler = pipeline["model"], pipeline["imputer"], pipeline["scaler"]
    feature_cols, raw_features = pipeline["feature_columns"], pipeline["raw_features"]
    task, target, label_encoder = pipeline["task"], pipeline["target"], pipeline["label_encoder"]

    st.info(f"Active Architecture: **{pipeline['algorithm']}}** | Target: `{target}}` | Task: {task}} | Trained: {pipeline['trained_at'][:19]}}")

    mode = st.radio("Inference Strategy", ["Single Record Ingestion", "Batch CSV Inference"], horizontal=True, key="pred_mode")

    def _predict(input_df: pd.DataFrame):
        encoded = pd.get_dummies(input_df[raw_features], drop_first=True)
        encoded = encoded.reindex(columns=feature_cols, fill_value=0)
        imp = imputer.transform(encoded)
        scaled = scaler.transform(imp)
        preds = model.predict(scaled)
        proba, interval = None, None
        if task == "Classification":
            if hasattr(model, "predict_proba"):
                try:
                    proba = model.predict_proba(scaled)
                except Exception:
                    proba = None
            if label_encoder is not None:
                preds = label_encoder.inverse_transform(preds.astype(int))
        elif hasattr(model, "estimators_"):
            tree_preds = np.array([est.predict(scaled) for est in model.estimators_])
            interval = (np.percentile(tree_preds, 5, axis=0), np.percentile(tree_preds, 95, axis=0))
        return preds, proba, interval

    if mode == "Single Record Ingestion":
        st.markdown("#### Input Feature Values")
        inputs = {}
        cols = st.columns(min(4, max(1, len(raw_features))))
        for i, feat in enumerate(raw_features):
            col = cols[i % len(cols)]
            if pd.api.types.is_numeric_dtype(df[feat]):
                inputs[feat] = col.number_input(feat, value=float(df[feat].mean()), key=f"pred_in_{feat}}")
            else:
                options = df[feat].dropna().unique().tolist()
                inputs[feat] = col.selectbox(feat, options if options else ["None"], key=f"pred_in_{feat}}")

        if st.button("🔮 Compute Prediction", type="primary", key="run_predict"):
            try:
                input_df = pd.DataFrame([inputs])
                preds, proba, interval = _predict(input_df)
                if task == "Classification":
                    st.metric(f"Predicted Target ({target}})", str(preds[0]))
                    if proba is not None:
                        classes = label_encoder.classes_ if label_encoder is not None else getattr(model, "classes_", range(proba.shape[1]))
                        proba_df = pd.DataFrame({"Class": classes, "Probability": proba[0]}).sort_values("Probability", ascending=False)
                        st.dataframe(proba_df, use_container_width=True, hide_index=True)
                else:
                    st.metric(f"Predicted Target ({target}})", f"{preds[0]:.4f}}")
                    if interval is not None:
                        st.caption(f"Estimated 90% Confidence Interval: [{interval[0][0]:.4f}}, {interval[1][0]:.4f}}]")
            except Exception as e:
                st.error(f"Inference Exception: {e}}")

    else:
        st.markdown("#### Batch Prediction Suite")
        st.caption(f"Required Schema Predictors: {', '.join(raw_features)}}")
        batch_file = st.file_uploader("Upload Target CSV Payload", type=["csv"], key="pred_batch_upload")
        if batch_file is not None and st.button("🔮 Execute Batch Inference", type="primary", key="run_batch_predict"):
            try:
                batch_df = pd.read_csv(batch_file)
                missing = [c for c in raw_features if c not in batch_df.columns]
                if missing:
                    st.error(f"⛔ Missing baseline columns: {', '.join(missing)}}")
                else:
                    preds, proba, interval = _predict(batch_df)
                    out = batch_df.copy()
                    out[f"Predicted_{target}}"] = preds
                    if interval is not None:
                        out["Interval_Low_90"], out["Interval_High_90"] = interval[0], interval[1]
                    st.dataframe(out, use_container_width=True)
                    render_export_buttons(out, base_name="batch_predictions")
            except Exception as e:
                st.error(f"Batch Execution Exception: {e}}")

def render_feature_engineering_tab(df):
    section_header("⚡ Feature Engineering Studio", "Transform and expand target datasets using advanced operations.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    tab_interact, tab_bin, tab_poly, tab_select = st.tabs([
        "✖️ Interactions", "📦 Binning & Quantiles", "📈 Polynomials", "🎯 Feature Selection"
    ])

    with tab_interact:
        if len(numeric_cols) >= 2:
            f1 = st.selectbox("Feature 1", numeric_cols, key="fe_f1")
            f2 = st.selectbox("Feature 2", [c for c in numeric_cols if c != f1], key="fe_f2")
            op = st.selectbox("Mathematical Operation", ["Multiply (X * Y)", "Divide (X / Y)", "Difference (X - Y)", "Sum (X + Y)"], key="fe_op")

            if st.button("➕ Generate Feature", type="primary", key="run_fe_interact"):
                working = df.copy()
                if "Multiply" in op:
                    new_col, values = f"{f1}}_mul_{f2}}", working[f1] * working[f2]
                elif "Divide" in op:
                    new_col, values = f"{f1}}_div_{f2}}", working[f1] / working[f2].replace(0, np.nan)
                elif "Difference" in op:
                    new_col, values = f"{f1}}_sub_{f2}}", working[f1] - working[f2]
                else:
                    new_col, values = f"{f1}}_add_{f2}}", working[f1] + working[f2]

                working[new_col] = values
                set_active_dataframe(working, st.session_state.get("source_name", "engineered.csv"))
                st.success(f"✅ Generated engineered feature '{new_col}}'")
                st.rerun()
        else:
            st.info("Requires at least 2 numeric features.")

    with tab_bin:
        if numeric_cols:
            col = st.selectbox("Target Binning Feature", numeric_cols, key="fe_bin_col")
            strategy = st.radio("Bin Strategy", ["Equal Width (Uniform)", "Equal Frequency (Quantiles)"], horizontal=True, key="fe_bin_strat")
            n_bins = st.slider("Bin Split Count", 2, 10, 4, key="fe_bin_n")

            if st.button("📦 Execute Binning", type="primary", key="run_fe_bin"):
                working = df.copy()
                if "Uniform" in strategy:
                    working[f"{col}}_bin"] = pd.cut(working[col], bins=n_bins, labels=[f"Bin_{i+1}}" for i in range(n_bins)])
                else:
                    working[f"{col}}_bin"] = pd.qcut(working[col], q=n_bins, labels=[f"Q_{i+1}}" for i in range(n_bins)], duplicates="drop")
                set_active_dataframe(working, st.session_state.get("source_name", "binned.csv"))
                st.success(f"✅ Feature '{col}}' transformed into {n_bins}} distinct bins.")
                st.rerun()
        else:
            st.info("No numeric features available.")

    with tab_poly:
        if numeric_cols:
            mode = st.radio("Polynomial Processing Mode", ["Single Column Powers", "Multi-Column Polynomial Sets"], key="fe_poly_mode")
            if mode == "Single Column Powers":
                col = st.selectbox("Select Target Column", numeric_cols, key="fe_poly_col")
                degree = st.slider("Max Polynomial Degree", 2, 4, 2, key="fe_poly_deg")
                if st.button("📈 Compute Polynomials", type="primary", key="run_fe_poly"):
                    working = df.copy()
                    for d in range(2, degree + 1):
                        working[f"{col}}_pow{d}}"] = working[col] ** d
                    set_active_dataframe(working, st.session_state.get("source_name", "polynomial.csv"))
                    st.success(f"✅ Created polynomial features up to degree {degree}}.")
                    st.rerun()
            else:
                if not SKLEARN_AVAILABLE:
                    st.error("`scikit-learn` required for multi-column polynomial expansions.")
                else:
                    cols_sel = st.multiselect("Select Target Features", numeric_cols, default=numeric_cols[:min(2, len(numeric_cols))], key="fe_poly_cols")
                    degree = st.slider("Degree Expansion", 2, 3, 2, key="fe_poly_multi_deg")
                    if len(cols_sel) >= 2 and st.button("📈 Expand Polynomial Set", type="primary", key="run_fe_poly_multi"):
                        working = df.copy()
                        clean = working[cols_sel].dropna()
                        poly = PolynomialFeatures(degree=degree, include_bias=False)
                        expanded = poly.fit_transform(clean)
                        names = poly.get_feature_names_out(cols_sel)
                        expanded_df = pd.DataFrame(expanded, columns=names, index=clean.index)
                        new_names = [n for n in names if n not in cols_sel]
                        for n in new_names:
                            working.loc[clean.index, n] = expanded_df[n]
                        set_active_dataframe(working, st.session_state.get("source_name", "polynomial_expanded.csv"))
                        st.success(f"✅ Poly expansion completed: {len(new_names)}} features derived.")
                        st.rerun()
        else:
            st.info("No numeric columns available.")

    with tab_select:
        st.markdown("#### Automated Feature Selection (SelectKBest)")
        if len(df.columns) >= 3:
            target_col = st.selectbox("Target Variable", df.columns, key="fs_target")
            is_classification = not pd.api.types.is_numeric_dtype(df[target_col]) or df[target_col].nunique() <= 10
            st.caption(f"Inferred Execution: **{'Classification (f_classif)' if is_classification else 'Regression (f_regression)'}}**")

            features_pool = [c for c in numeric_cols if c != target_col]
            if not features_pool:
                st.info("Numeric predictors required.")
            else:
                k_val = st.slider("Top K Features to Extract", 1, min(len(features_pool), 10), min(len(features_pool), 3), key="fs_k")

                if st.button("🎯 Execute Selection", type="primary", key="run_fs"):
                    clean_df = df[features_pool + [target_col]].dropna()
                    X_sel = clean_df[features_pool]
                    y_raw = clean_df[target_col]

                    if is_classification:
                        y_sel = LabelEncoder().fit_transform(y_raw.astype(str)) if not pd.api.types.is_numeric_dtype(y_raw) else y_raw
                        selector = SelectKBest(score_func=f_classif, k=k_val)
                    else:
                        y_sel = y_raw
                        selector = SelectKBest(score_func=f_regression, k=k_val)

                    selector.fit(X_sel, y_sel)
                    scores = pd.Series(selector.scores_, index=features_pool).fillna(0).sort_values(ascending=False)

                    st.markdown("#### 📊 Feature Significance Scores")
                    st.bar_chart(scores)
                    top_feats = scores.head(k_val).index.tolist()
                    st.success(f"✅ Top {k_val}} Optimal Features: {', '.join(top_feats)}}")
        else:
            st.info("Dataset requires a minimum of 3 features for selection scanning.")

def _mission_outlier_sweep(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    rows = []
    for c in numeric_cols:
        s = df[c].dropna()
        if s.empty:
            continue
        q1, q3 = np.percentile(s, 25), np.percentile(s, 75)
        iqr = q3 - q1
        mask = (s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)
        rows.append({"Column": c, "Outliers Found": int(mask.sum()), "Outlier Rate (%)": round(100 * mask.sum() / len(s), 2)})
    return pd.DataFrame(rows).sort_values("Outliers Found", ascending=False) if rows else pd.DataFrame()

def _mission_quality_audit(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "Column": df.columns,
        "Null Count": df.isnull().sum().values,
        "Null %": (df.isnull().mean() * 100).round(2).values,
        "Duplicate Rows (Dataset Wide)": [int(df.duplicated().sum())] * len(df.columns),
    })

def _mission_trend_check(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    rows = []
    x = np.arange(len(df))
    for c in numeric_cols:
        y = df[c].values
        mask = ~pd.isnull(y)
        if mask.sum() < 5 or np.std(y[mask]) == 0:
            continue
        slope, intercept, r, p, se = sps.linregress(x[mask], y[mask])
        state = "Degrading" if (slope < 0 and p < 0.05) else ("Improving" if (slope > 0 and p < 0.05) else "Stable")
        rows.append({"Column": c, "Trend Slope": round(slope, 5), "P-Value": round(p, 5), "Assessment": state})
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def _mission_executive_report(df: pd.DataFrame) -> str:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    lines = [
        "# AUTOMATED EXECUTIVE DATA REPORT",
        f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}}",
        "",
        f"- Total Samples: {df.shape[0]:,}} | Total Columns: {df.shape[1]}}",
        f"- Missing Values: {int(df.isnull().sum().sum()):,}}",
        f"- Duplicate Records: {int(df.duplicated().sum()):,}}",
    ]
    if numeric_cols:
        lines.append("\n## Numeric Distribution Overview")
        lines.append(df[numeric_cols].describe().T.round(3).to_string())
        if len(numeric_cols) >= 2:
            corr = df[numeric_cols].corr().abs()
            upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
            stacked = upper.stack()
            if not stacked.empty:
                top_pair = stacked.idxmax()
                lines.append(f"\n## Top Collinear Feature Pair\n`{top_pair[0]}}` ↔ `{top_pair[1]}}`: r = {stacked.max():.3f}}")
    return "\n".join(lines)

def render_agents_tab():
    section_header("🤖 Autonomous Data Agents", "Execute non-simulated, autonomous dataset diagnostics.")

    df = get_active_dataframe()
    if df is None:
        st.warning("⚠️ Active dataset required for scanning.")
        return

    mission = st.selectbox("Select Diagnostic Mission", [
        "Outlier Detection & IQR Sweep",
        "Data Quality & Completeness Audit",
        "Trend & Monotonicity Analysis",
        "Executive Report Generation",
    ], key="agent_mission")

    if st.button("🚀 Execute Mission", type="primary", key="deploy_agent"):
        with st.spinner(f"Executing: {mission}}..."):
            if mission == "Outlier Detection & IQR Sweep":
                result = _mission_outlier_sweep(df)
                if result.empty:
                    st.info("No numeric features available.")
                else:
                    st.dataframe(result, use_container_width=True, hide_index=True)
                    render_export_buttons(result, base_name="agent_outliers")

            elif mission == "Data Quality & Completeness Audit":
                result = _mission_quality_audit(df)
                st.dataframe(result, use_container_width=True, hide_index=True)
                render_export_buttons(result, base_name="agent_quality")

            elif mission == "Trend & Monotonicity Analysis":
                result = _mission_trend_check(df)
                if result.empty:
                    st.info("Insufficient variance or data points for trend analysis.")
                else:
                    st.dataframe(result, use_container_width=True, hide_index=True)
                    render_export_buttons(result, base_name="agent_trends")

            elif mission == "Executive Report Generation":
                report = _mission_executive_report(df)
                st.code(report, language="markdown")
                st.download_button("⬇️ Download Report (.md)", data=report, file_name="executive_report.md", mime="text/markdown")

def main():
    setup_page("ML & Predictive Studio", "🤖", initial_sidebar_state="expanded")

    hero_card(
        "🤖 Enterprise ML & Predictive Studio",
        "Unified Machine Learning Suite with Automated Preprocessing, Model Tuning, Persistence, and Real-Time Predictions.",
        badge_text="ENTERPRISE STACK",
    )

    df = get_df()

    tabs = st.tabs([
        "🤖 AutoML & Training",
        "🔮 Prediction Engine",
        "⚡ Feature Engineering",
        "🤖 Autonomous Data Agents",
    ])

    with tabs[0]:
        render_automl_tab(df)
    with tabs[1]:
        render_predict_tab(df)
    with tabs[2]:
        render_feature_engineering_tab(df)
    with tabs[3]:
        render_agents_tab()

    render_standard_footer("ML & PREDICTIVE STUDIO")

if __name__ == "__main__":
    main()
