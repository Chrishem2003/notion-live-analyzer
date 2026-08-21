
"""Unit tests for modules.export."""
import base64
import io
import json

import pandas as pd
import pytest

from modules import export


@pytest.fixture
def df():
    return pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})


class FakeFigure:
    def __init__(self, data=b"image-bytes", error=None):
        self.data = data
        self.error = error
        self.calls = []

    def to_image(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.data


class TestChartExport:
    def test_png_export_passes_dimensions(self):
        fig = FakeFigure()
        assert export.export_chart_as_png(fig) == b"image-bytes"
        assert fig.calls[0] == {"format": "png", "width": 1200, "height": 800, "scale": 2}

    def test_svg_export_passes_dimensions(self):
        fig = FakeFigure(b"<svg/>")
        assert export.export_chart_as_svg(fig) == b"<svg/>"
        assert fig.calls[0] == {"format": "svg", "width": 1200, "height": 800}

    def test_none_figure_returns_none(self):
        assert export.export_chart_as_png(None) is None
        assert export.export_chart_as_svg(None) is None

    def test_export_returns_none_without_plotly(self, monkeypatch):
        monkeypatch.setattr(export, "HAS_PLOTLY", False)
        assert export.export_chart_as_png(FakeFigure()) is None
        assert export.export_chart_as_svg(FakeFigure()) is None

    def test_png_export_failure_is_handled(self):
        assert export.export_chart_as_png(FakeFigure(error=RuntimeError("no kaleido"))) is None

    def test_svg_export_failure_is_handled(self):
        assert export.export_chart_as_svg(FakeFigure(error=RuntimeError("boom"))) is None

    def test_chart_download_link_embeds_base64_png(self):
        link = export.get_chart_download_link(FakeFigure(b"abc"), "mychart", "png")
        assert 'download="mychart.png"' in link
        assert f"data:image/png;base64,{base64.b64encode(b'abc').decode()}}" in link

    def test_chart_download_link_svg(self):
        link = export.get_chart_download_link(FakeFigure(b"<svg/>"), "c", "svg")
        assert "data:image/svgxml;base64," in link

    def test_chart_download_link_unknown_format(self):
        assert export.get_chart_download_link(FakeFigure(), "c", "pdf") is None

    def test_chart_download_link_none_when_export_fails(self):
        fig = FakeFigure(error=RuntimeError("boom"))
        assert export.get_chart_download_link(fig, "c", "png") is None


class TestDataExport:
    def test_csv(self, df):
        assert export.export_data_as_csv(df).decode() == df.to_csv(index=False)

    def test_excel_roundtrip(self, df):
        data = export.export_data_as_excel(df)
        restored = pd.read_excel(io.BytesIO(data))
        pd.testing.assert_frame_equal(restored, df, check_dtype=False)

    def test_json_records(self, df):
        assert json.loads(export.export_data_as_json(df)) == [
            {"a": 1, "b": "x"},
            {"a": 2, "b": "y"},
        ]

    def test_parquet_roundtrip(self, df):
        pytest.importorskip("pyarrow")
        restored = pd.read_parquet(io.BytesIO(export.export_data_as_parquet(df)))
        pd.testing.assert_frame_equal(restored, df, check_dtype=False)


class TestDataDownloadLink:
    @pytest.mark.parametrize(
        "fmt,mime",
        [
            ("csv", "text/csv"),
            ("json", "application/json"),
            (
                "xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        ],
    )
    def test_link_contains_mime_and_filename(self, df, fmt, mime):
        link = export.get_data_download_link(df, "dataset", fmt)
        assert f"data:{mime}};base64," in link
        assert f'download="dataset.{fmt}}"' in link

    def test_empty_dataframe_yields_no_link(self):
        assert export.get_data_download_link(pd.DataFrame(), "d", "csv") == ""

    def test_none_dataframe_yields_no_link(self):
        assert export.get_data_download_link(None, "d", "csv") == ""

    def test_unknown_format_yields_no_link(self, df):
        assert export.get_data_download_link(df, "d", "xml") == ""


class TestMarkdownReport:
    def test_report_includes_title_and_sections(self):
        report = export.generate_markdown_report("My Report", {"Intro": "Hello", "Method": "t-test"})
        assert report.startswith("# My Report")
        assert "## Intro" in report
        assert "Hello" in report
        assert "## Method" in report

    def test_report_includes_dataset_summary(self, df):
        report = export.generate_markdown_report("R", {}, df_summary=df)
        assert "## Dataset Summary" in report
        assert "**Rows**: 2" in report
        assert "a, b" in report

    def test_report_skips_summary_for_empty_frame(self):
        report = export.generate_markdown_report("R", {}, df_summary=pd.DataFrame())
        assert "Dataset Summary" not in report

    def test_non_string_section_content_is_stringified(self):
        report = export.generate_markdown_report("R", {"Numbers": 123})
        assert "123" in report

