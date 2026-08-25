"""
CHRISHEM Universal File & Data Converter Studio
================================================
A comprehensive multi-format conversion engine supporting:

  - Format converters: CSV <-> Excel <-> JSON <-> Parquet <-> XML <-> YAML <-> SQL <-> HTML table
  - Encoding converters: UTF-8, Latin-1, Base64, Hex, URL-encoding (auto-detect & convert)
  - Data reshaper: wide<->long pivot, transpose, melt
  - Scientific unit converter: metric/imperial, temperature, pressure, distance, mass
  - Coordinate converter: Decimal <-> DMS <-> UTM
  - PDF text/table extraction

Owner: Kula Chris (CHRISHEM)
"""
from __future__ import annotations

import base64
import binascii
import io
import json
import math
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# ═══════════════════════════════════════════════════════════════════════
# FORMAT CONVERTERS
# ═══════════════════════════════════════════════════════════════════════
def dataframe_to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def dataframe_to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    return buf.getvalue()


def dataframe_to_json(df: pd.DataFrame) -> bytes:
    return df.to_json(orient="records", date_format="iso").encode("utf-8")


def dataframe_to_parquet(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    return buf.getvalue()


def dataframe_to_xml(df: pd.DataFrame, root_tag: str = "dataset", row_tag: str = "row") -> bytes:
    root = ET.Element(root_tag)
    for _, row in df.iterrows():
        el = ET.SubElement(root, row_tag)
        for col in df.columns:
            child = ET.SubElement(el, _xml_safe(col))
            child.text = "" if pd.isna(row[col]) else str(row[col])
    return ET.tostring(root, encoding="utf-8")


def _xml_safe(tag: str) -> str:
    tag = re.sub(r"[^\w\-.]", "_", str(tag))
    if not tag or tag[0].isdigit():
        tag = f"col_{tag}"
    return tag


def dataframe_to_yaml(df: pd.DataFrame) -> bytes:
    records = df.astype(object).where(pd.notnull(df), None).to_dict(orient="records")
    lines = ["# CHRISHEM Universal Converter — YAML Export", f"rows: {len(df)}", "data:"]
    for i, rec in enumerate(records):
        lines.append(f"  - id: {i}")
        for k, v in rec.items():
            if isinstance(v, float) and (v != v):  # NaN
                v = None
            lines.append(f"    {str(k)}: {json.dumps(v, default=str)}")
    return "\n".join(lines).encode("utf-8")


def dataframe_to_sql(df: pd.DataFrame, table_name: str = "converted_table") -> bytes:
    """Generate a CREATE TABLE + INSERT statements for the dataframe."""
    col_defs = []
    for col in df.columns:
        if pd.api.types.is_integer_dtype(df[col]):
            ctype = "INTEGER"
        elif pd.api.types.is_float_dtype(df[col]):
            ctype = "REAL"
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            ctype = "TEXT"
        else:
            ctype = "TEXT"
        col_defs.append(f'"{col}" {ctype}')
    create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n  {", ".join(col_defs)}\n);\n'
    insert_sql = []
    for _, row in df.iterrows():
        vals = []
        for col in df.columns:
            v = row[col]
            if pd.isna(v):
                vals.append("NULL")
            elif isinstance(v, (int, float)):
                vals.append(str(v))
            else:
                vals.append(f"'{str(v).replace(chr(39), chr(39) + chr(39))}'")
        insert_sql.append(f'INSERT INTO "{table_name}" VALUES ({", ".join(vals)});')
    return (create_sql + "\n".join(insert_sql)).encode("utf-8")


def dataframe_to_html(df: pd.DataFrame, title: str = "CHRISHEM Data Export") -> bytes:
    styled = df.to_html(index=False, border=0, classes="chris-table")
    html_doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }}
table.chris-table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
table.chris-table th {{ background: #0b1e36; color: #fff; padding: 8px 10px; text-align: left; }}
table.chris-table td {{ border: 1px solid #e5e7eb; padding: 6px 10px; }}
</style></head><body>
<h2>{title}</h2>
<p><em>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — CHRISHEM Universal Converter</em></p>
{styled}
</body></html>"""
    return html_doc.encode("utf-8")


def dataframe_to_markdown(df: pd.DataFrame) -> bytes:
    return df.to_markdown(index=False).encode("utf-8")


def convert_dataframe(df: pd.DataFrame, target_format: str, **kwargs) -> bytes:
    """Dispatch a dataframe to the requested target format."""
    fmt = target_format.lower()
    if fmt in ("csv",):
        return dataframe_to_csv(df)
    if fmt in ("excel", "xlsx", "xls"):
        return dataframe_to_excel(df)
    if fmt in ("json",):
        return dataframe_to_json(df)
    if fmt in ("parquet",):
        return dataframe_to_parquet(df)
    if fmt in ("xml",):
        return dataframe_to_xml(df, **kwargs)
    if fmt in ("yaml", "yml"):
        return dataframe_to_yaml(df)
    if fmt in ("sql", "sqlite"):
        return dataframe_to_sql(df, kwargs.get("table_name", "converted_table"))
    if fmt in ("html", "htm"):
        return dataframe_to_html(df, kwargs.get("title", "CHRISHEM Data Export"))
    if fmt in ("md", "markdown"):
        return dataframe_to_markdown(df)
    raise ValueError(f"Unsupported target format: {target_format}")


# ═══════════════════════════════════════════════════════════════════════
# ENCODING CONVERTERS
# ═══════════════════════════════════════════════════════════════════════
def auto_detect_encoding(raw: bytes) -> str:
    """Best-effort encoding detection."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        raw.decode("latin-1")
        return "latin-1"
    except Exception:
        return "unknown"


def encode_data(raw: bytes, target_encoding: str) -> bytes:
    """Encode raw bytes into the requested encoding format."""
    target = target_encoding.lower()
    if target in ("base64", "b64"):
        return base64.b64encode(raw)
    if target in ("hex",):
        return raw.hex().encode("utf-8")
    if target in ("url", "urlencode", "percent"):
        return urllib.parse.quote_from_bytes(raw).encode("utf-8")
    if target in ("binary", "bin"):
        return "".join(f"{b:08b}" for b in raw).encode("utf-8")
    if target in ("ascii85", "a85"):
        return base64.a85encode(raw)
    raise ValueError(f"Unsupported encoding: {target_encoding}")


def decode_data(raw: bytes, source_encoding: str) -> bytes:
    """Decode raw bytes from the given encoding back to plain bytes."""
    source = source_encoding.lower()
    text = raw.decode("utf-8", errors="ignore").strip()
    if source in ("base64", "b64"):
        return base64.b64decode(text + "=" * (-len(text) % 4), validate=False)
    if source in ("hex",):
        return bytes.fromhex(re.sub(r"\s+", "", text))
    if source in ("url", "urlencode", "percent"):
        return urllib.parse.unquote_to_bytes(text)
    if source in ("binary", "bin"):
        cleaned = re.sub(r"[^01]", "", text)
        return int(cleaned or "0", 2).to_bytes((len(cleaned) + 7) // 8, "big")
    if source in ("ascii85", "a85"):
        return base64.a85decode(text)
    raise ValueError(f"Unsupported source encoding: {source_encoding}")


# ═══════════════════════════════════════════════════════════════════════
# DATA RESHAPER
# ═══════════════════════════════════════════════════════════════════════
def wide_to_long(
    df: pd.DataFrame, id_vars: List[str], value_vars: List[str], var_name: str = "variable", value_name: str = "value"
) -> pd.DataFrame:
    return df.melt(id_vars=id_vars, value_vars=value_vars, var_name=var_name, value_name=value_name)


def long_to_wide(
    df: pd.DataFrame, id_col: str, var_col: str, value_col: str, aggfunc: str = "first"
) -> pd.DataFrame:
    pivot = df.pivot_table(index=id_col, columns=var_col, values=value_col, aggfunc=aggfunc)
    pivot = pivot.reset_index()
    pivot.columns = [str(c) for c in pivot.columns]
    return pivot


def transpose_df(df: pd.DataFrame, include_header: bool = True) -> pd.DataFrame:
    t = df.T
    if include_header:
        t.columns = [f"col_{i}" for i in range(t.shape[1])]
        t = t.reset_index()
        t.columns = ["Field"] + list(t.columns[1:])
    return t


def stack_columns(df: pd.DataFrame, columns: List[str], stack_name: str = "stacked") -> pd.DataFrame:
    """Stack selected columns into key/value pairs per row."""
    frames = []
    for col in columns:
        frame = pd.DataFrame(
            {
                "row_id": range(len(df)),
                stack_name: df[col],
                "source_column": col,
            }
        )
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else df.copy()


# ═══════════════════════════════════════════════════════════════════════
# SCIENTIFIC UNIT CONVERTER
# ═══════════════════════════════════════════════════════════════════════
# length: meters
LENGTH_UNITS = {
    "meters": 1.0, "kilometers": 1000.0, "centimeters": 0.01, "millimeters": 0.001,
    "miles": 1609.344, "yards": 0.9144, "feet": 0.3048, "inches": 0.0254,
    "nautical_miles": 1852.0,
}
# mass: kilograms
MASS_UNITS = {
    "kilograms": 1.0, "grams": 0.001, "milligrams": 1e-6, "tonnes": 1000.0,
    "pounds": 0.45359237, "ounces": 0.028349523, "stones": 6.35029318,
}
# temperature: celsius base
def _to_celsius(v, unit):
    unit = unit.lower()
    if unit in ("celsius", "c", "degc"):
        return v
    if unit in ("fahrenheit", "f", "degf"):
        return (v - 32) * 5 / 9
    if unit in ("kelvin", "k"):
        return v - 273.15
    raise ValueError(f"Unknown temperature unit: {unit}")


def _from_celsius(v, unit):
    unit = unit.lower()
    if unit in ("celsius", "c", "degc"):
        return v
    if unit in ("fahrenheit", "f", "degf"):
        return v * 9 / 5 + 32
    if unit in ("kelvin", "k"):
        return v + 273.15
    raise ValueError(f"Unknown temperature unit: {unit}")


def convert_unit(value: float, from_unit: str, to_unit: str, category: str) -> Dict[str, Any]:
    """Convert a value between units within a category."""
    category = category.lower()
    if category in ("length", "distance"):
        table = LENGTH_UNITS
        key_from = from_unit.lower().replace(" ", "_")
        key_to = to_unit.lower().replace(" ", "_")
        if key_from not in table or key_to not in table:
            return {"error": f"Unknown {category} unit. Choose from {list(table.keys())}"}
        result = value * table[key_from] / table[key_to]
    elif category in ("mass", "weight"):
        table = MASS_UNITS
        key_from = from_unit.lower().replace(" ", "_")
        key_to = to_unit.lower().replace(" ", "_")
        if key_from not in table or key_to not in table:
            return {"error": f"Unknown {category} unit. Choose from {list(table.keys())}"}
        result = value * table[key_from] / table[key_to]
    elif category == "temperature":
        result = _from_celsius(_to_celsius(value, from_unit), to_unit)
    elif category in ("speed", "velocity"):
        # via meters/second
        speed_table = {
            "m/s": 1.0, "km/h": 1 / 3.6, "mph": 0.44704, "knots": 0.514444,
            "mps": 1.0, "knot": 0.514444,
        }
        key_from = from_unit.lower()
        key_to = to_unit.lower()
        if key_from not in speed_table or key_to not in speed_table:
            return {"error": f"Unknown speed unit. Choose from {list(speed_table.keys())}"}
        result = value * speed_table[key_from] / speed_table[key_to]
    else:
        return {"error": f"Unsupported category: {category}"}
    return {"value": value, "from": from_unit, "to": to_unit, "result": round(result, 8), "category": category}


# ═══════════════════════════════════════════════════════════════════════
# COORDINATE CONVERTER
# ═══════════════════════════════════════════════════════════════════════
def decimal_to_dms(lat: float, lon: float) -> Dict[str, Any]:
    def _to_dms(value: float, pos: str, neg: str) -> Tuple[int, int, float, str]:
        direction = pos if value >= 0 else neg
        abs_val = abs(value)
        deg = int(abs_val)
        rem = (abs_val - deg) * 60
        minutes = int(rem)
        seconds = (rem - minutes) * 60
        return deg, minutes, seconds, direction

    d1, m1, s1, d1_dir = _to_dms(lat, "N", "S")
    d2, m2, s2, d2_dir = _to_dms(lon, "E", "W")
    return {
        "lat_dms": f"{d1}°{m1}′{s1:.2f}″{d1_dir}",
        "lon_dms": f"{d2}°{m2}′{s2:.2f}″{d2_dir}",
        "formatted": f"{d1}°{m1}′{s1:.1f}″{d1_dir} {d2}°{m2}′{s2:.1f}″{d2_dir}",
    }


def dms_to_decimal(lat_dms: str, lon_dms: str) -> Dict[str, Any]:
    def _parse(dms: str) -> float:
        regex = re.search(
            r"([\d.]+)\s*[°d]\s*([\d.]+)\s*['′]\s*([\d.]*)\s*(?:\"|″|'')?\s*([NSEW])?", dms, re.I
        )
        if not regex:
            raise ValueError(f"Cannot parse DMS: {dms}")
        deg, minutes, seconds = float(regex.group(1)), float(regex.group(2)), float(regex.group(3) or 0)
        direction = (regex.group(4) or "").upper()
        value = deg + minutes / 60 + seconds / 3600
        if direction in ("S", "W"):
            value *= -1
        return value

    return {"lat": _parse(lat_dms), "lon": _parse(lon_dms), "formatted": f"{_parse(lat_dms):.6f}, {_parse(lon_dms):.6f}"}


# ═══════════════════════════════════════════════════════════════════════
# PDF TEXT EXTRACTION (zero-dep fallback)
# ═══════════════════════════════════════════════════════════════════════
def extract_pdf_text(raw: bytes) -> Dict[str, Any]:
    """
    Extract text from a PDF. Uses pypdf if available, otherwise falls back
    to a raw stream scanner that pulls printable text blocks.
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return {
            "pages": len(pages),
            "extractor": "pypdf",
            "text": "\n\n".join(pages),
            "total_chars": sum(len(p) for p in pages),
        }
    except Exception:
        pass

    # Fallback: raw PDF stream text extraction (FlateDecode best-effort)
    import zlib

    texts = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.DOTALL):
        stream_data = m.group(1)
        try:
            data = zlib.decompress(stream_data)
        except Exception:
            data = stream_data
        # extract text in parentheses from Tj/TJ operators
        parts = re.findall(rb"\((?:[^()\\]|\\.)*\)", data)
        for p in parts:
            try:
                t = p[1:-1].decode("latin-1").replace("\\((", "(").replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")
                if len(t.strip()) >= 2:
                    texts.append(t)
            except Exception:
                continue
    full_text = " ".join(texts)
    return {
        "pages": full_text.count("\f") + 1,
        "extractor": "raw-stream",
        "text": full_text[:20000],
        "total_chars": len(full_text),
    }


if __name__ == "__main__":
    demo = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})
    print(convert_dataframe(demo, "json")[:80])
    print(decimal_to_dms(0.3476, 32.5825))
    print(convert_unit(100, "Celsius", "Fahrenheit", "temperature"))

