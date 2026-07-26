"""Tests for the upload parsing path and its memory guards."""
import io

import numpy as np
import pandas as pd
import pytest

from modules import file_uploader, runtime_perf


class FakeUpload(io.BytesIO):
    def __init__(self, data: bytes, name: str = "data.csv"):
        super().__init__(data)
        self.name = name
        self.size = len(data)


@pytest.fixture
def captured_messages(monkeypatch):
    """Collect the Streamlit messages emitted while parsing."""
    messages = {"error": [], "warning": [], "success": [], "info": [], "caption": []}
    for level in messages:
        monkeypatch.setattr(
            file_uploader.st,
            level,
            lambda msg, _level=level, **kwargs: messages[_level].append(str(msg)),
        )
    return messages


def csv_bytes(rows: int) -> bytes:
    frame = pd.DataFrame(
        {"n": np.arange(rows, dtype="int64"), "label": ["a", "b"] * (rows // 2)}
    )
    return frame.to_csv(index=False).encode()


class TestGetFileExtension:
    @pytest.mark.parametrize(
        "name,expected",
        [("a.csv", "csv"), ("a.CSV", "csv"), ("a.b.xlsx", "xlsx"), ("noext", "")],
    )
    def test_extension(self, name, expected):
        assert file_uploader.get_file_extension(name) == expected


class TestParseUploadedFile:
    def test_none_returns_none(self):
        assert file_uploader.parse_uploaded_file(None) is None

    def test_parses_csv(self, captured_messages):
        df = file_uploader.parse_uploaded_file(FakeUpload(csv_bytes(10)))
        assert list(df.columns) == ["n", "label"]
        assert len(df) == 10
        assert captured_messages["success"]

    def test_strips_column_whitespace(self, captured_messages):
        df = file_uploader.parse_uploaded_file(FakeUpload(b" a , b \n1,2\n"))
        assert list(df.columns) == ["a", "b"]

    def test_rejects_oversized_upload(self, captured_messages):
        upload = FakeUpload(csv_bytes(10))
        upload.size = int(runtime_perf.MAX_UPLOAD_MB * 1024 * 1024) + 1
        assert file_uploader.parse_uploaded_file(upload) is None
        assert captured_messages["error"]
        assert not captured_messages["success"]

    def test_truncates_and_warns_beyond_row_cap(self, captured_messages, monkeypatch):
        monkeypatch.setattr(runtime_perf, "MAX_ROWS_IN_MEMORY", 20)
        monkeypatch.setattr(runtime_perf, "CSV_CHUNK_ROWS", 10)
        df = file_uploader.parse_uploaded_file(FakeUpload(csv_bytes(100)))
        assert len(df) == 20
        assert captured_messages["warning"]

    def test_csv_is_downcast(self, captured_messages):
        df = file_uploader.parse_uploaded_file(FakeUpload(csv_bytes(50)))
        assert df["n"].dtype.itemsize < 8

    def test_unsupported_extension_errors(self, captured_messages):
        assert file_uploader.parse_uploaded_file(FakeUpload(b"x", name="a.txt")) is None
        assert captured_messages["error"]

    def test_latin1_fallback(self, captured_messages):
        df = file_uploader.parse_uploaded_file(FakeUpload("name\ncaf\xe9\n".encode("latin-1")))
        assert len(df) == 1


class TestMergeDatasets:
    def test_returns_uploaded_when_notion_empty(self, captured_messages):
        uploaded = pd.DataFrame({"a": [1]})
        pd.testing.assert_frame_equal(
            file_uploader.merge_datasets(pd.DataFrame(), uploaded), uploaded
        )

    def test_merges_on_key(self, captured_messages):
        left = pd.DataFrame({"id": [1, 2], "x": ["a", "b"]})
        right = pd.DataFrame({"id": [1, 2], "y": [10, 20]})
        merged = file_uploader.merge_datasets(left, right, merge_key="id")
        assert list(merged.columns) == ["id", "x", "y"]
        assert len(merged) == 2

    def test_appends_when_columns_overlap(self, captured_messages):
        frame = pd.DataFrame({"a": [1]})
        assert len(file_uploader.merge_datasets(frame, frame)) == 2

    def test_concats_sidewise_without_common_columns(self, captured_messages):
        merged = file_uploader.merge_datasets(
            pd.DataFrame({"a": [1]}), pd.DataFrame({"b": [2]})
        )
        assert list(merged.columns) == ["a", "b"]
