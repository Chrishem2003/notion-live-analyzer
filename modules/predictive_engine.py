# --- CHRISHEM AUTHOR PROFILE BLOCK ---
import os
import streamlit as st

st.markdown("# **Notion Live Analyzer**")
st.markdown("### **Creator: CHRISHEM**")
st.markdown("---")
# -------------------------------------

"""
Predictive Engine â€” AutoML for classification, regression, clustering, and time series forecasting.
Provides automated model selection, training, evaluation, and prediction.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
import warnings
import io
import base64
import json

from modules.pandas_compat import is_text_dtype, text_columns

warnings.filterwarnings('ignore')

# â”€â”€â”€ scikit-learn imports â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
try:
    from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.metrics import accuracy_score, mean_squared_error, classification_report
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    train_test_split = cross_val_score = GridSearchCV = None
    RandomForestClassifier = RandomForestRegressor = None
    accuracy_score = mean_squared_error = classification_report = None
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    mean_squared_error, mean_absolute_error, r2_score, confusion_matrix,
    classification_report, silhouette_score
)

# â”€â”€â”€ Models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Classification
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

# Regression
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.svm import SVR

# Clustering
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.decomposition import PCA

# Time Series (fallback if prophet not available)
try:
    from prophet import Prophet
    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False


class PredictiveEngine:
    """Automated machine learning engine for research."""

    def __init__(self):
        self.model = None
        self.preprocessor = None
        self.label_encoders = {}
        self.feature_names = []
        self.target_name = None
        self.model_type = None
        self.results = {}
        self.is_trained = False

    # â”€â”€â”€ Classification Models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def get_classification_models(self) -> Dict[str, Any]:
        """Return available classification models with hyperparameters."""
        models = {
            "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
            "Decision Tree": DecisionTreeClassifier(random_state=42),
            "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
            "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, random_state=42),
            "SVM (RBF)": SVC(kernel='rbf', probability=True, random_state=42),
            "K-Nearest Neighbors": KNeighborsClassifier(n_neighbors=5),
            "Naive Bayes": GaussianNB(),
        }
        if HAS_XGB:
            models["XGBoost"] = XGBClassifier(n_estimators=100, random_state=42, verbosity=0)
        return models

    def get_regression_models(self) -> Dict[str, Any]:
        """Return available regression models."""
        return {
            "Linear Regression": LinearRegression(),
            "Ridge Regression": Ridge(alpha=1.0, random_state=42),
            "Lasso Regression": Lasso(alpha=1.0, random_state=42),
            "Elastic Net": ElasticNet(alpha=1.0, l1_ratio=0.5, random_state=42),
            "Decision Tree Regressor": DecisionTreeRegressor(random_state=42),
            "Random Forest Regressor": RandomForestRegressor(n_estimators=100, random_state=42),
            "Gradient Boosting Regressor": GradientBoostingRegressor(n_estimators=100, random_state=42),
            "SVM Regressor (RBF)": SVR(kernel='rbf'),
        }

    def get_clustering_models(self) -> Dict[str, Any]:
        """Return available clustering algorithms."""
        return {
            "K-Means": KMeans(n_clusters=3, random_state=42, n_init=10),
            "DBSCAN": DBSCAN(eps=0.5, min_samples=5),
            "Hierarchical (Agglomerative)": AgglomerativeClustering(n_clusters=3),
        }

    # â”€â”€â”€ Data Preparation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def prepare_data(
        self,
        df: pd.DataFrame,
        target_col: str,
        feature_cols: Optional[List[str]] = None,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Tuple:
        """Prepare data for modeling by splitting features and target."""
        if feature_cols is None:
            # Auto-select numeric features (exclude target)
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            feature_cols = [c for c in numeric_cols if c != target_col]

        if not feature_cols:
            raise ValueError("No feature columns available")

        self.feature_names = feature_cols
        self.target_name = target_col

        X = df[feature_cols].copy()
        y = df[target_col].copy()

        # Handle missing values
        imputer = SimpleImputer(strategy='median')
        X = pd.DataFrame(imputer.fit_transform(X), columns=feature_cols)

        # Handle categorical target
        if is_text_dtype(y) or y.dtype.name == 'category':
            le = LabelEncoder()
            y = le.fit_transform(y)
            self.label_encoders['target'] = le
            self.model_type = 'classification'
        else:
            self.model_type = 'regression' if y.nunique() > 10 else 'classification'

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y if self.model_type == 'classification' else None
        )

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        self.preprocessor = scaler

        return X_train_scaled, X_test_scaled, y_train, y_test, X.columns.tolist()

    # â”€â”€â”€ Auto-Classification â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def auto_classify(
        self,
        df: pd.DataFrame,
        target_col: str,
        feature_cols: Optional[List[str]] = None,
        test_size: float = 0.2,
        compare_all: bool = True,
    ) -> Dict[str, Any]:
        """Automatically run multiple classifiers and return best model."""
        try:
            X_train, X_test, y_train, y_test, features = self.prepare_data(
                df, target_col, feature_cols, test_size
            )
        except Exception as e:
            return {"error": str(e)}

        models = self.get_classification_models()
        results = []

        selected_models = models if compare_all else {"Random Forest": models["Random Forest"]}

        for name, model in selected_models.items():
            try:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)

                result = {
                    "model": name,
                    "accuracy": round(accuracy_score(y_test, y_pred), 4),
                    "precision": round(precision_score(y_test, y_pred, average='weighted', zero_division=0), 4),
                    "recall": round(recall_score(y_test, y_pred, average='weighted', zero_division=0), 4),
                    "f1_score": round(f1_score(y_test, y_pred, average='weighted', zero_division=0), 4),
                }

                # ROC AUC for binary classification
                if len(np.unique(y_test)) == 2 and hasattr(model, "predict_proba"):
                    try:
                        y_proba = model.predict_proba(X_test)[:, 1]
                        result["roc_auc"] = round(roc_auc_score(y_test, y_proba), 4)
                    except Exception:
                        pass

                # Cross-validation score
                try:
                    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='accuracy')
                    result["cv_mean"] = round(cv_scores.mean(), 4)
                    result["cv_std"] = round(cv_scores.std(), 4)
                except Exception:
                    pass

                results.append(result)
            except Exception as e:
                results.append({"model": name, "error": str(e)})

        # Find best model
        results_df = pd.DataFrame(results)
        if "accuracy" in results_df.columns:
            best_idx = results_df["accuracy"].idxmax()
            best_model_name = results_df.loc[best_idx, "model"]
            best_model = selected_models[best_model_name]
            # Retrain best on full data
            best_model.fit(np.vstack([X_train, X_test]), np.hstack([y_train, y_test]))
            self.model = best_model
            self.is_trained = True
        else:
            best_model_name = None

        return {
            "type": "classification",
            "results": results_df,
            "best_model": best_model_name,
            "features": features,
            "n_classes": len(np.unique(y_test)),
            "class_distribution": pd.Series(y_test).value_counts().to_dict(),
        }

    # â”€â”€â”€ Auto-Regression â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def auto_regress(
        self,
        df: pd.DataFrame,
        target_col: str,
        feature_cols: Optional[List[str]] = None,
        test_size: float = 0.2,
        compare_all: bool = True,
    ) -> Dict[str, Any]:
        """Automatically run multiple regression models and return best."""
        try:
            X_train, X_test, y_train, y_test, features = self.prepare_data(
                df, target_col, feature_cols, test_size
            )
        except Exception as e:
            return {"error": str(e)}

        models = self.get_regression_models()
        results = []

        selected_models = models if compare_all else {"Random Forest": models["Random Forest Regressor"]}

        for name, model in selected_models.items():
            try:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)

                result = {
                    "model": name,
                    "r2_score": round(r2_score(y_test, y_pred), 4),
                    "rmse": round(np.sqrt(mean_squared_error(y_test, y_pred)), 4),
                    "mae": round(mean_absolute_error(y_test, y_pred), 4),
                    "mse": round(mean_squared_error(y_test, y_pred), 4),
                }

                # Cross-validation
                try:
                    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='r2')
                    result["cv_mean_r2"] = round(cv_scores.mean(), 4)
                    result["cv_std_r2"] = round(cv_scores.std(), 4)
                except Exception:
                    pass

                results.append(result)
            except Exception as e:
                results.append({"model": name, "error": str(e)})

        results_df = pd.DataFrame(results)
        if "r2_score" in results_df.columns:
            best_idx = results_df["r2_score"].idxmax()
            best_model_name = results_df.loc[best_idx, "model"]
            best_model = selected_models[best_model_name]
            best_model.fit(np.vstack([X_train, X_test]), np.hstack([y_train, y_test]))
            self.model = best_model
            self.is_trained = True
        else:
            best_model_name = None

        return {
            "type": "regression",
            "results": results_df,
            "best_model": best_model_name,
            "features": features,
            "target_mean": float(y_train.mean()),
            "target_std": float(y_train.std()),
        }

    # â”€â”€â”€ Clustering â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def auto_cluster(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
        n_clusters: int = 3,
        algorithm: str = "K-Means",
    ) -> Dict[str, Any]:
        """Perform clustering analysis."""
        if feature_cols is None:
            feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if len(feature_cols) < 2:
            return {"error": "Need at least 2 numeric features for clustering"}

        X = df[feature_cols].dropna()
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        models_map = self.get_clustering_models()
        if algorithm not in models_map:
            return {"error": f"Unknown algorithm: {algorithm}"}

        clusterer = models_map[algorithm]
        if algorithm == "K-Means":
            clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        elif algorithm == "Hierarchical (Agglomerative)":
            clusterer = AgglomerativeClustering(n_clusters=n_clusters)

        labels = clusterer.fit_predict(X_scaled)

        # Silhouette score
        sil_score = silhouette_score(X_scaled, labels) if len(np.unique(labels)) > 1 else 0

        # PCA for visualization
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)

        result_df = X.copy()
        result_df["Cluster"] = labels
        result_df["PC1"] = X_pca[:, 0]
        result_df["PC2"] = X_pca[:, 1]

        # Cluster profiles
        profiles = result_df.groupby("Cluster")[feature_cols].mean().round(4)

        return {
            "type": "clustering",
            "algorithm": algorithm,
            "n_clusters": len(np.unique(labels)),
            "silhouette_score": round(float(sil_score), 4),
            "labels": labels.tolist(),
            "cluster_sizes": pd.Series(labels).value_counts().to_dict(),
            "profiles": profiles,
            "result_df": result_df,
            "pca_variance": pca.explained_variance_ratio_.tolist(),
            "feature_cols": feature_cols,
        }

    # â”€â”€â”€ Feature Importance â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """Get feature importance from trained tree-based model."""
        if not self.is_trained:
            return None

        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            importances = np.abs(self.model.coef_[0]) if len(self.model.coef_.shape) > 1 else np.abs(self.model.coef_)
        else:
            return None

        if len(importances) != len(self.feature_names):
            # Pad or truncate
            if len(importances) > len(self.feature_names):
                importances = importances[:len(self.feature_names)]
            else:
                importances = np.pad(importances, (0, len(self.feature_names) - len(importances)))

        importance_df = pd.DataFrame({
            "Feature": self.feature_names[:len(importances)],
            "Importance": importances,
        }).sort_values("Importance", ascending=False)

        importance_df["Importance_Pct"] = (importance_df["Importance"] / importance_df["Importance"].sum() * 100).round(2)
        return importance_df

    # â”€â”€â”€ Time Series Forecasting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def forecast_time_series(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        periods: int = 30,
        freq: str = 'D',
        seasonality: str = 'auto',
    ) -> Dict[str, Any]:
        """Forecast time series data using Prophet or ARIMA-like approach."""
        ts_df = df[[date_col, value_col]].copy()
        ts_df.columns = ['ds', 'y']
        ts_df = ts_df.dropna()
        ts_df['ds'] = pd.to_datetime(ts_df['ds'])

        if HAS_PROPHET:
            model = Prophet(
                yearly_seasonality=True if seasonality in ('auto', 'yearly') else False,
                weekly_seasonality=True if seasonality in ('auto', 'weekly') else False,
                daily_seasonality=True if seasonality in ('auto', 'daily') else False,
            )
            model.fit(ts_df)
            future = model.make_future_dataframe(periods=periods, freq=freq)
            forecast = model.predict(future)

            self.model = model
            self.is_trained = True

            # Historical fit
            historical = ts_df.copy()
            forecasted = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)

            return {
                "type": "forecast",
                "method": "Prophet",
                "historical": historical,
                "forecast": forecasted,
                "components": ['trend', 'weekly', 'yearly'] if seasonality == 'auto' else ['trend'],
                "changepoints": model.changepoints.tolist() if hasattr(model, 'changepoints') else [],
            }
        else:
            # Fallback: simple moving average  linear trend
            ts_df['ma'] = ts_df['y'].rolling(window=min(7, len(ts_df)), min_periods=1).mean()
            last_val = ts_df['ma'].iloc[-1]
            trend = (ts_df['y'].iloc[-1] - ts_df['y'].iloc[0]) / max(len(ts_df), 1)

            future_dates = pd.date_range(
                start=ts_df['ds'].iloc[-1]  timedelta(days=1),
                periods=periods,
                freq=freq
            )
            forecast_values = [last_val  trend * i for i in range(1, periods  1)]

            forecast_df = pd.DataFrame({
                'ds': future_dates,
                'yhat': forecast_values,
                'yhat_lower': [v * 0.9 for v in forecast_values],
                'yhat_upper': [v * 1.1 for v in forecast_values],
            })

            return {
                "type": "forecast",
                "method": "Moving Average  Trend (Prophet not installed)",
                "historical": ts_df[['ds', 'y']],
                "forecast": forecast_df,
                "components": ['trend'],
            }

    # â”€â”€â”€ Model Persistence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def save_model(self, filepath: str) -> bool:
        """Save trained model to disk using joblib."""
        import joblib
        try:
            model_data = {
                'model': self.model,
                'preprocessor': self.preprocessor,
                'label_encoders': self.label_encoders,
                'feature_names': self.feature_names,
                'target_name': self.target_name,
                'model_type': self.model_type,
            }
            joblib.dump(model_data, filepath)
            return True
        except Exception as e:
            st.error(f"Model save failed: {str(e)}")
            return False

    def load_model(self, filepath: str) -> bool:
        """Load trained model from disk."""
        import joblib
        try:
            model_data = joblib.load(filepath)
            self.model = model_data['model']
            self.preprocessor = model_data['preprocessor']
            self.label_encoders = model_data['label_encoders']
            self.feature_names = model_data['feature_names']
            self.target_name = model_data['target_name']
            self.model_type = model_data['model_type']
            self.is_trained = True
            return True
        except Exception as e:
            st.error(f"Model load failed: {str(e)}")
            return False

    # â”€â”€â”€ Prediction on New Data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def predict(self, df: pd.DataFrame) -> Optional[np.ndarray]:
        """Make predictions on new data."""
        if not self.is_trained:
            return None

        try:
            X = df[self.feature_names].copy()
            if self.preprocessor:
                X = self.preprocessor.transform(X)
            predictions = self.model.predict(X)

            # Decode if classification
            if 'target' in self.label_encoders:
                predictions = self.label_encoders['target'].inverse_transform(predictions.astype(int))

            return predictions
        except Exception as e:
            st.error(f"Prediction error: {str(e)}")
            return None


# â”€â”€â”€ UI Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def render_predictive_modeling_ui(df: pd.DataFrame) -> None:
    """Render the complete AutoML UI."""
    st.markdown("## ðŸ§¬ Predictive Modeling Engine")
    st.markdown("*Automated Machine Learning â€” Classification, Regression, Clustering, Forecasting*")

    if df is None or df.empty:
        st.warning("No data available. Load data first.")
        return

    engine = PredictiveEngine()

    task_type = st.radio(
        "Select task type:",
        ["Classification", "Regression", "Clustering", "Time Series Forecasting"],
        horizontal=True
    )

    if task_type == "Classification":
        st.subheader("ðŸ“Š Auto Classification")
        target_options = df.columns.tolist()

        target_col = st.selectbox("Target variable (to predict)", options=target_options, key="clf_target")

        # Auto-detect binary/categorical targets
        if target_col:
            nunique = df[target_col].nunique()
            if nunique > 20:
                st.warning(f"âš ï¸ '{target_col}' has {nunique} unique values â€” consider Regression instead")
            elif nunique == 2:
                st.info(f"âœ… Binary classification detected (2 classes)")

        feature_cols = st.multiselect(
            "Feature columns (leave empty to auto-select numeric columns)",
            options=[c for c in df.columns if c != target_col],
            key="clf_features"
        )

        compare_all = st.checkbox("Compare all models (takes longer)", value=True, key="clf_compare")

        col1, col2 = st.columns([1, 3])
        with col1:
            test_size = st.slider("Test size (%)", 10, 50, 20, 5, key="clf_test") / 100

        if st.button("ðŸš€ Run Auto Classification", type="primary"):
            with st.spinner("Training classification models..."):
                results = engine.auto_classify(df, target_col, feature_cols or None, test_size, compare_all)

            if "error" in results:
                st.error(results["error"])
            else:
                st.success(f"âœ… Best model: **{results.get('best_model', 'N/A')}**")
                st.dataframe(results["results"], use_container_width=True, hide_index=True)

                # Feature importance
                imp_df = engine.get_feature_importance()
                if imp_df is not None:
                    st.subheader("ðŸ”‘ Feature Importance")
                    st.dataframe(imp_df, use_container_width=True, hide_index=True)

                    # Plot
                    import plotly.express as px
                    fig = px.bar(imp_df.head(15), x="Importance", y="Feature", orientation="h",
                                 title="Top Feature Importances", height=400)
                    st.plotly_chart(fig, use_container_width=True)

    elif task_type == "Regression":
        st.subheader("ðŸ“ˆ Auto Regression")
        target_options = df.select_dtypes(include=[np.number]).columns.tolist()

        if not target_options:
            st.warning("No numeric target variables available")
            return

        target_col = st.selectbox("Target variable (to predict)", options=target_options, key="reg_target")
        feature_cols = st.multiselect(
            "Feature columns (leave empty for auto-select)",
            options=[c for c in df.columns if c != target_col],
            key="reg_features"
        )
        compare_all = st.checkbox("Compare all models", value=True, key="reg_compare")
        test_size = st.slider("Test size (%)", 10, 50, 20, 5, key="reg_test") / 100

        if st.button("ðŸš€ Run Auto Regression", type="primary"):
            with st.spinner("Training regression models..."):
                results = engine.auto_regress(df, target_col, feature_cols or None, test_size, compare_all)

            if "error" in results:
                st.error(results["error"])
            else:
                st.success(f"âœ… Best model: **{results.get('best_model', 'N/A')}**")
                st.dataframe(results["results"], use_container_width=True, hide_index=True)

                imp_df = engine.get_feature_importance()
                if imp_df is not None:
                    st.subheader("ðŸ”‘ Feature Importance")
                    st.dataframe(imp_df, use_container_width=True, hide_index=True)

                    import plotly.express as px
                    fig = px.bar(imp_df.head(15), x="Importance", y="Feature", orientation="h",
                                 title="Top Predictors", height=400)
                    st.plotly_chart(fig, use_container_width=True)

    elif task_type == "Clustering":
        st.subheader("ðŸ”µ Auto Clustering")
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            st.warning("Need at least 2 numeric columns for clustering")
            return

        feature_cols = st.multiselect(
            "Features for clustering",
            options=numeric_cols,
            default=numeric_cols[:min(4, len(numeric_cols))],
            key="clust_features"
        )
        n_clusters = st.slider("Number of clusters", 2, 10, 3, key="clust_n")
        algorithm = st.selectbox(
            "Algorithm",
            options=["K-Means", "DBSCAN", "Hierarchical (Agglomerative)"],
            key="clust_algo"
        )

        if st.button("ðŸš€ Run Clustering", type="primary"):
            with st.spinner("Performing clustering..."):
                results = engine.auto_cluster(df, feature_cols, n_clusters, algorithm)

            if "error" in results:
                st.error(results["error"])
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Clusters", results.get("n_clusters"))
                with col2:
                    st.metric("Silhouette Score", results.get("silhouette_score", 0))
                with col3:
                    st.metric("Features", len(results.get("feature_cols", [])))

                st.subheader("ðŸ“‹ Cluster Profiles")
                st.dataframe(results.get("profiles", pd.DataFrame()), use_container_width=True)

                # Visualization
                result_df = results.get("result_df")
                if result_df is not None and "PC1" in result_df.columns:
                    import plotly.express as px
                    fig = px.scatter(
                        result_df, x="PC1", y="PC2", color="Cluster",
                        title="Cluster Visualization (PCA Reduced)",
                        hover_data=feature_cols[:3], height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)

    elif task_type == "Time Series Forecasting":
        st.subheader("ðŸ“… Time Series Forecasting")
        date_cols = []
        for col in df.columns:
            try:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    date_cols.append(col)
            except Exception:
                pass
        # Also check object columns that might be dates
        for col in text_columns(df):
            try:
                pd.to_datetime(df[col].dropna().head(5))
                date_cols.append(col)
            except Exception:
                pass

        if not date_cols:
            st.warning("No date/time columns detected. Please ensure a date column exists.")
            return

        date_col = st.selectbox("Date column", options=date_cols, key="ts_date")
        value_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        value_col = st.selectbox("Value column to forecast", options=value_cols, key="ts_value")

        periods = st.number_input("Forecast periods ahead", min_value=1, max_value=365, value=30, key="ts_periods")
        freq = st.selectbox("Time frequency", options=['D', 'W', 'M', 'Q', 'Y'], index=0, key="ts_freq",
                            help="D=Daily, W=Weekly, M=Monthly, Q=Quarterly, Y=Yearly")

        if st.button("ðŸš€ Run Forecast", type="primary"):
            with st.spinner("Generating forecast..."):
                results = engine.forecast_time_series(df, date_col, value_col, int(periods), freq)

            if "error" in results:
                st.error(results["error"])
            else:
                st.info(f"**Method**: {results.get('method', 'N/A')}")

                hist = results.get("historical")
                fore = results.get("forecast")

                if hist is not None and fore is not None:
                    import plotly.express as px
                    import plotly.graph_objects as go

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=hist['ds'], y=hist['y'], mode='lines', name='Historical'))
                    fig.add_trace(go.Scatter(
                        x=fore['ds'], y=fore['yhat'], mode='linesmarkers',
                        name='Forecast', line=dict(color='red', dash='dash')
                    ))
                    if 'yhat_lower' in fore.columns and 'yhat_upper' in fore.columns:
                        fig.add_trace(go.Scatter(
                            x=fore['ds'], y=fore['yhat_upper'], fill=None,
                            mode='lines', line=dict(color='red', width=0), showlegend=False
                        ))
                        fig.add_trace(go.Scatter(
                            x=fore['ds'], y=fore['yhat_lower'], fill='tonexty',
                            mode='lines', line=dict(color='red', width=0),
                            name='Confidence Interval'
                        ))

                    fig.update_layout(title=f"Time Series Forecast for {value_col}", height=500)
                    st.plotly_chart(fig, use_container_width=True)

                    st.subheader("ðŸ“‹ Forecast Values")
                    st.dataframe(fore, use_container_width=True, hide_index=True)

        # Model export
        if engine.is_trained:
            st.markdown("---")
            st.subheader("ðŸ’¾ Export Trained Model")
            if st.button("ðŸ“¥ Download Model (joblib)"):
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f:
                    engine.save_model(f.name)
                    with open(f.name, 'rb') as fh:
                        model_bytes = fh.read()
                    os.unlink(f.name)

                b64 = base64.b64encode(model_bytes).decode()
                href = f'<a href="data:application/octet-stream;base64,{b64}" download="trained_model.joblib">ðŸ“¥ Click to Download</a>'
                st.markdown(href, unsafe_allow_html=True)


