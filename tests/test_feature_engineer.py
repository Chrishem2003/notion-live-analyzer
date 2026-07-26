"""Unit tests for modules.feature_engineer."""
import numpy as np
import pandas as pd
import pytest

from modules.feature_engineer import HAS_SKLEARN, FeatureEngineer
from tests.helpers import object_series

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture
def engine():
    return FeatureEngineer()


@pytest.fixture
def modelling_df():
    rng = np.random.default_rng(0)
    n = 60
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    return pd.DataFrame(
        {
            "x1": x1,
            "x2": x2,
            "x3": rng.normal(size=n),
            "target": (x1 * x2 > 0).astype(int),
        }
    )


class TestPolynomials:
    def test_generates_requested_degrees(self, engine, modelling_df):
        result = engine.generate_polynomials(modelling_df, ["x1"], max_degree=3)
        assert "x1^2" in result.columns
        assert "x1^3" in result.columns
        np.testing.assert_allclose(result["x1^2"], modelling_df["x1"] ** 2)

    def test_does_not_mutate_input(self, engine, modelling_df):
        before = list(modelling_df.columns)
        engine.generate_polynomials(modelling_df, ["x1"], max_degree=2)
        assert list(modelling_df.columns) == before

    def test_degree_two_only(self, engine, modelling_df):
        result = engine.generate_polynomials(modelling_df, ["x1", "x2"], max_degree=2)
        new_cols = [c for c in result.columns if "^" in c]
        assert new_cols == ["x1^2", "x2^2"]


class TestAutoBin:
    @pytest.fixture
    def df(self):
        return pd.DataFrame({"v": list(range(20))})

    def test_quantile_binning(self, engine, df):
        binned = engine.auto_bin(df, "v", "quantile", n_bins=4)
        assert binned.nunique() == 4

    def test_uniform_binning(self, engine, df):
        binned = engine.auto_bin(df, "v", "uniform", n_bins=5)
        assert binned.nunique() == 5
        assert binned.iloc[0] == 0

    def test_entropy_binning_doubles_bins(self, engine, df):
        binned = engine.auto_bin(df, "v", "entropy", n_bins=3)
        assert binned.nunique() == 6

    def test_unknown_method_falls_back_to_quantile(self, engine, df):
        fallback = engine.auto_bin(df, "v", "unknown", n_bins=4)
        expected = engine.auto_bin(df, "v", "quantile", n_bins=4)
        pd.testing.assert_series_equal(fallback, expected)


class TestDateFeatures:
    def test_decomposes_date_column(self, engine):
        df = pd.DataFrame({"when": pd.to_datetime(["2024-01-06", "2024-07-15"])})
        result = engine.extract_date_features(df, "when")
        assert result["when_year"].tolist() == [2024, 2024]
        assert result["when_month"].tolist() == [1, 7]
        assert result["when_quarter"].tolist() == [1, 3]
        assert result["when_is_weekend"].tolist() == [1, 0]
        assert "when_weekofyear" in result.columns

    def test_invalid_column_returns_copy(self, engine):
        df = pd.DataFrame({"when": object_series(["not-a-date", "also-bad"])})
        result = engine.extract_date_features(df, "when")
        assert list(result.columns) == ["when"]


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn not installed")
class TestSklearnBackedFeatures:
    def test_extract_text_features_adds_tfidf_columns(self, engine):
        df = pd.DataFrame(
            {"text": object_series(["alpha beta", "beta gamma", "gamma delta"])}
        )
        result = engine.extract_text_features(df, "text", max_features=5)
        tfidf_cols = [c for c in result.columns if c.startswith("tfidf_")]
        assert tfidf_cols
        assert len(result) == len(df)

    def test_extract_text_features_handles_empty_vocabulary(self, engine):
        df = pd.DataFrame({"text": object_series(["the", "the", "the"])})
        result = engine.extract_text_features(df, "text")
        assert list(result.columns) == ["text"]

    def test_discover_interactions_ranks_by_mutual_information(self, engine, modelling_df):
        result = engine.discover_interactions(modelling_df, "target", top_n=3)
        assert result["method"] == "Interaction Discovery"
        assert result["n_discovered"] >= 1
        assert len(result["interactions"]) <= 3
        scores = [i["mutual_info_score"] for i in result["interactions"]]
        assert scores == sorted(scores, reverse=True)
        assert result["top_interaction"] == result["interactions"][0]

    def test_discover_interactions_requires_two_features(self, engine):
        df = pd.DataFrame({"only": [1.0, 2.0, 3.0], "target": [0, 1, 0]})
        assert "error" in engine.discover_interactions(df, "target")

    @pytest.mark.parametrize("method", ["mutual_info", "rfe", "lasso"])
    def test_auto_feature_selection_methods(self, engine, modelling_df, method):
        result = engine.auto_feature_selection(modelling_df, "target", method, max_features=2)
        assert result["method"] == method
        assert result["n_features"] == 3
        assert len(result["selected_features"]) == 2
        assert len(result["all_features"]) == 3

    def test_auto_feature_selection_unknown_method(self, engine, modelling_df):
        result = engine.auto_feature_selection(modelling_df, "target", "magic")
        assert result["error"] == "Unknown method: magic"

    def test_auto_feature_selection_without_numeric_features(self, engine):
        df = pd.DataFrame({"target": [1.0, 2.0, 3.0]})
        assert engine.auto_feature_selection(df, "target")["error"] == "No numeric features available"


class TestSklearnUnavailable:
    def test_methods_degrade_gracefully(self, engine, modelling_df, monkeypatch):
        monkeypatch.setattr("modules.feature_engineer.HAS_SKLEARN", False)
        assert engine.discover_interactions(modelling_df, "target") == {"error": "scikit-learn required"}
        assert engine.auto_feature_selection(modelling_df, "target") == {"error": "scikit-learn required"}
        df = pd.DataFrame({"text": object_series(["a b", "c d"])})
        pd.testing.assert_frame_equal(engine.extract_text_features(df, "text"), df)
