import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
"""
🤖 ML & Predictive Studio — Consolidated Enterprise Machine Learning Hub (Advanced Production Edition v2)
Enhanced machine learning platform featuring robust imputation pipelines, grid search cross-validation,
live batch evaluation engines, and automated feature transformation tools.
"""

import io
import pickle
import numpy as np
import pandas as pd
import streamlit as st

# Modular Framework Imports
from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import get_active_dataframe, set_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_dataset_context_banner,
)

# Core ML Initialization
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.impute import SimpleImputer
    from sklearn.decomposition import PCA
    from sklearn.ensemble import (
        RandomForestClassifier,
        RandomForestRegressor,
        GradientBoostingClassifier,
        GradientBoostingRegressor,
    )
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import (
        accuracy_score, 
        r2_score, 
        mean_squared_error, 
        roc_auc_score
    )
    from sklearn.feature_selection import SelectKBest, f_classif, f_regression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

PARAM_GRIDS = {
    "Random Forest": {"n_estimators": [50, 100, 200], "max_depth": [None, 10, 20]},
    "Gradient Boosting": {"n_estimators": [50, 100], "learning_rate": [0.05, 0.1]},
    "Logistic Regression": {"C": [0.1, 1.0, 10.0]},
    "Ridge Regression": {"alpha": [0.1, 1.0, 10.0]},
}

@st.cache_data
def load_synthetic_dataset():
    np.random.seed(42)
    return pd.DataFrame({
        "Feature_A": np.random.normal(12.5, 2.1, 300),
        "Feature_B": np.random.normal(8.3, 1.4, 300),
        "Feature_C": np.random.uniform(0.1, 5.0, 300),
        "Category_X": np.random.choice(["Type A", "Type B", "Type C"], 300),
        "Target": np.random.choice([0, 1], p=[0.45, 0.55], size=300),
    })

def get_df():
    df = get_active_dataframe()
    if df is None:
        df = load_synthetic_dataset()
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

def render_automl_tab(df):
    section_header("🤖 Advanced AutoML & Training Studio", "Configure, train, and validate robust machine learning pipelines with production metrics.")

    if not SKLEARN_AVAILABLE:
        st.error("⚠️ `scikit-learn` is required to run machine learning workflows.")
        return

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        st.warning("No numeric features available for processing.")
        return

    target = st.selectbox("Select Target Variable", df.columns, key="ml_target_v2")
    available_features = [c for c in df.columns if c != target]
    features = st.multiselect("Select Feature Predictors", available_features, default=available_features[:min(4, len(available_features))], key="ml_features_v2")

    col1, col2, col3 = st.columns(3)
    with col1:
        test_size = st.slider("Test Split (%)", 10, 50, 20, 5, key="ml_test_v2")
    with col2:
        task = st.radio("Task Type", ["Classification", "Regression"], horizontal=True, key="ml_task_v2")
    with col3:
        cv_folds = st.slider("Cross-Validation Folds", 3, 10, 5, key="ml_cv_v2")

    tune = st.checkbox("🔧 Enable Hyperparameter Optimization Grid Search", value=False, key="ml_tune_v2")
    apply_pca = st.checkbox("🧬 Apply Dimensionality Reduction (PCA)", value=False, key="ml_pca_v2")
    pca_components = 2
    if apply_pca:
        pca_components = st.slider("PCA Components", 1, min(10, max(1, len(features))), 2, key="ml_pca_comp_v2")

    models = _build_model_registry(task)
    selected_models = st.multiselect("Select Algorithms to Evaluate", list(models.keys()), default=list(models.keys()), key="ml_algos_v2")

    if st.button("🚀 Execute Comprehensive Training Suite", type="primary", key="run_ml_v2"):
        if not features:
            st.error("Please select at least one feature predictor.")
            return
        if not selected_models:
            st.error("Please select at least one algorithm.")
            return

        with st.spinner("Executing data scaling, imputation, and cross-validation pipelines..."):
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

                pca = None
                if apply_pca:
                    pca = PCA(n_components=min(pca_components, X_tr.shape[1]), random_state=42)
                    X_tr = pca.fit_transform(X_tr)
                    X_te = pca.transform(X_te)

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
                        cv_mean = grid.best_score_
                        best_params_note = str(grid.best_params_)
                    else:
                        cv_scores = cross_val_score(base_model, X_tr, y_train, cv=cv_folds, scoring=scoring)
                        cv_mean = cv_scores.mean()
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
                                    auc_str = f"{roc_auc_score(y_test, y_proba[:, 1]):.4f}"
                                else:
                                    auc_str = f"{roc_auc_score(y_test, y_proba, multi_class='ovr'):.4f}"
                            except Exception:
                                pass
                        results.append({
                            "Algorithm": name,
                            "CV Accuracy": f"{cv_mean * 100:.2f}%",
                            "Test Accuracy": f"{test_metric * 100:.2f}%",
                            "ROC-AUC": auc_str,
                            "Hyperparameters": best_params_note,
                        })
                    else:
                        test_metric = r2_score(y_test, y_pred)
                        test_rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                        results.append({
                            "Algorithm": name,
                            "CV R²": f"{cv_mean:.4f}",
                            "Test R²": f"{test_metric:.4f}",
                            "Test RMSE": f"{test_rmse:.4f}",
                            "Hyperparameters": best_params_note,
                        })

                    trained_models[name] = model
                    if test_metric > best_score:
                        best_score, best_name, best_model = test_metric, name, model

                res_df = pd.DataFrame(results)
                st.markdown("#### 📊 Model Performance Evaluation")
                st.dataframe(res_df, use_container_width=True, hide_index=True)
                st.success(f"🏆 Top Performing Model: **{best_name}** (Score: {best_score:.4f})")

                st.session_state["ml_active_pipeline"] = {
                    "model": best_model,
                    "imputer": imputer,
                    "scaler": scaler,
                    "pca": pca,
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
                st.error(f"Pipeline Execution Error: {e}")

    pipeline = st.session_state.get("ml_active_pipeline")
    if pipeline:
        st.markdown("---")
        st.markdown("#### 💾 Export Trained Model Bundle")
        raw_bytes = _serialize_pipeline(pipeline)
        st.download_button(
            "⬇️ Download Model Pipeline (.pkl)",
            data=raw_bytes,
            file_name=f"pipeline_{pipeline['algorithm'].lower().replace(' ', '_')}.pkl",
            mime="application/octet-stream",
        )

def render_predict_tab(df):
    section_header("🔮 Real-Time Inference & Monitoring Hub", "Input parameters dynamically to generate live predictions using the compiled pipeline.")

    pipeline = st.session_state.get("ml_active_pipeline")
    if not pipeline:
        st.warning("⚠️ No active pipeline found. Please train a model in the **AutoML & Training** tab first.")
        return

    model, imputer, scaler, pca = pipeline["model"], pipeline["imputer"], pipeline["scaler"], pipeline["pca"]
    feature_cols, raw_features = pipeline["feature_columns"], pipeline["raw_features"]
    task, target, label_encoder = pipeline["task"], pipeline["target"], pipeline["label_encoder"]

    st.info(f"Active Model: **{pipeline['algorithm']}** | Target Metric: `{target}`")

    inputs = {}
    cols = st.columns(min(3, max(1, len(raw_features))))
    for i, feat in enumerate(raw_features):
        col = cols[i % len(cols)]
        if pd.api.types.is_numeric_dtype(df[feat]):
            inputs[feat] = col.number_input(feat, value=float(df[feat].mean()), key=f"inf_{feat}")
        else:
            options = df[feat].dropna().unique().tolist()
            inputs[feat] = col.selectbox(feat, options if options else ["None"], key=f"inf_{feat}")

    if st.button("🔮 Compute Prediction", type="primary", key="compute_inf"):
        try:
            input_df = pd.DataFrame([inputs])
            encoded = pd.get_dummies(input_df[raw_features], drop_first=True).reindex(columns=feature_cols, fill_value=0)
            imp = imputer.transform(encoded)
            scaled = scaler.transform(imp)
            if pca is not None:
                scaled = pca.transform(scaled)
            preds = model.predict(scaled)
            if task == "Classification" and label_encoder is not None:
                preds = label_encoder.inverse_transform(preds.astype(int))
            st.metric(f"Predicted Output ({target})", str(preds[0]))
        except Exception as e:
            st.error(f"Inference Processing Error: {e}")

def render_feature_engineering_tab(df):
    section_header("⚡ Advanced Feature Engineering", "Perform statistical feature selection and data transformation workflows.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        st.warning("Numeric columns required for feature selection.")
        return

    target_col = st.selectbox("Target Column for Analysis", df.columns, key="FE_target")
    k_val = st.slider("Select Top Features Count", 1, min(len(numeric_cols)-1, 10), min(3, len(numeric_cols)-1), key="FE_k")

    if st.button("Run Statistical Feature Evaluation", type="primary"):
        features_pool = [c for c in numeric_cols if c != target_col]
        if not features_pool:
            st.error("Insufficient features available for evaluation.")
            return
        clean_df = df[features_pool + [target_col]].dropna()
        selector = SelectKBest(score_func=f_classif if df[target_col].nunique() <= 10 else f_regression, k=k_val)
        selector.fit(clean_df[features_pool], clean_df[target_col])
        scores = pd.Series(selector.scores_, index=features_pool).sort_values(ascending=False)
        st.bar_chart(scores)
        st.success(f"Top Recommended Features: {', '.join(scores.head(k_val).index.tolist())}")

def main():
    from modules.subscription import require_active_subscription
    require_active_subscription(hub_id="ml")

    setup_page("ML & Predictive Studio", "🤖", initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "🤖 Enterprise ML & Predictive Studio (Advanced Production Edition v2)",
        "Advanced modular machine learning hub featuring automated preprocessing, hyperparameter optimization, and real-time evaluation engines.",
        badge_text="ENTERPRISE STACK • PROD",
    )

    render_dataset_context_banner()
    df = get_df()

    tabs = st.tabs([
        "🤖 AutoML & Training",
        "🔮 Live Inference",
        "⚡ Feature Engineering",
    ])

    with tabs[0]:
        render_automl_tab(df)
    with tabs[1]:
        render_predict_tab(df)
    with tabs[2]:
        render_feature_engineering_tab(df)

    render_standard_footer("ML & PREDICTIVE STUDIO")

if __name__ == "__main__":
    main()import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
"""
🤖 ML & Predictive Studio — Consolidated Enterprise Machine Learning Hub (Advanced Production Edition v2)
Enhanced machine learning platform featuring robust imputation pipelines, grid search cross-validation,
live batch evaluation engines, and automated feature transformation tools.
"""

import io
import pickle
import numpy as np
import pandas as pd
import streamlit as st

# Modular Framework Imports
from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import get_active_dataframe, set_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_dataset_context_banner,
)

# Core ML Initialization
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.impute import SimpleImputer
    from sklearn.decomposition import PCA
    from sklearn.ensemble import (
        RandomForestClassifier,
        RandomForestRegressor,
        GradientBoostingClassifier,
        GradientBoostingRegressor,
    )
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import (
        accuracy_score, 
        r2_score, 
        mean_squared_error, 
        roc_auc_score
    )
    from sklearn.feature_selection import SelectKBest, f_classif, f_regression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

PARAM_GRIDS = {
    "Random Forest": {"n_estimators": [50, 100, 200], "max_depth": [None, 10, 20]},
    "Gradient Boosting": {"n_estimators": [50, 100], "learning_rate": [0.05, 0.1]},
    "Logistic Regression": {"C": [0.1, 1.0, 10.0]},
    "Ridge Regression": {"alpha": [0.1, 1.0, 10.0]},
}

@st.cache_data
def load_synthetic_dataset():
    np.random.seed(42)
    return pd.DataFrame({
        "Feature_A": np.random.normal(12.5, 2.1, 300),
        "Feature_B": np.random.normal(8.3, 1.4, 300),
        "Feature_C": np.random.uniform(0.1, 5.0, 300),
        "Category_X": np.random.choice(["Type A", "Type B", "Type C"], 300),
        "Target": np.random.choice([0, 1], p=[0.45, 0.55], size=300),
    })

def get_df():
    df = get_active_dataframe()
    if df is None:
        df = load_synthetic_dataset()
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

def render_automl_tab(df):
    section_header("🤖 Advanced AutoML & Training Studio", "Configure, train, and validate robust machine learning pipelines with production metrics.")

    if not SKLEARN_AVAILABLE:
        st.error("⚠️ `scikit-learn` is required to run machine learning workflows.")
        return

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        st.warning("No numeric features available for processing.")
        return

    target = st.selectbox("Select Target Variable", df.columns, key="ml_target_v2")
    available_features = [c for c in df.columns if c != target]
    features = st.multiselect("Select Feature Predictors", available_features, default=available_features[:min(4, len(available_features))], key="ml_features_v2")

    col1, col2, col3 = st.columns(3)
    with col1:
        test_size = st.slider("Test Split (%)", 10, 50, 20, 5, key="ml_test_v2")
    with col2:
        task = st.radio("Task Type", ["Classification", "Regression"], horizontal=True, key="ml_task_v2")
    with col3:
        cv_folds = st.slider("Cross-Validation Folds", 3, 10, 5, key="ml_cv_v2")

    tune = st.checkbox("🔧 Enable Hyperparameter Optimization Grid Search", value=False, key="ml_tune_v2")
    apply_pca = st.checkbox("🧬 Apply Dimensionality Reduction (PCA)", value=False, key="ml_pca_v2")
    pca_components = 2
    if apply_pca:
        pca_components = st.slider("PCA Components", 1, min(10, max(1, len(features))), 2, key="ml_pca_comp_v2")

    models = _build_model_registry(task)
    selected_models = st.multiselect("Select Algorithms to Evaluate", list(models.keys()), default=list(models.keys()), key="ml_algos_v2")

    if st.button("🚀 Execute Comprehensive Training Suite", type="primary", key="run_ml_v2"):
        if not features:
            st.error("Please select at least one feature predictor.")
            return
        if not selected_models:
            st.error("Please select at least one algorithm.")
            return

        with st.spinner("Executing data scaling, imputation, and cross-validation pipelines..."):
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

                pca = None
                if apply_pca:
                    pca = PCA(n_components=min(pca_components, X_tr.shape[1]), random_state=42)
                    X_tr = pca.fit_transform(X_tr)
                    X_te = pca.transform(X_te)

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
                        cv_mean = grid.best_score_
                        best_params_note = str(grid.best_params_)
                    else:
                        cv_scores = cross_val_score(base_model, X_tr, y_train, cv=cv_folds, scoring=scoring)
                        cv_mean = cv_scores.mean()
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
                                    auc_str = f"{roc_auc_score(y_test, y_proba[:, 1]):.4f}"
                                else:
                                    auc_str = f"{roc_auc_score(y_test, y_proba, multi_class='ovr'):.4f}"
                            except Exception:
                                pass
                        results.append({
                            "Algorithm": name,
                            "CV Accuracy": f"{cv_mean * 100:.2f}%",
                            "Test Accuracy": f"{test_metric * 100:.2f}%",
                            "ROC-AUC": auc_str,
                            "Hyperparameters": best_params_note,
                        })
                    else:
                        test_metric = r2_score(y_test, y_pred)
                        test_rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                        results.append({
                            "Algorithm": name,
                            "CV R²": f"{cv_mean:.4f}",
                            "Test R²": f"{test_metric:.4f}",
                            "Test RMSE": f"{test_rmse:.4f}",
                            "Hyperparameters": best_params_note,
                        })

                    trained_models[name] = model
                    if test_metric > best_score:
                        best_score, best_name, best_model = test_metric, name, model

                res_df = pd.DataFrame(results)
                st.markdown("#### 📊 Model Performance Evaluation")
                st.dataframe(res_df, use_container_width=True, hide_index=True)
                st.success(f"🏆 Top Performing Model: **{best_name}** (Score: {best_score:.4f})")

                st.session_state["ml_active_pipeline"] = {
                    "model": best_model,
                    "imputer": imputer,
                    "scaler": scaler,
                    "pca": pca,
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
                st.error(f"Pipeline Execution Error: {e}")

    pipeline = st.session_state.get("ml_active_pipeline")
    if pipeline:
        st.markdown("---")
        st.markdown("#### 💾 Export Trained Model Bundle")
        raw_bytes = _serialize_pipeline(pipeline)
        st.download_button(
            "⬇️ Download Model Pipeline (.pkl)",
            data=raw_bytes,
            file_name=f"pipeline_{pipeline['algorithm'].lower().replace(' ', '_')}.pkl",
            mime="application/octet-stream",
        )

def render_predict_tab(df):
    section_header("🔮 Real-Time Inference & Monitoring Hub", "Input parameters dynamically to generate live predictions using the compiled pipeline.")

    pipeline = st.session_state.get("ml_active_pipeline")
    if not pipeline:
        st.warning("⚠️ No active pipeline found. Please train a model in the **AutoML & Training** tab first.")
        return

    model, imputer, scaler, pca = pipeline["model"], pipeline["imputer"], pipeline["scaler"], pipeline["pca"]
    feature_cols, raw_features = pipeline["feature_columns"], pipeline["raw_features"]
    task, target, label_encoder = pipeline["task"], pipeline["target"], pipeline["label_encoder"]

    st.info(f"Active Model: **{pipeline['algorithm']}** | Target Metric: `{target}`")

    inputs = {}
    cols = st.columns(min(3, max(1, len(raw_features))))
    for i, feat in enumerate(raw_features):
        col = cols[i % len(cols)]
        if pd.api.types.is_numeric_dtype(df[feat]):
            inputs[feat] = col.number_input(feat, value=float(df[feat].mean()), key=f"inf_{feat}")
        else:
            options = df[feat].dropna().unique().tolist()
            inputs[feat] = col.selectbox(feat, options if options else ["None"], key=f"inf_{feat}")

    if st.button("🔮 Compute Prediction", type="primary", key="compute_inf"):
        try:
            input_df = pd.DataFrame([inputs])
            encoded = pd.get_dummies(input_df[raw_features], drop_first=True).reindex(columns=feature_cols, fill_value=0)
            imp = imputer.transform(encoded)
            scaled = scaler.transform(imp)
            if pca is not None:
                scaled = pca.transform(scaled)
            preds = model.predict(scaled)
            if task == "Classification" and label_encoder is not None:
                preds = label_encoder.inverse_transform(preds.astype(int))
            st.metric(f"Predicted Output ({target})", str(preds[0]))
        except Exception as e:
            st.error(f"Inference Processing Error: {e}")

def render_feature_engineering_tab(df):
    section_header("⚡ Advanced Feature Engineering", "Perform statistical feature selection and data transformation workflows.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        st.warning("Numeric columns required for feature selection.")
        return

    target_col = st.selectbox("Target Column for Analysis", df.columns, key="FE_target")
    k_val = st.slider("Select Top Features Count", 1, min(len(numeric_cols)-1, 10), min(3, len(numeric_cols)-1), key="FE_k")

    if st.button("Run Statistical Feature Evaluation", type="primary"):
        features_pool = [c for c in numeric_cols if c != target_col]
        if not features_pool:
            st.error("Insufficient features available for evaluation.")
            return
        clean_df = df[features_pool + [target_col]].dropna()
        selector = SelectKBest(score_func=f_classif if df[target_col].nunique() <= 10 else f_regression, k=k_val)
        selector.fit(clean_df[features_pool], clean_df[target_col])
        scores = pd.Series(selector.scores_, index=features_pool).sort_values(ascending=False)
        st.bar_chart(scores)
        st.success(f"Top Recommended Features: {', '.join(scores.head(k_val).index.tolist())}")

def main():
    from modules.subscription import require_active_subscription
    require_active_subscription(hub_id="ml")

    setup_page("ML & Predictive Studio", "🤖", initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "🤖 Enterprise ML & Predictive Studio (Advanced Production Edition v2)",
        "Advanced modular machine learning hub featuring automated preprocessing, hyperparameter optimization, and real-time evaluation engines.",
        badge_text="ENTERPRISE STACK • PROD",
    )

    render_dataset_context_banner()
    df = get_df()

    tabs = st.tabs([
        "🤖 AutoML & Training",
        "🔮 Live Inference",
        "⚡ Feature Engineering",
    ])

    with tabs[0]:
        render_automl_tab(df)
    with tabs[1]:
        render_predict_tab(df)
    with tabs[2]:
        render_feature_engineering_tab(df)

    render_standard_footer("ML & PREDICTIVE STUDIO")

if __name__ == "__main__":
    main()import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
"""
🤖 ML & Predictive Studio — Consolidated Enterprise Machine Learning Hub (Advanced Production Edition v2)
Enhanced machine learning platform featuring robust imputation pipelines, grid search cross-validation,
live batch evaluation engines, and automated feature transformation tools.
"""

import io
import pickle
import numpy as np
import pandas as pd
import streamlit as st

# Modular Framework Imports
from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import get_active_dataframe, set_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_dataset_context_banner,
)

# Core ML Initialization
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.impute import SimpleImputer
    from sklearn.decomposition import PCA
    from sklearn.ensemble import (
        RandomForestClassifier,
        RandomForestRegressor,
        GradientBoostingClassifier,
        GradientBoostingRegressor,
    )
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import (
        accuracy_score, 
        r2_score, 
        mean_squared_error, 
        roc_auc_score
    )
    from sklearn.feature_selection import SelectKBest, f_classif, f_regression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

PARAM_GRIDS = {
    "Random Forest": {"n_estimators": [50, 100, 200], "max_depth": [None, 10, 20]},
    "Gradient Boosting": {"n_estimators": [50, 100], "learning_rate": [0.05, 0.1]},
    "Logistic Regression": {"C": [0.1, 1.0, 10.0]},
    "Ridge Regression": {"alpha": [0.1, 1.0, 10.0]},
}

@st.cache_data
def load_synthetic_dataset():
    np.random.seed(42)
    return pd.DataFrame({
        "Feature_A": np.random.normal(12.5, 2.1, 300),
        "Feature_B": np.random.normal(8.3, 1.4, 300),
        "Feature_C": np.random.uniform(0.1, 5.0, 300),
        "Category_X": np.random.choice(["Type A", "Type B", "Type C"], 300),
        "Target": np.random.choice([0, 1], p=[0.45, 0.55], size=300),
    })

def get_df():
    df = get_active_dataframe()
    if df is None:
        df = load_synthetic_dataset()
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

def render_automl_tab(df):
    section_header("🤖 Advanced AutoML & Training Studio", "Configure, train, and validate robust machine learning pipelines with production metrics.")

    if not SKLEARN_AVAILABLE:
        st.error("⚠️ `scikit-learn` is required to run machine learning workflows.")
        return

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        st.warning("No numeric features available for processing.")
        return

    target = st.selectbox("Select Target Variable", df.columns, key="ml_target_v2")
    available_features = [c for c in df.columns if c != target]
    features = st.multiselect("Select Feature Predictors", available_features, default=available_features[:min(4, len(available_features))], key="ml_features_v2")

    col1, col2, col3 = st.columns(3)
    with col1:
        test_size = st.slider("Test Split (%)", 10, 50, 20, 5, key="ml_test_v2")
    with col2:
        task = st.radio("Task Type", ["Classification", "Regression"], horizontal=True, key="ml_task_v2")
    with col3:
        cv_folds = st.slider("Cross-Validation Folds", 3, 10, 5, key="ml_cv_v2")

    tune = st.checkbox("🔧 Enable Hyperparameter Optimization Grid Search", value=False, key="ml_tune_v2")
    apply_pca = st.checkbox("🧬 Apply Dimensionality Reduction (PCA)", value=False, key="ml_pca_v2")
    pca_components = 2
    if apply_pca:
        pca_components = st.slider("PCA Components", 1, min(10, max(1, len(features))), 2, key="ml_pca_comp_v2")

    models = _build_model_registry(task)
    selected_models = st.multiselect("Select Algorithms to Evaluate", list(models.keys()), default=list(models.keys()), key="ml_algos_v2")

    if st.button("🚀 Execute Comprehensive Training Suite", type="primary", key="run_ml_v2"):
        if not features:
            st.error("Please select at least one feature predictor.")
            return
        if not selected_models:
            st.error("Please select at least one algorithm.")
            return

        with st.spinner("Executing data scaling, imputation, and cross-validation pipelines..."):
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

                pca = None
                if apply_pca:
                    pca = PCA(n_components=min(pca_components, X_tr.shape[1]), random_state=42)
                    X_tr = pca.fit_transform(X_tr)
                    X_te = pca.transform(X_te)

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
                        cv_mean = grid.best_score_
                        best_params_note = str(grid.best_params_)
                    else:
                        cv_scores = cross_val_score(base_model, X_tr, y_train, cv=cv_folds, scoring=scoring)
                        cv_mean = cv_scores.mean()
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
                                    auc_str = f"{roc_auc_score(y_test, y_proba[:, 1]):.4f}"
                                else:
                                    auc_str = f"{roc_auc_score(y_test, y_proba, multi_class='ovr'):.4f}"
                            except Exception:
                                pass
                        results.append({
                            "Algorithm": name,
                            "CV Accuracy": f"{cv_mean * 100:.2f}%",
                            "Test Accuracy": f"{test_metric * 100:.2f}%",
                            "ROC-AUC": auc_str,
                            "Hyperparameters": best_params_note,
                        })
                    else:
                        test_metric = r2_score(y_test, y_pred)
                        test_rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                        results.append({
                            "Algorithm": name,
                            "CV R²": f"{cv_mean:.4f}",
                            "Test R²": f"{test_metric:.4f}",
                            "Test RMSE": f"{test_rmse:.4f}",
                            "Hyperparameters": best_params_note,
                        })

                    trained_models[name] = model
                    if test_metric > best_score:
                        best_score, best_name, best_model = test_metric, name, model

                res_df = pd.DataFrame(results)
                st.markdown("#### 📊 Model Performance Evaluation")
                st.dataframe(res_df, use_container_width=True, hide_index=True)
                st.success(f"🏆 Top Performing Model: **{best_name}** (Score: {best_score:.4f})")

                st.session_state["ml_active_pipeline"] = {
                    "model": best_model,
                    "imputer": imputer,
                    "scaler": scaler,
                    "pca": pca,
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
                st.error(f"Pipeline Execution Error: {e}")

    pipeline = st.session_state.get("ml_active_pipeline")
    if pipeline:
        st.markdown("---")
        st.markdown("#### 💾 Export Trained Model Bundle")
        raw_bytes = _serialize_pipeline(pipeline)
        st.download_button(
            "⬇️ Download Model Pipeline (.pkl)",
            data=raw_bytes,
            file_name=f"pipeline_{pipeline['algorithm'].lower().replace(' ', '_')}.pkl",
            mime="application/octet-stream",
        )

def render_predict_tab(df):
    section_header("🔮 Real-Time Inference & Monitoring Hub", "Input parameters dynamically to generate live predictions using the compiled pipeline.")

    pipeline = st.session_state.get("ml_active_pipeline")
    if not pipeline:
        st.warning("⚠️ No active pipeline found. Please train a model in the **AutoML & Training** tab first.")
        return

    model, imputer, scaler, pca = pipeline["model"], pipeline["imputer"], pipeline["scaler"], pipeline["pca"]
    feature_cols, raw_features = pipeline["feature_columns"], pipeline["raw_features"]
    task, target, label_encoder = pipeline["task"], pipeline["target"], pipeline["label_encoder"]

    st.info(f"Active Model: **{pipeline['algorithm']}** | Target Metric: `{target}`")

    inputs = {}
    cols = st.columns(min(3, max(1, len(raw_features))))
    for i, feat in enumerate(raw_features):
        col = cols[i % len(cols)]
        if pd.api.types.is_numeric_dtype(df[feat]):
            inputs[feat] = col.number_input(feat, value=float(df[feat].mean()), key=f"inf_{feat}")
        else:
            options = df[feat].dropna().unique().tolist()
            inputs[feat] = col.selectbox(feat, options if options else ["None"], key=f"inf_{feat}")

    if st.button("🔮 Compute Prediction", type="primary", key="compute_inf"):
        try:
            input_df = pd.DataFrame([inputs])
            encoded = pd.get_dummies(input_df[raw_features], drop_first=True).reindex(columns=feature_cols, fill_value=0)
            imp = imputer.transform(encoded)
            scaled = scaler.transform(imp)
            if pca is not None:
                scaled = pca.transform(scaled)
            preds = model.predict(scaled)
            if task == "Classification" and label_encoder is not None:
                preds = label_encoder.inverse_transform(preds.astype(int))
            st.metric(f"Predicted Output ({target})", str(preds[0]))
        except Exception as e:
            st.error(f"Inference Processing Error: {e}")

def render_feature_engineering_tab(df):
    section_header("⚡ Advanced Feature Engineering", "Perform statistical feature selection and data transformation workflows.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        st.warning("Numeric columns required for feature selection.")
        return

    target_col = st.selectbox("Target Column for Analysis", df.columns, key="FE_target")
    k_val = st.slider("Select Top Features Count", 1, min(len(numeric_cols)-1, 10), min(3, len(numeric_cols)-1), key="FE_k")

    if st.button("Run Statistical Feature Evaluation", type="primary"):
        features_pool = [c for c in numeric_cols if c != target_col]
        if not features_pool:
            st.error("Insufficient features available for evaluation.")
            return
        clean_df = df[features_pool + [target_col]].dropna()
        selector = SelectKBest(score_func=f_classif if df[target_col].nunique() <= 10 else f_regression, k=k_val)
        selector.fit(clean_df[features_pool], clean_df[target_col])
        scores = pd.Series(selector.scores_, index=features_pool).sort_values(ascending=False)
        st.bar_chart(scores)
        st.success(f"Top Recommended Features: {', '.join(scores.head(k_val).index.tolist())}")

def main():
    from modules.subscription import require_active_subscription
    require_active_subscription(hub_id="ml")

    setup_page("ML & Predictive Studio", "🤖", initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "🤖 Enterprise ML & Predictive Studio (Advanced Production Edition v2)",
        "Advanced modular machine learning hub featuring automated preprocessing, hyperparameter optimization, and real-time evaluation engines.",
        badge_text="ENTERPRISE STACK • PROD",
    )

    render_dataset_context_banner()
    df = get_df()

    tabs = st.tabs([
        "🤖 AutoML & Training",
        "🔮 Live Inference",
        "⚡ Feature Engineering",
    ])

    with tabs[0]:
        render_automl_tab(df)
    with tabs[1]:
        render_predict_tab(df)
    with tabs[2]:
        render_feature_engineering_tab(df)

    render_standard_footer("ML & PREDICTIVE STUDIO")

if __name__ == "__main__":
    main()