
"""
Automated Feature Engineering + Interaction term discovery, polynomial features,
binning, text extraction, date decomposition, and auto feature selection.
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import warnings

from modules.pandas_compat import text_columns
warnings.filterwarnings('ignore')

try:
    from sklearn.feature_selection import RFE, SelectKBest, f_classif, mutual_info_classif
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.linear_model import Lasso, LogisticRegression
    from sklearn.preprocessing import LabelEncoder
    from sklearn.feature_extraction.text import TfidfVectorizer
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class FeatureEngineer:
    """Automated feature engineering for research datasets."""

    def discover_interactions(
        self,
        df: pd.DataFrame,
        target: str,
        top_n: int = 10,
        max_interaction_vars: int = 5,
    ) -> Dict[str, Any]:
        """
        Discover meaningful interaction terms using mutual information.
        """
        if not HAS_SKLEARN:
            return {"error": "scikit-learn required"}

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = [c for c in numeric_cols if c != target]

        if len(feature_cols) < 2:
            return {"error": "Need at least 2 numeric features"}

        # Limit to top variables to avoid combinatorial explosion
        top_vars = feature_cols[:min(max_interaction_vars, len(feature_cols))]

        # Score each interaction using mutual information
        interactions = []
        y = df[target].fillna(df[target].median())

        for i, v1 in enumerate(top_vars):
            for v2 in top_vars[i + 1:]:
                interaction = df[v1] * df[v2]
                valid = interaction.notna()
                if valid.sum() < 10:
                    continue
                try:
                    mi = mutual_info_classif(
                        np.column_stack([df[v1].fillna(0), df[v2].fillna(0), interaction.fillna(0)]),
                        y.fillna(y.median()),
                        random_state=42
                    )
                    score = float(mi[2]) if len(mi) > 2 else 0
                    interactions.append({
                        "variable_1": v1,
                        "variable_2": v2,
                        "interaction": f"{v1} × {v2}",
                        "mutual_info_score": round(score, 4),
                    })
                except Exception:
                    continue

        interactions.sort(key=lambda x: x["mutual_info_score"], reverse=True)
        return {
            "method": "Interaction Discovery",
            "n_discovered": len(interactions),
            "interactions": interactions[:top_n],
            "top_interaction": interactions[0] if interactions else None,
        }

    def generate_polynomials(
        self,
        df: pd.DataFrame,
        columns: List[str],
        max_degree: int = 3,
    ) -> pd.DataFrame:
        """Generate polynomial features up to specified degree."""
        result = df.copy()
        for col in columns:
            for degree in range(2, max_degree + 1):
                new_col = f"{col}^{degree}"
                result[new_col] = df[col] ** degree
        return result

    def auto_bin(
        self,
        df: pd.DataFrame,
        column: str,
        method: str = "quantile",
        n_bins: int = 4,
    ) -> pd.Series:
        """Discretize a numeric column into bins."""
        if method == "quantile":
            return pd.qcut(df[column], q=n_bins, labels=False, duplicates="drop")
        elif method == "uniform":
            return pd.cut(df[column], bins=n_bins, labels=False)
        elif method == "entropy":
            # Simple entropy-based binning: use quantile with more bins
            return pd.qcut(df[column], q=min(n_bins * 2, df[column].nunique()), labels=False, duplicates="drop")
        return pd.qcut(df[column], q=n_bins, labels=False, duplicates="drop")

    def extract_date_features(
        self,
        df: pd.DataFrame,
        date_col: str,
    ) -> pd.DataFrame:
        """Decompose a date column into multiple features."""
        result = df.copy()
        try:
            dates = pd.to_datetime(df[date_col])
            result[f"{date_col}_year"] = dates.dt.year
            result[f"{date_col}_month"] = dates.dt.month
            result[f"{date_col}_day"] = dates.dt.day
            result[f"{date_col}_dayofweek"] = dates.dt.dayofweek
            result[f"{date_col}_quarter"] = dates.dt.quarter
            result[f"{date_col}_is_weekend"] = (dates.dt.dayofweek >= 5).astype(int)
            result[f"{date_col}_dayofyear"] = dates.dt.dayofyear
            result[f"{date_col}_weekofyear"] = dates.dt.isocalendar().week.astype(int)
        except Exception:
            pass
        return result

    def extract_text_features(
        self,
        df: pd.DataFrame,
        text_col: str,
        max_features: int = 50,
    ) -> pd.DataFrame:
        """Extract TF-IDF features from a text column."""
        if not HAS_SKLEARN:
            return df
        result = df.copy()
        texts = df[text_col].fillna("").astype(str)
        vectorizer = TfidfVectorizer(max_features=max_features, stop_words="english")
        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()
            tfidf_df = pd.DataFrame(
                tfidf_matrix.toarray(),
                columns=[f"tfidf_{w}" for w in feature_names],
                index=df.index,
            )
            result = pd.concat([result, tfidf_df], axis=1)
        except Exception:
            pass
        return result

    def auto_feature_selection(
        self,
        df: pd.DataFrame,
        target: str,
        method: str = "mutual_info",
        max_features: int = 10,
    ) -> Dict[str, Any]:
        """
        Automatically select the best features for predicting target.
        """
        if not HAS_SKLEARN:
            return {"error": "scikit-learn required"}

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = [c for c in numeric_cols if c != target]
        if not feature_cols:
            return {"error": "No numeric features available"}

        X = df[feature_cols].fillna(0)
        y = df[target].fillna(df[target].median())

        if method == "mutual_info":
            selector = SelectKBest(score_func=mutual_info_classif if y.nunique() < 10 else f_classif,
                                   k=min(max_features, len(feature_cols)))
            selector.fit(X, y)
            scores = selector.scores_
        elif method == "rfe":
            estimator = RandomForestClassifier(n_estimators=50, random_state=42) if y.nunique() < 10 else RandomForestRegressor(n_estimators=50, random_state=42)
            selector = RFE(estimator, n_features_to_select=min(max_features, len(feature_cols)))
            selector.fit(X, y)
            scores = selector.ranking_
        elif method == "lasso":
            estimator = LogisticRegression(penalty='l1', solver='saga', C=0.1, random_state=42) if y.nunique() < 10 else Lasso(alpha=0.01, random_state=42)
            estimator.fit(X, y)
            scores = np.abs(estimator.coef_[0]) if hasattr(estimator, 'coef_') and len(estimator.coef_.shape) > 1 else np.abs(estimator.coef_)
        else:
            return {"error": f"Unknown method: {method}"}

        selected = []
        for i, col in enumerate(feature_cols):
            selected.append({
                "feature": col,
                "score": round(float(scores[i]) if i < len(scores) else 0, 4),
                "selected": i < max_features,
            })
        selected.sort(key=lambda x: x["score"], reverse=True)

        return {
            "method": method,
            "n_features": len(feature_cols),
            "max_features": max_features,
            "selected_features": selected[:max_features],
            "all_features": selected,
        }


# ─── UI ─────────────────────────────────────────────────────────────
def render_feature_engineering_ui():
    """Render the Feature Engineering page."""
    import streamlit as st
    import plotly.express as px

    st.markdown("## ⚡ Automated Feature Engineering")
    st.markdown("*Discover interactions, generate polynomials, bin, extract text/date features*")

    df = st.session_state.get("active_df")
    if df is None or df.empty:
        st.warning("No data loaded.")
        return

    engine = FeatureEngineer()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = text_columns(df)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔗 Interactions", "📐 Polynomials", " Binning",
        "📅 Date Features", "🎯 Feature Selection"
    ])

    with tab1:
        st.subheader("🔗 Interaction Term Discovery")
        target = st.selectbox("Target variable", options=numeric_cols, key="fe_target")
        if st.button("🔍 Discover Interactions", type="primary", use_container_width=True):
            result = engine.discover_interactions(df, target)
            if "error" in result:
                st.error(result["error"])
            else:
                st.info(f"Discovered {result['n_discovered']} potential interactions")
                if result.get("interactions"):
                    int_df = pd.DataFrame(result["interactions"])
                    st.dataframe(int_df, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("📐 Polynomial Feature Generation")
        poly_cols = st.multiselect("Columns to expand", options=numeric_cols, default=numeric_cols[:3], key="fe_poly_cols")
        max_deg = st.slider("Max degree", 2, 5, 3, key="fe_max_deg")
        if st.button("📐 Generate Polynomials", type="primary", use_container_width=True) and poly_cols:
            result = engine.generate_polynomials(df, poly_cols, max_deg)
            new_features = [c for c in result.columns if c not in df.columns]
            st.success(f"✅ Generated {len(new_features)} new features")
            st.dataframe(result[new_features].head(10), use_container_width=True)

    with tab3:
        st.subheader(" Binning / Discretization")
        bin_col = st.selectbox("Column to bin", options=numeric_cols, key="fe_bin_col")
        bin_method = st.selectbox("Binning method", options=["quantile", "uniform", "entropy"], key="fe_bin_method")
        n_bins = st.slider("Number of bins", 2, 10, 4, key="fe_n_bins")
        if st.button(" Apply Binning", type="primary", use_container_width=True):
            binned = engine.auto_bin(df, bin_col, bin_method, n_bins)
            st.success(f"✅ Binned into {binned.nunique()} bins")
            st.dataframe(binned.value_counts().reset_index(), use_container_width=True)

    with tab4:
        st.subheader("📅 Date Feature Extraction")
        date_cols = [c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()]
        date_col = st.selectbox("Date column", options=date_cols + [c for c in df.columns], key="fe_date_col")
        if st.button("📅 Extract Date Features", type="primary", use_container_width=True):
            result = engine.extract_date_features(df, date_col)
            new_features = [c for c in result.columns if c not in df.columns and date_col in c]
            st.success(f"✅ Generated {len(new_features)} date features")
            st.dataframe(result[new_features].head(10), use_container_width=True)

    with tab5:
        st.subheader("🎯 Auto Feature Selection")
        target2 = st.selectbox("Target variable", options=numeric_cols, key="fe_target2")
        sel_method = st.selectbox("Selection method", options=["mutual_info", "rfe", "lasso"], key="fe_sel_method")
        max_feats = st.slider("Max features to select", 1, 20, 10, key="fe_max_feats")
        if st.button("🎯 Run Feature Selection", type="primary", use_container_width=True):
            result = engine.auto_feature_selection(df, target2, sel_method, max_feats)
            if "error" in result:
                st.error(result["error"])
            else:
                sel_df = pd.DataFrame(result["selected_features"])
                st.dataframe(sel_df, use_container_width=True, hide_index=True)
                fig = px.bar(sel_df, x="feature", y="score", title="Feature Importance Scores")
                st.plotly_chart(fig, use_container_width=True)

