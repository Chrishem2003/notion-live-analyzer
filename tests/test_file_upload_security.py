"""Security regression tests for untrusted file upload handling."""
from __future__ import annotations

import importlib
import sys
import types

import pytest

for _name in ("pandas", "streamlit"):
    if _name not in sys.modules:
        sys.modules[_name] = types.ModuleType(_name)

if not hasattr(sys.modules["pandas"], "DataFrame"):
    sys.modules["pandas"].DataFrame = object

_streamlit = sys.modules["streamlit"]
if not hasattr(_streamlit, "error"):
    _streamlit.error_messages = []
    _streamlit.error = lambda message: _streamlit.error_messages.append(str(message))

file_uploader = importlib.import_module("modules.file_uploader")


class FakeUpload:
    def __init__(self, name: str):
        self.name = name


def test_pickle_is_not_an_advertised_upload_format():
    assert "Pickle (.pkl)" not in file_uploader.SUPPORTED_FORMATS
    assert "pkl" not in file_uploader.SUPPORTED_FORMATS.values()


@pytest.mark.parametrize("filename", ["payload.pkl", "payload.pickle"])
def test_pickle_upload_is_rejected_without_deserialization(filename):
    result = file_uploader.parse_uploaded_file(FakeUpload(filename))

    assert result is None
    assert any(
        "Pickle files are not supported" in message
        for message in _streamlit.error_messages
    )
