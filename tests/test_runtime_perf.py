"""Tests for modules.runtime_perf — the hosted-deployment memory guards."""
import io

import numpy as np
import pandas as pd
import pytest

from modules import runtime_perf as rp


class FakeUpload(io.BytesIO):
    """Minimal stand-in for a Streamlit UploadedFile."""

    def __init__(self, data: bytes, name: str = "data.csv"):
        super().__init__(data)
        self.name = name
        self.size = len(data)


def make_csv(rows: int, cols: int = 3) -> bytes:
    frame = pd.DataFrame(
        {f"c{i}": np.arange(rows, dtype="int64") + i for i in range(cols)}
    )
    return frame.to_csv(index=False).encode()


class TestMemoryProbes:
    def test_memory_usage_is_positive(self):
        assert rp.memory_usage_mb() > 0

    def test_dataframe_memory_scales_with_rows(self):
        small = pd.DataFrame({"a": range(100)})
        large = pd.DataFrame({"a": range(100_000)})
        assert rp.dataframe_memory_mb(large) > rp.dataframe_memory_mb(small)

    def test_dataframe_memory_handles_none(self):
        assert rp.dataframe_memory_mb(None) == 0.0

    def test_release_returns_non_negative(self):
        assert rp.release() >= 0.0


class TestShrinkDataframe:
    def test_downcasts_integers(self):
        df = pd.DataFrame({"small": pd.Series([1, 2, 3], dtype="int64")})
        assert rp.shrink_dataframe(df)["small"].dtype.itemsize < 8

    def test_downcasts_floats(self):
        df = pd.DataFrame({"f": pd.Series([1.5, 2.5], dtype="float64")})
        assert rp.shrink_dataframe(df)["f"].dtype == np.float32

    def test_reduces_total_footprint(self):
        df = pd.DataFrame({f"c{i}": np.arange(50_000, dtype="int64") for i in range(4)})
        assert rp.dataframe_memory_mb(rp.shrink_dataframe(df)) < rp.dataframe_memory_mb(df)

    def test_preserves_values_and_shape(self):
        df = pd.DataFrame({"i": [1, 2, 3], "f": [0.5, 1.5, 2.5], "s": ["a", "b", "c"]})
        out = rp.shrink_dataframe(df)
        assert out.shape == df.shape
        assert out["i"].tolist() == [1, 2, 3]
        assert out["s"].tolist() == ["a", "b", "c"]

    def test_leaves_text_alone_by_default(self):
        # Categorical text would break pandas_compat.is_text_dtype consumers.
        df = pd.DataFrame({"s": ["a", "a", "b", "b"]})
        assert not isinstance(rp.shrink_dataframe(df)["s"].dtype, pd.CategoricalDtype)

    def test_categorizes_when_threshold_enabled(self):
        df = pd.DataFrame({"s": ["a", "a", "b", "b"]})
        out = rp.shrink_dataframe(df, category_threshold=0.9)
        assert isinstance(out["s"].dtype, pd.CategoricalDtype)

    def test_empty_frame_passes_through(self):
        empty = pd.DataFrame()
        assert rp.shrink_dataframe(empty).empty

    def test_booleans_are_untouched(self):
        df = pd.DataFrame({"b": [True, False]})
        assert rp.shrink_dataframe(df)["b"].dtype == bool


class TestCheckUploadSize:
    def test_accepts_small_file(self):
        ok, msg = rp.check_upload_size(FakeUpload(b"a,b\n1,2\n"))
        assert ok and msg == ""

    def test_rejects_oversized_file(self):
        upload = FakeUpload(b"x")
        upload.size = int(rp.MAX_UPLOAD_MB * 1024 * 1024) + 1
        ok, msg = rp.check_upload_size(upload)
        assert not ok
        assert "above the" in msg

    def test_rejects_none(self):
        ok, _ = rp.check_upload_size(None)
        assert not ok

    def test_allows_object_without_size_attribute(self):
        ok, _ = rp.check_upload_size(io.BytesIO(b"a,b\n1,2\n"))
        assert ok


class TestReadCsvChunked:
    def test_reads_all_rows_under_the_cap(self):
        df, truncated = rp.read_csv_chunked(FakeUpload(make_csv(500)), chunk_rows=100)
        assert len(df) == 500
        assert not truncated

    def test_truncates_at_max_rows(self):
        df, truncated = rp.read_csv_chunked(
            FakeUpload(make_csv(500)), max_rows=120, chunk_rows=50
        )
        assert len(df) == 120
        assert truncated

    def test_single_chunk_matches_read_csv(self):
        data = make_csv(50)
        df, _ = rp.read_csv_chunked(FakeUpload(data), chunk_rows=1000)
        pd.testing.assert_frame_equal(
            df, rp.shrink_dataframe(pd.read_csv(io.BytesIO(data)))
        )

    def test_chunk_boundary_does_not_drop_rows(self):
        df, _ = rp.read_csv_chunked(FakeUpload(make_csv(300)), chunk_rows=100)
        assert df["c0"].tolist() == list(range(300))

    def test_empty_csv_returns_empty_frame(self):
        df, truncated = rp.read_csv_chunked(FakeUpload(b"c0,c1\n"))
        assert df.empty
        assert not truncated

    def test_result_is_downcast(self):
        df, _ = rp.read_csv_chunked(FakeUpload(make_csv(200)), chunk_rows=50)
        assert df["c0"].dtype.itemsize < 8


class TestTrimHistory:
    def test_keeps_most_recent(self):
        assert rp.trim_history(range(10), max_entries=3) == [7, 8, 9]

    def test_shorter_list_unchanged(self):
        assert rp.trim_history([1, 2], max_entries=5) == [1, 2]

    def test_zero_clears(self):
        assert rp.trim_history([1, 2], max_entries=0) == []


class TestResolveAppUrl:
    @pytest.fixture(autouse=True)
    def _clear_env(self, monkeypatch):
        for var in ("APP_URL", "RENDER_EXTERNAL_URL", "STREAMLIT_APP_URL", "SPACE_HOST"):
            monkeypatch.delenv(var, raising=False)

    def test_none_without_configuration(self):
        assert rp.resolve_app_url() is None

    def test_reads_app_url(self, monkeypatch):
        monkeypatch.setenv("APP_URL", "https://analyzer.streamlit.app")
        assert rp.resolve_app_url() == "https://analyzer.streamlit.app"

    def test_adds_scheme_and_strips_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("APP_URL", "analyzer.streamlit.app/")
        assert rp.resolve_app_url() == "https://analyzer.streamlit.app"

    def test_app_url_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("APP_URL", "https://primary.dev")
        monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://secondary.dev")
        assert rp.resolve_app_url() == "https://primary.dev"
