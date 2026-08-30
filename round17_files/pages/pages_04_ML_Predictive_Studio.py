import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
"""
🤖 ML & Predictive Studio — Consolidated Machine Learning Hub (Premium)
AutoML with real hyperparameter tuning, cross-validation, model persistence/export, a prediction
engine that actually uses your trained model (not a throwaway retrain), automated feature
selection, and non-theatrical autonomous agent missions.
"""

import io
import pickle

import numpy as np
import pandas as pd
import scipy.stats as sps
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import get_active_dataframe, set_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_dataset_context_banner,
    render_export_buttons,
)

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
    from sklearn.preprocessing import StandardScaler, LabelEncoder, PolynomialFeatures
    from sklearn.impute import SimpleImputer
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import accuracy_score, r2_score, mean_squared_error, roc_auc_score
    from sklearn.feature_selection import SelectKBest, f_classif, f_regression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


PARAM_GRIDS = {
    "Random Forest": {"n_estimators": [100, 250], "max_depth": [None, 10, 20]},
    "Gradient Boosting": {"n_estimators": [100, 200], "learning_rate": [0.05, 0.1]},
    "Logistic Regression": {"C": [0.1, 1.0, 10.0]},
    "Ridge Regression": {"alpha": [0.1, 1.0, 10.0]},
}


def get_df():
    df = get_active_dataframe()
    if df is None:
        np.random.seed(42)
        return pd.DataFrame({
            "Feature_A": np.random.normal(12.5, 2.1, 200),
            "Feature_B": np.random.normal(8.3, 1.4, 200),
            "Feature_C": np.random.uniform(0.1, 5.0, 200),
            "Category_X": np.random.choice(["Type 1", "Type 2", "Type 3"], 200),
            "Target": np.random.choice([0, 1], p=[0.4, 0.6], size=200),
        })
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
    section_header("🤖 Advanced AutoML & Hyperparameter Studio", "Train, tune, cross-validate, and evaluate multi-algorithm machine learning models — with real hyperparameter search and a persistable trained pipeline.")

    if not SKLEARN_AVAILABLE:
        st.error("⚠️ `scikit-learn` is required for this module.")
        return

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        st.warning("No numeric columns available for machine learning.")
        return

    target = st.selectbox("Select Target Variable", df.columns, key="ml_target")
    features = st.multiselect("Select Feature Predictors", [c for c in df.columns if c != target], default=[c for c in df.columns if c != target][:4], key="ml_features")

    col1, col2, col3 = st.columns(3)
    with col1:
        test_size = st.slider("Test Split (%)", 10, 50, 20, 5, key="ml_test")
    with col2:
        task = st.radio("Task Type", ["Classification", "Regression"], horizontal=True, key="ml_task")
    with col3:
        cv_folds = st.slider("Cross-Validation Folds", 3, 10, 5, key="ml_cv")

    tune = st.checkbox("🔧 Enable Hyperparameter Tuning (GridSearchCV) — slower, more accurate", value=False, key="ml_tune")

    models = _build_model_registry(task)
    selected_models = st.multiselect("Select Algorithms to Evaluate", list(models.keys()), default=list(models.keys()), key="ml_algos")

    if st.button("🚀 Run AutoML & Cross-Validation Suite", type="primary", key="run_ml"):
        if not features:
            st.error("Select at least one feature.")
        elif not selected_models:
            st.error("Select at least one algorithm.")
        elif task == "Regression" and not pd.api.types.is_numeric_dtype(pd.to_numeric(df[target], errors="coerce")):
            st.error(f"🚫 Target `{target}` cannot be interpreted as numeric — choose Classification instead, or pick a numeric target for regression.")
        else:
            with st.spinner("Preprocessing data and executing cross-validation training..."):
                try:
                    X = pd.get_dummies(df[features].copy(), drop_first=True)
                    y = df[target].copy()

                    imputer = SimpleImputer(strategy="median")
                    X_imp = pd.DataFrame(imputer.fit_transform(X), columns=X.columns, index=X.index)

                    label_encoder = None
                    if task == "Classification":
                        if y.dtype == "object" or str(y.dtype) == "category" or y.dtype == "bool":
                            label_encoder = LabelEncoder()
                            y_target = label_encoder.fit_transform(y.astype(str))
                        else:
                            y_target = y.values
                        scoring = "accuracy"
                    else:
                        y_num = pd.to_numeric(y, errors="coerce")
                        valid = y_num.notnull()
                        if valid.sum() < 10:
                            st.error("🚫 Fewer than 10 valid numeric target rows after cleaning — cannot train reliably.")
                            st.stop()
                        X_imp = X_imp.loc[valid]
                        y_target = y_num.loc[valid].values
                        scoring = "r2"

                    X_train, X_test, y_train, y_test = train_test_split(X_imp, y_target, test_size=test_size / 100, random_state=42)
                    scaler = StandardScaler()
                    X_tr = scaler.fit_transform(X_train)
                    X_te = scaler.transform(X_test)

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
                            try:
                                y_proba = model.predict_proba(X_te)[:, 1]
                                auc = roc_auc_score(y_test, y_proba)
                            except Exception:
                                auc = None
                            results.append({
                                "Algorithm": name,
                                "CV Accuracy": f"{cv_mean * 100:.2f}%" + (f" (±{cv_std*100:.2f}%)" if not np.isnan(cv_std) else ""),
                                "Test Accuracy": f"{test_metric * 100:.2f}%",
                                "ROC-AUC": f"{auc:.4f}" if auc is not None else "N/A",
                                "Params": best_params_note,
                            })
                        else:
                            test_metric = r2_score(y_test, y_pred)
                            test_rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                            results.append({
                                "Algorithm": name,
                                "CV R²": f"{cv_mean:.4f}" + (f" (±{cv_std:.4f})" if not np.isnan(cv_std) else ""),
                                "Test R²": f"{test_metric:.4f}",
                                "Test RMSE": f"{test_rmse:.4f}",
                                "Params": best_params_note,
                            })

                        trained_models[name] = model
                        if test_metric > best_score:
                            best_score, best_name, best_model = test_metric, name, model

                    res_df = pd.DataFrame(results)
                    st.markdown("#### 📊 Model Performance Leaderboard")
                    st.dataframe(res_df, width='stretch', hide_index=True)
                    st.success(f"✅ Best performer: **{best_name}** (test score {best_score:.4f}) — this is now the active model for the Prediction Engine tab.")

                    if "Random Forest" in trained_models and hasattr(trained_models["Random Forest"], "feature_importances_"):
                        st.markdown("#### 🔍 Random Forest Feature Importances")
                        importances = pd.Series(trained_models["Random Forest"].feature_importances_, index=X_imp.columns).sort_values(ascending=False)
                        st.bar_chart(importances)

                    st.session_state["ml_active_pipeline"] = {
                        "model": best_model,
                        "scaler": scaler,
                        "features": list(X.columns),
                        "raw_features": features,
                        "task": task,
                        "target": target,
                        "label_encoder": label_encoder,
                        "algorithm": best_name,
                        "test_score": float(best_score),
                        "trained_at": pd.Timestamp.now().isoformat(),
                    }

                except Exception as e:
                    st.error(f"Training error: {e}")

    pipeline = st.session_state.get("ml_active_pipeline")
    if pipeline:
        st.markdown("---")
        st.markdown("#### 💾 Model Persistence")
        c1, c2 = st.columns(2)
        with c1:
            st.caption(f"Active model: **{pipeline['algorithm']}** ({pipeline['task']}, target=`{pipeline['target']}`, test score={pipeline['test_score']:.4f})")
            raw = _serialize_pipeline(pipeline)
            st.download_button("⬇️ Export Trained Pipeline (.pkl)", data=raw, file_name=f"ml_pipeline_{pipeline['algorithm'].lower().replace(' ', '_')}.pkl", mime="application/octet-stream", key="dl_pipeline")
        with c2:
            uploaded_pipeline = st.file_uploader("📤 Import a Previously Exported Pipeline", type=["pkl"], key="upload_pipeline")
            if uploaded_pipeline is not None and st.button("Load Imported Pipeline", key="load_pipeline"):
                try:
                    loaded = _deserialize_pipeline(uploaded_pipeline.getvalue())
                    st.session_state["ml_active_pipeline"] = loaded
                    st.success(f"✅ Loaded pipeline: {loaded.get('algorithm', 'Unknown')} ({loaded.get('task', 'Unknown')})")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not load pipeline: {e}")


def render_predict_tab(df):
    section_header("🔮 Interactive Prediction Engine", "Score new records using the model you actually trained in the AutoML tab — not a disconnected throwaway retrain.")

    if not SKLEARN_AVAILABLE:
        st.error("`scikit-learn` required.")
        return

    pipeline = st.session_state.get("ml_active_pipeline")
    if not pipeline:
        st.warning("⚠️ No trained model yet. Go to **AutoML & Training**, run the suite, and come back — this tab will automatically use the best model from that run.")
        return

    model, scaler = pipeline["model"], pipeline["scaler"]
    feature_cols, raw_features = pipeline["features"], pipeline["raw_features"]
    task, target, label_encoder = pipeline["task"], pipeline["target"], pipeline["label_encoder"]

    st.info(f"Using **{pipeline['algorithm']}** trained for `{target}` ({task}) on {len(raw_features)} input feature(s). Trained: {pipeline['trained_at'][:19]}")

    mode = st.radio("Scoring Mode", ["Single Record", "Batch CSV Upload"], horizontal=True, key="pred_mode")

    def _predict(input_df: pd.DataFrame):
        encoded = pd.get_dummies(input_df[raw_features], drop_first=True)
        encoded = encoded.reindex(columns=feature_cols, fill_value=0)
        scaled = scaler.transform(encoded)
        preds = model.predict(scaled)
        proba, interval = None, None
        if task == "Classification":
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

    if mode == "Single Record":
        st.markdown("#### Enter Predictor Values")
        inputs = {}
        cols = st.columns(min(4, len(raw_features)))
        for i, feat in enumerate(raw_features):
            col = cols[i % len(cols)]
            if pd.api.types.is_numeric_dtype(df[feat]):
                inputs[feat] = col.number_input(feat, value=float(df[feat].mean()), key=f"pred_in_{feat}")
            else:
                options = df[feat].dropna().unique().tolist()
                inputs[feat] = col.selectbox(feat, options, key=f"pred_in_{feat}")

        if st.button("🔮 Generate Prediction", type="primary", key="run_predict"):
            try:
                input_df = pd.DataFrame([inputs])
                preds, proba, interval = _predict(input_df)
                if task == "Classification":
                    st.metric(f"Predicted {target}", str(preds[0]))
                    if proba is not None:
                        classes = label_encoder.classes_ if label_encoder is not None else model.classes_
                        proba_df = pd.DataFrame({"Class": classes, "Probability": proba[0]}).sort_values("Probability", ascending=False)
                        st.dataframe(proba_df, width='stretch', hide_index=True)
                else:
                    st.metric(f"Predicted {target}", f"{preds[0]:.4f}")
                    if interval is not None:
                        st.caption(f"Approx. 90% prediction interval (tree-spread): [{interval[0][0]:.4f}, {interval[1][0]:.4f}]")
            except Exception as e:
                st.error(f"Prediction error: {e}")

    else:
        st.markdown("#### Batch Scoring")
        st.caption(f"Upload a CSV containing at least these columns: {', '.join(raw_features)}")
        batch_file = st.file_uploader("Upload CSV for batch scoring", type=["csv"], key="pred_batch_upload")
        if batch_file is not None and st.button("🔮 Score Batch", type="primary", key="run_batch_predict"):
            try:
                batch_df = pd.read_csv(batch_file)
                missing = [c for c in raw_features if c not in batch_df.columns]
                if missing:
                    st.error(f"🚫 Uploaded file is missing required columns: {', '.join(missing)}")
                else:
                    preds, proba, interval = _predict(batch_df)
                    out = batch_df.copy()
                    out[f"Predicted_{target}"] = preds
                    if interval is not None:
                        out["Interval_Low_90"], out["Interval_High_90"] = interval[0], interval[1]
                    st.dataframe(out, width='stretch')
                    render_export_buttons(out, base_name="batch_predictions")
            except Exception as e:
                st.error(f"Batch scoring error: {e}")


def render_feature_engineering_tab(df):
    section_header("⚡ Advanced Feature Engineering Studio", "Engineer high-value mathematical, polynomial, interaction, and binned features.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    tab_interact, tab_bin, tab_poly, tab_select = st.tabs([
        "✖️ Interactions", "📦 Binning & Quantiles", "📈 Polynomials", "🎯 Automated Feature Selection"
    ])

    with tab_interact:
        if len(numeric_cols) >= 2:
            f1 = st.selectbox("Feature 1", numeric_cols, key="fe_f1")
            f2 = st.selectbox("Feature 2", [c for c in numeric_cols if c != f1], key="fe_f2")
            op = st.selectbox("Operation", ["Multiply (X * Y)", "Divide (X / Y)", "Difference (X - Y)", "Sum (X + Y)"], key="fe_op")

            if st.button("➕ Create Interaction Feature", type="primary", key="run_fe_interact"):
                working = df.copy()
                if "Multiply" in op:
                    new_col, values = f"{f1}_mul_{f2}", working[f1] * working[f2]
                elif "Divide" in op:
                    new_col, values = f"{f1}_div_{f2}", working[f1] / working[f2].replace(0, np.nan)
                elif "Difference" in op:
                    new_col, values = f"{f1}_sub_{f2}", working[f1] - working[f2]
                else:
                    new_col, values = f"{f1}_add_{f2}", working[f1] + working[f2]

                working[new_col] = values
                set_active_dataframe(working, st.session_state.get("source_name", "engineered.csv"))
                st.success(f"✅ Created engineered feature '{new_col}' and updated active dataset.")
                st.rerun()
        else:
            st.info("Need at least 2 numeric columns.")

    with tab_bin:
        if numeric_cols:
            col = st.selectbox("Variable to bin", numeric_cols, key="fe_bin_col")
            strategy = st.radio("Binning Strategy", ["Equal Width (Uniform)", "Equal Frequency (Quantiles)"], horizontal=True, key="fe_bin_strat")
            n_bins = st.slider("Number of Bins", 2, 10, 4, key="fe_bin_n")

            if st.button("📦 Create Binned Feature", type="primary", key="run_fe_bin"):
                working = df.copy()
                if "Uniform" in strategy:
                    working[f"{col}_bin"] = pd.cut(working[col], bins=n_bins, labels=[f"Bin_{i+1}" for i in range(n_bins)])
                else:
                    working[f"{col}_bin"] = pd.qcut(working[col], q=n_bins, labels=[f"Q_{i+1}" for i in range(n_bins)], duplicates="drop")
                set_active_dataframe(working, st.session_state.get("source_name", "binned.csv"))
                st.success(f"✅ Binned '{col}' into {n_bins} categories.")
                st.rerun()
        else:
            st.info("No numeric columns available.")

    with tab_poly:
        if numeric_cols:
            mode = st.radio("Mode", ["Single Column Powers", "Multi-Column Polynomial + Interactions (sklearn)"], key="fe_poly_mode")
            if mode == "Single Column Powers":
                col = st.selectbox("Variable for polynomial generation", numeric_cols, key="fe_poly_col")
                degree = st.slider("Maximum Degree", 2, 4, 2, key="fe_poly_deg")
                if st.button("📈 Generate Polynomial Features", type="primary", key="run_fe_poly"):
                    working = df.copy()
                    for d in range(2, degree + 1):
                        working[f"{col}_pow{d}"] = working[col] ** d
                    set_active_dataframe(working, st.session_state.get("source_name", "polynomial.csv"))
                    st.success(f"✅ Created polynomial features up to degree {degree}.")
                    st.rerun()
            else:
                if not SKLEARN_AVAILABLE:
                    st.error("`scikit-learn` required for multi-column polynomial expansion.")
                else:
                    cols_sel = st.multiselect("Select columns to expand", numeric_cols, default=numeric_cols[:2], key="fe_poly_cols")
                    degree = st.slider("Degree", 2, 3, 2, key="fe_poly_multi_deg")
                    if len(cols_sel) >= 2 and st.button("📈 Generate Polynomial + Interaction Set", type="primary", key="run_fe_poly_multi"):
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
                        st.success(f"✅ Added {len(new_names)} polynomial/interaction terms: {', '.join(new_names[:8])}{'…' if len(new_names) > 8 else ''}")
                        st.rerun()
        else:
            st.info("No numeric columns available.")

    with tab_select:
        st.markdown("#### Automated, Task-Aware Feature Selection (SelectKBest)")
        if len(df.columns) >= 3:
            target_col = st.selectbox("Target variable for selection", df.columns, key="fs_target")
            is_classification = not pd.api.types.is_numeric_dtype(df[target_col]) or df[target_col].nunique() <= 10
            st.caption(f"Auto-detected task: **{'Classification (f_classif)' if is_classification else 'Regression (f_regression)'}** based on target type/cardinality.")

            features_pool = [c for c in numeric_cols if c != target_col]
            if not features_pool:
                st.info("Need numeric candidate features.")
            else:
                k_val = st.slider("Select top K features", 1, min(len(features_pool), 10), min(len(features_pool), 3), key="fs_k")

                if st.button("🎯 Run Feature Selection", type="primary", key="run_fs"):
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
                    scores = pd.Series(selector.scores_, index=features_pool).sort_values(ascending=False)

                    st.markdown("#### 📊 Feature F-Scores")
                    st.bar_chart(scores)
                    top_feats = scores.head(k_val).index.tolist()
                    st.success(f"✅ Top {k_val} recommended features: {', '.join(top_feats)}")
        else:
            st.info("Need at least 3 columns for feature selection.")


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
        "Duplicate Rows (dataset-wide)": [int(df.duplicated().sum())] * len(df.columns),
    })


def _mission_trend_check(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    rows = []
    x = np.arange(len(df))
    for c in numeric_cols:
        y = df[c].values
        mask = ~pd.isnull(y)
        if mask.sum() < 5:
            continue
        slope, intercept, r, p, se = sps.linregress(x[mask], y[mask])
        state = "Degrading" if (slope < 0 and p < 0.05) else ("Improving" if (slope > 0 and p < 0.05) else "Stable")
        rows.append({"Column": c, "Trend Slope": round(slope, 5), "P-Value": round(p, 5), "Assessment": state})
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _mission_executive_report(df: pd.DataFrame) -> str:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    lines = [
        "# AUTOMATED EXECUTIVE DATA REPORT",
        f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"- Rows: {df.shape[0]:,} | Columns: {df.shape[1]}",
        f"- Missing cells: {int(df.isnull().sum().sum()):,}",
        f"- Duplicate rows: {int(df.duplicated().sum()):,}",
    ]
    if numeric_cols:
        lines.append("\n## Numeric Column Summary")
        lines.append(df[numeric_cols].describe().T.round(3).to_string())
        if len(numeric_cols) >= 2:
            corr = df[numeric_cols].corr().abs()
            upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
            stacked = upper.stack()
            if not stacked.empty:
                top_pair = stacked.idxmax()
                lines.append(f"\n## Strongest Correlation\n`{top_pair[0]}` ↔ `{top_pair[1]}`: r = {stacked.max():.3f}")
    return "\n".join(lines)


def _mission_pipeline_sync(df: pd.DataFrame) -> dict:
    import hashlib
    fp = hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()
    recorded = st.session_state.get("dataset_schema_meta", {}).get("fingerprint")
    return {"current_fingerprint": fp, "data_studio_fingerprint": recorded, "consistent": recorded is None or recorded == fp}


def render_agents_tab():
    section_header("🦾 Autonomous Agent Console", "Each mission actually inspects the active dataset — no simulated delays, no canned success messages.")

    df = get_active_dataframe()
    if df is None:
        st.warning("⚠️ No active dataset. Load one in Data Studio first — these missions need real data to inspect.")
        return

    mission = st.selectbox("Select Agent Mission", [
        "Anomaly Detection & Outlier Sweep",
        "Data Quality & Missingness Audit",
        "Trend Degradation Check",
        "Automated Executive Reporting Generator",
        "Cross-Hub Data Pipeline Consistency Check",
    ], key="agent_mission")

    if st.button("🚀 Run Agent Mission", type="primary", key="deploy_agent"):
        with st.spinner(f"Running: {mission}..."):
            if mission == "Anomaly Detection & Outlier Sweep":
                result = _mission_outlier_sweep(df)
                if result.empty:
                    st.info("No numeric columns to scan.")
                else:
                    st.dataframe(result, width='stretch', hide_index=True)
                    total = int(result["Outliers Found"].sum())
                    st.success(f"✅ Mission complete — {total:,} outlier values found across {len(result)} numeric columns.")
                    render_export_buttons(result, base_name="agent_outlier_sweep")

            elif mission == "Data Quality & Missingness Audit":
                result = _mission_quality_audit(df)
                st.dataframe(result, width='stretch', hide_index=True)
                st.success("✅ Mission complete.")
                render_export_buttons(result, base_name="agent_quality_audit")

            elif mission == "Trend Degradation Check":
                result = _mission_trend_check(df)
                if result.empty:
                    st.info("Not enough numeric data (need 5+ non-null points per column) to assess trends.")
                else:
                    st.dataframe(result, width='stretch', hide_index=True)
                    degrading = result[result["Assessment"] == "Degrading"]
                    if len(degrading):
                        st.warning(f"⚠️ {len(degrading)} column(s) show a statistically significant downward trend over row order: {', '.join(degrading['Column'])}")
                    else:
                        st.success("✅ No statistically significant degrading trends detected.")
                    render_export_buttons(result, base_name="agent_trend_check")

            elif mission == "Automated Executive Reporting Generator":
                report = _mission_executive_report(df)
                st.code(report, language="markdown")
                st.download_button("⬇️ Download Executive Report (.md)", data=report, file_name="agent_executive_report.md", mime="text/markdown", key="dl_agent_report")
                st.success("✅ Mission complete.")

            else:
                result = _mission_pipeline_sync(df)
                if result["data_studio_fingerprint"] is None:
                    st.info("No fingerprint recorded by Data Studio yet this session — nothing to compare against. Current dataset fingerprint: " + result["current_fingerprint"][:24] + "…")
                elif result["consistent"]:
                    st.success(f"✅ Consistent — this dataset matches the fingerprint Data Studio last recorded ({result['current_fingerprint'][:24]}…).")
                else:
                    st.error(f"🚨 Inconsistent — the active dataset has changed since Data Studio last recorded a fingerprint. Current: {result['current_fingerprint'][:16]}… vs. recorded: {result['data_studio_fingerprint'][:16]}…")


def render_realworld_chaos_tab(df):
    section_header(
        "🌍 Real-World Chaos & Nonlinear Dynamics Detector",
        "Data-driven chaos detection on your actual uploaded data — Rosenstein Lyapunov exponent, "
        "the Gottwald–Melbourne 0-1 Test, Grassberger–Procaccia correlation dimension, sample entropy, "
        "and Huang's Empirical Mode Decomposition / Hilbert Spectral Analysis. Same rigorous math for "
        "any sector — education, healthcare, security, agriculture, engineering, economics, finance, or "
        "anything else. This tab analyzes what you actually uploaded; it does not simulate a toy model."
    )

    try:
        from modules.chaos_detector import (
            analyze_time_series, empirical_mode_decomposition, hilbert_spectrum, recurrence_analysis,
        )
    except ImportError as e:
        st.error(f"Chaos detector module unavailable: {e}")
        return

    import plotly.graph_objects as go

    if df is None or df.empty:
        st.warning("No dataset loaded. Upload data in Data Studio first, or use the quick loader below.")
        uploaded = st.file_uploader("Quick-load a CSV for chaos analysis", type=["csv"], key="rwc_quick_upload")
        if uploaded is not None:
            quick_df = pd.read_csv(uploaded)
            set_active_dataframe(quick_df, uploaded.name)
            st.rerun()
        return

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        st.error("No numeric columns found in the active dataset. This engine needs a numeric time series.")
        return

    with st.expander("⚙️ Analysis Configuration", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            col = st.selectbox("Numeric column to analyze (in row order)", numeric_cols, key="rwc_col")
        with c2:
            sector = st.selectbox(
                "Sector context (labeling only — the math below is identical regardless of choice)",
                ["Generic / Unspecified", "Education", "Healthcare", "Security", "Agriculture",
                 "Engineering", "Economics & Finance", "Other"],
                key="rwc_sector",
            )
        with c3:
            dt_real = st.number_input(
                "Real time step between rows (e.g. 1.0 = daily units, 0.0833 = monthly-in-years). "
                "Only affects the *scale* of the reported Lyapunov exponent, not the chaos/no-chaos call.",
                value=1.0, min_value=1e-6, format="%.4f", key="rwc_dt",
            )
        run = st.button("🔬 Run Full Chaos & Nonlinear Dynamics Analysis", type="primary", key="rwc_run")

    if not run:
        st.info("Configure the column above and click **Run Full Chaos & Nonlinear Dynamics Analysis**.")
        return

    series = df[col].dropna().to_numpy(dtype=float)
    n = len(series)
    st.caption(f"Analyzing **{n} real data point(s)** from column `{col}` "
               f"(sector context: {sector}, dt = {dt_real}).")

    if n < 30:
        st.error(
            f"Only {n} usable data points after dropping missing values — that is too few for any of "
            f"these methods to be meaningful (most need 50-200+ points). Upload a longer series."
        )
        return

    with st.spinner("Running Rosenstein LLE, 0-1 Test, correlation dimension, sample entropy, EMD…"):
        report = analyze_time_series(series, dt=dt_real)

    # --- Verdict banner --------------------------------------------------
    verdict_lower = report.verdict.lower()
    if "all" in verdict_lower and "chaotic" in verdict_lower:
        st.error(f"🌀 **{report.verdict}**")
    elif "all" in verdict_lower and "no evidence" in verdict_lower:
        st.success(f"✅ **{report.verdict}**")
    else:
        st.warning(f"⚠️ **{report.verdict}**")

    if report.warnings:
        with st.expander(f"⚠️ {len(report.warnings)} data-adequacy warning(s) — read before trusting numbers below"):
            for w in report.warnings:
                st.markdown(f"- {w}")

    # --- Headline metrics --------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    lle = report.lyapunov.get("lle")
    m1.metric("Largest Lyapunov Exponent (Rosenstein)", f"{lle:.4f}" if np.isfinite(lle) else "n/a",
               help="Positive = neighboring trajectories diverge exponentially (hallmark of chaos). "
                    "Computed directly from your data, not from a simulated equation.")
    K = report.zero_one.get("K")
    m2.metric("0-1 Test for Chaos (K)", f"{K:.3f}" if np.isfinite(K) else "n/a",
               help="K≈0: regular (periodic/quasi-periodic). K≈1: irregular (chaotic OR stochastic — "
                    "this test alone cannot tell those apart; see correlation dimension for that).")
    se = report.sample_entropy.get("sampen")
    m3.metric("Sample Entropy", f"{se:.4f}" if np.isfinite(se) else "n/a",
               help="Higher = less predictable / more complex. Pure noise scores very high; clean "
                    "periodic signals score near zero; chaos is usually in between.")
    m4.metric("Embedding used", f"m={report.embedding_dim}, τ={report.tau}",
               help="Automatically chosen via False Nearest Neighbors and Average Mutual Information "
                    "— not hand-tuned per dataset.")

    # --- Correlation dimension detail ---------------------------------------
    cd = report.correlation_dim
    with st.expander("📐 Correlation Dimension (Grassberger–Procaccia) — is the attractor low-dimensional?"):
        st.caption(cd.get("note", ""))
        d2_by_dim = cd.get("d2_by_dim", {})
        if d2_by_dim:
            dims = list(d2_by_dim.keys())
            vals = list(d2_by_dim.values())
            fig = go.Figure(data=[go.Scatter(x=dims, y=vals, mode="lines+markers",
                                              line=dict(color="#f472b6", width=3))])
            fig.update_layout(title="Correlation Dimension D2 vs Embedding Dimension",
                               xaxis_title="Embedding dimension", yaxis_title="D2",
                               height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font=dict(color="white"))
            st.plotly_chart(fig, width='stretch')
            st.caption("A flat curve (D2 stops rising) = consistent with a genuine, low-dimensional "
                       "deterministic attractor. A curve that keeps climbing roughly 1-for-1 with "
                       "embedding dimension = consistent with noise or very high-dimensional dynamics. "
                       "This method is notoriously data-hungry — treat it as supporting evidence, not "
                       "a standalone verdict, especially with under ~500 points.")
        else:
            st.info("Not enough data to compute a reliable correlation dimension curve here.")

    # --- Lyapunov divergence curve -----------------------------------------
    with st.expander("📈 Lyapunov Divergence Curve (Rosenstein)"):
        k_axis, mean_log_div = report.lyapunov.get("divergence_curve", (None, None))
        if k_axis is not None:
            fig = go.Figure(data=[go.Scatter(x=k_axis, y=mean_log_div, mode="lines",
                                              line=dict(color="#00f2fe", width=2))])
            fit_region = report.lyapunov.get("fit_region")
            if fit_region:
                fig.add_vrect(x0=fit_region[0], x1=fit_region[1], fillcolor="#00f2fe", opacity=0.15,
                              line_width=0, annotation_text="fit region")
            fig.update_layout(title="Mean Log Divergence of Nearby Trajectories vs Time Step",
                               xaxis_title="Time step (× dt)", yaxis_title="⟨ln divergence⟩",
                               height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font=dict(color="white"))
            st.plotly_chart(fig, width='stretch')
            st.caption("A sustained upward slope early on, followed by flattening once trajectories "
                       "saturate at the attractor's size, is the real signature the Lyapunov exponent "
                       "is measuring. The shaded region shows where the slope was actually fit.")

    # --- EMD / Hilbert spectrum ----------------------------------------------
    with st.expander("🌊 Empirical Mode Decomposition & Hilbert Spectrum (Huang et al., 1998)"):
        st.caption("Decomposes your series into physically meaningful oscillatory modes without "
                   "assuming linearity or stationarity — useful for spotting regime shifts and the "
                   "dominant timescales actually present in the data.")
        emd_res = empirical_mode_decomposition(series)
        imfs = emd_res["imfs"]
        if len(imfs) == 0:
            st.info("No clear intrinsic modes found — the series may already be too smooth or too short.")
        else:
            fig = go.Figure()
            for i, imf in enumerate(imfs[:5]):
                fig.add_trace(go.Scatter(y=imf, mode="lines", name=f"IMF {i+1}"))
            fig.add_trace(go.Scatter(y=emd_res["residual"], mode="lines", name="Residual (trend)",
                                      line=dict(color="white", width=2, dash="dot")))
            fig.update_layout(title=f"{min(5, len(imfs))} of {len(imfs)} Intrinsic Mode Functions + Residual Trend",
                               height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font=dict(color="white"))
            st.plotly_chart(fig, width='stretch')

    # --- Recurrence plot -------------------------------------------------
    with st.expander("🔁 Recurrence Plot (Marwan et al., 2007)"):
        try:
            rqa = recurrence_analysis(series, report.embedding_dim, report.tau)
            r1, r2, r3 = st.columns(3)
            r1.metric("Recurrence rate", f"{rqa['recurrence_rate']*100:.1f}%")
            r2.metric("Determinism", f"{rqa['determinism']*100:.1f}%")
            r3.metric("Avg. diagonal length", f"{rqa['avg_diag_length']:.2f}")
            fig = go.Figure(data=go.Heatmap(z=rqa["RP"], colorscale="Blues", showscale=False))
            fig.update_layout(title="Recurrence Plot", height=420, paper_bgcolor="rgba(0,0,0,0)",
                               plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig, width='stretch')
            st.caption("High determinism with short, broken diagonal lines is a classic visual "
                       "signature of chaos (as opposed to the long unbroken diagonals of periodic "
                       "motion, or the near-absence of structure in pure noise).")
        except Exception as e:
            st.info(f"Recurrence plot unavailable for this series: {e}")

    st.markdown("---")
    st.caption(
        "**Methods, honestly cited:** Rosenstein et al. (1993) largest Lyapunov exponent from data · "
        "Gottwald & Melbourne (2004) 0-1 test for chaos, built on the Li–Yorke definition of chaos "
        "(Li & Yorke, 1975) · Grassberger & Procaccia (1983) correlation dimension · Kennel et al. "
        "(1992) false nearest neighbors · Fraser & Swinney (1986) mutual information · Huang et al. "
        "(1998) empirical mode decomposition & Hilbert spectral analysis · Richman & Moorman (2000) "
        "sample entropy · Marwan et al. (2007) recurrence quantification analysis. **Known honest "
        "limitation:** no method here, alone or combined, can perfectly separate low-dimensional chaos "
        "from high-dimensional stochastic noise on short real-world data — this is an open problem in "
        "nonlinear time series analysis, not a gap specific to this tool. Where the tests disagree, "
        "this page says so instead of forcing a confident-sounding answer."
    )


def render_chaos_tab():
    section_header(
        "⚛️ ODE Simulator (Toy Model — Not Real Data)",
        "A parameter sandbox for exploring generic nonlinear dynamical equations via SciPy's numerical "
        "ODE solvers. Sector labels here only relabel the same underlying generic 3-variable system — "
        "this tab does not analyze your uploaded data. For real, data-driven chaos detection on your "
        "actual dataset, use the 'Real-World Chaos Detector' tab instead.",
    )

    st.markdown(
        "Explore real nonlinear dynamical systems using SciPy's numerical ODE integration solvers. "
        "Test resilience, feedback loops, and early-warning signals across customizable sector parameters."
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
        )
    except ImportError as e:
        st.error(f"Chaos engine module unavailable: {e}")
        return

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    with st.expander("⚙️ Dynamical System Configuration", expanded=True):
        colA, colB = st.columns(2)
        with colA:
            sector_presets = {
                "Generic / Custom System": ("a", "Drive term", "b", "Friction term", "c", "Buffer decay"),
                "Economic Growth & Debt": ("a", "Growth driver", "b", "Investment cost", "c", "Market elasticity"),
                "Healthcare Capacity Burnout": ("a", "Patient influx", "b", "Capacity burnout", "c", "Staff fatigue decay"),
                "Epidemiology SIR/SEIR": ("a", "Transmission rate", "b", "Recovery rate", "c", "Waning immunity"),
                "Critical Infrastructure Grid": ("a", "Demand surge", "b", "Load friction", "c", "Buffer capacity"),
            }
            sector = st.selectbox("Sector Framing Model", list(sector_presets.keys()))
            a_label, a_desc, b_label, b_desc, c_label, c_desc = sector_presets[sector]
        with colB:
            t_max = st.slider("Simulation Horizon (steps)", 50, 400, 200, 10, key="chaos_tmax")
            policy_shock = st.slider("Injected Shock Magnitude (Mid-run)", -3.0, 3.0, 0.0, 0.1, key="chaos_shock")
            pss_slice_z = st.slider("Poincaré Cut Plane (Z)", -3.0, 3.0, 0.1, 0.05, key="chaos_z_plane")

        col1, col2, col3 = st.columns(3)
        a = col1.slider(f"{a_label} ({a_desc})", 0.1, 5.0, 1.5, 0.1, key="chaos_a")
        b = col2.slider(f"{b_label} ({b_desc})", 0.0, 3.0, 0.9, 0.1, key="chaos_b")
        c = col3.slider(f"{c_label} ({c_desc})", 0.0, 3.0, 1.0, 0.1, key="chaos_c")

        col4, col5, col6 = st.columns(3)
        x0 = col4.number_input("Initial x0", value=0.10, format="%.3f", key="chaos_x0")
        y0 = col5.number_input("Initial y0", value=0.10, format="%.3f", key="chaos_y0")
        z0 = col6.number_input("Initial z0", value=0.10, format="%.3f", key="chaos_z0")

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
        "Bifurcation Analysis", "Monte Carlo Ensemble", "Sensitivity Heatmap", "Time-Series Forecasting",
    ])

    with tabs[0]:
        c1, c2 = st.columns(2)
        c1.metric("Expansion-Rate Heuristic (mLCE)", f"{mlce:.4f}")
        c2.metric("Trajectory State Classification", state_label)

        fig = go.Figure(data=[go.Scatter3d(
            x=x_traj, y=y_traj, z=z_traj, mode="lines",
            line=dict(color="#60A5FA", width=4),
            marker=dict(size=2, color=z_traj, colorscale="Viridis", opacity=0.9)
        )])
        fig.update_layout(title_text="3D Phase Portrait Trajectory", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=480, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig, width='stretch')

    with tabs[1]:
        fig = go.Figure(data=[go.Scatter3d(x=x_traj, y=y_traj, z=z_traj, mode="lines", line=dict(color="#60A5FA", width=4))])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=550, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, width='stretch')

    with tabs[2]:
        mask = np.abs(z_traj - pss_slice_z) < 0.05
        fig = go.Figure(data=[go.Scatter(x=x_traj[mask], y=y_traj[mask], mode="markers", marker=dict(size=4, color="#60A5FA"))])
        fig.update_layout(title_text=f"Poincaré Section Slice (Z={pss_slice_z:.2f})", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=450, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig, width='stretch')

    with tabs[3]:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Rolling Variance (Critical Slowing Down)", "Rolling Autocorrelation (Lag-1)"))
        fig.add_trace(go.Scatter(x=t, y=rolling_var, line=dict(color="#F59E0B")), row=1, col=1)
        fig.add_trace(go.Scatter(x=t, y=rolling_ac, line=dict(color="#EC4899")), row=2, col=1)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig, width='stretch')

    with tabs[4]:
        st.caption("Recomputes model trajectories across a parameter sweep of friction (b) to identify bifurcations.")
        if st.button("Run Bifurcation Scan", key="chaos_bif"):
            with st.spinner("Scanning parameter space..."):
                b_pts, peaks = bifurcation_scan(default_ode, initial_state, t, np.linspace(0.2, 2.8, 40), param_idx=1, args_base=(a, b, c, 0.0, t_max))
            fig = go.Figure(data=[go.Scatter(x=b_pts, y=peaks, mode="markers", marker=dict(size=1.5, color="#60A5FA", opacity=0.6))])
            fig.update_layout(title_text="Bifurcation Diagram", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=450, margin=dict(l=0, r=0, t=50, b=0))
            fig.update_xaxes(title_text=f"{b_label} (b)"); fig.update_yaxes(title_text="Local Extrema")
            st.plotly_chart(fig, width='stretch')

    with tabs[5]:
        n_mc = st.slider("Ensemble Run Count", 10, 150, 30, 10, key="chaos_mc_n")
        if st.button("Run Monte Carlo Ensemble", key="chaos_mc"):
            with st.spinner(f"Running {n_mc} perturbed integrations..."):
                mc_runs = monte_carlo_ensemble(default_ode, initial_state, t, (a, b, c, policy_shock, t_max), n_runs=n_mc)
            fig = go.Figure()
            for i in range(mc_runs.shape[1]):
                fig.add_trace(go.Scatter(x=t, y=mc_runs[:, i], mode="lines", line=dict(width=0.8, color="rgba(96,165,250,0.25)"), showlegend=False))
            fig.update_layout(title_text=f"Monte Carlo Uncertainty Envelope ({n_mc} runs)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=450, margin=dict(l=0, r=0, t=50, b=0))
            st.plotly_chart(fig, width='stretch')

    with tabs[6]:
        if st.button("Compute Sensitivity Heatmap (a vs b)", key="chaos_sens"):
            with st.spinner("Computing 2D sensitivity landscape..."):
                a_grid, b_grid, Z_m = sensitivity_heatmap(default_ode, initial_state, t, np.linspace(0.5, 3.0, 12), np.linspace(0.2, 2.0, 12), args_base=(a, b, c, 0.0, t_max))
            fig = go.Figure(data=go.Contour(z=Z_m, x=a_grid, y=b_grid, colorscale="Viridis", contours=dict(coloring="heatmap")))
            fig.update_layout(title_text=f"Sensitivity Landscape: {a_label} vs {b_label}", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500, margin=dict(l=0, r=0, t=50, b=0))
            st.plotly_chart(fig, width='stretch')

    with tabs[7]:
        st.markdown("#### Time-Series Forecasting (Holt-Winters + AR Least-Squares)")
        series_src = st.radio("Series Source", ["Extracted Trajectory", "Active Dataset Column"], horizontal=True, key="chaos_fc_src")
        series = None
        if series_src == "Extracted Trajectory":
            series = x_traj
        else:
            source_df = get_active_dataframe()
            if source_df is not None:
                numeric_cols = source_df.select_dtypes(include=[np.number]).columns.tolist()
                if numeric_cols:
                    col = st.selectbox("Column to Forecast", numeric_cols, key="chaos_fc_col")
                    series = source_df[col].dropna().values
        if series is not None and len(series) >= 4:
            periods = st.slider("Forecast Horizon (periods)", 1, 30, 12, key="chaos_fc_periods")
            fitted_hw, forecast_hw = holt_winters_forecast(series, periods=periods)
            lags = st.slider("AR Lag Order (p)", 1, min(10, max(1, len(series) // 3)), 3, key="chaos_fc_lags")
            fitted_ar, forecast_ar, coeffs = ar_least_squares_forecast(series, lags=lags, periods=periods)
            x_hist = np.arange(len(series))
            x_fore = np.arange(len(series), len(series) + periods)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x_hist, y=series, name="Observed", line=dict(color="#94A3B8", width=2)))
            fig.add_trace(go.Scatter(x=x_hist, y=fitted_hw, name="Holt-Winters Fit", line=dict(color="#38BDF8", width=2, dash="dot")))
            fig.add_trace(go.Scatter(x=x_fore, y=forecast_hw, name="Holt-Winters Forecast", line=dict(color="#38BDF8", width=3)))
            fig.add_trace(go.Scatter(x=x_fore, y=forecast_ar, name=f"AR({lags}) Forecast", line=dict(color="#F472B6", width=3, dash="dash")))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=460, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, width='stretch')
            resid = series[lags:] - fitted_ar
            mae = float(np.mean(np.abs(resid))) if len(resid) else 0.0
            c1, c2 = st.columns(2)
            c1.metric("AR In-Sample MAE", f"{mae:.4f}")
            c2.metric("Series Length", f"{len(series)} pts")
        else:
            st.info("Need at least 4 numeric points to forecast.")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription(hub_id="ml")

    setup_page("ML & Predictive Studio", "🤖", initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "🤖 Enterprise ML & Predictive Studio (Premium)",
        "Consolidated machine learning hub featuring AutoML with real hyperparameter tuning, model persistence and export, a prediction engine connected to your actual trained model, task-aware feature selection, non-theatrical autonomous agents, and real ODE-based chaos dynamics.",
        badge_text="ML & PREDICTIVE STUDIO • PREMIUM TIER",
    )

    render_dataset_context_banner()

    df = get_df()

    tabs = st.tabs([
        "🤖 AutoML & Training",
        "🔮 Prediction Engine",
        "⚡ Feature Engineering",
        "🦾 Autonomous Agents",
        "🌍 Real-World Chaos Detector",
        "⚛️ ODE Simulator (Toy Model)",
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
        render_realworld_chaos_tab(df)
    with tabs[5]:
        render_chaos_tab()

    render_standard_footer("ML & PREDICTIVE STUDIO")


if __name__ == "__main__":
    main()
