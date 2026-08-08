"""
🔄 Universal Converter Studio
 Comprehensive file format, encoding, data reshaping, unit conversion,
 and coordinate conversion engine.
"""

import io
import json

import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import hero_card, section_header, metric_card
from modules.file_converter import (
    convert_dataframe,
    dataframe_to_csv,
    dataframe_to_excel,
    dataframe_to_json,
    auto_detect_encoding,
    encode_data,
    decode_data,
    wide_to_long,
    long_to_wide,
    transpose_df,
    stack_columns,
    convert_unit,
    decimal_to_dms,
    dms_to_decimal,
    extract_pdf_text,
)


def _load_dataframe(uploaded):
    """Parse an uploaded file into a DataFrame."""
    if uploaded is None:
        return None
    ext = uploaded.name.rsplit(".", 1)[-1].lower()
    try:
        if ext == "csv":
            return pd.read_csv(io.BytesIO(uploaded.getvalue()), encoding="utf-8", low_memory=False)
        if ext in ("xlsx", "xls"):
            return pd.read_excel(uploaded)
        if ext == "json":
            return pd.read_json(uploaded)
        if ext == "parquet":
            return pd.read_parquet(io.BytesIO(uploaded.getvalue()))
        if ext in ("sav", "sas7bdat", "dta"):
            import pyreadstat
            df, _ = {"sav": pyreadstat.read_sav, "sas7bdat": pyreadstat.read_sas7bdat, "dta": pyreadstat.read_dta}[ext](io.BytesIO(uploaded.getvalue()))
            return df
    except Exception as e:
        st.error(f"Parse error: {e}")
    return None


def render_format_tab():
    """Tab: Format conversion."""
    section_header("📦 Format Converter", "Convert between CSV, Excel, JSON, Parquet, XML, YAML, SQL, HTML, and Markdown.")

    uploaded = st.file_uploader("Upload source data file", type=["csv", "xlsx", "xls", "json", "parquet", "sav", "dta"], key="uc_fmt_upload")
    if uploaded is None:
        st.info("Upload a data file to convert.")
        return

    df = _load_dataframe(uploaded)
    if df is None or df.empty:
        st.error("Could not load the uploaded file.")
        return

    st.success(f"Loaded: {df.shape[0]} rows × {df.shape[1]} columns")
    st.dataframe(df.head(5), use_container_width=True)

    target = st.selectbox("Target format", [
        "CSV", "Excel (XLSX)", "JSON", "Parquet", "XML", "YAML", "SQL (SQLite)", "HTML", "Markdown",
    ], key="uc_fmt_target")

    fmt_map = {
        "CSV": "csv", "Excel (XLSX)": "xlsx", "JSON": "json", "Parquet": "parquet",
        "XML": "xml", "YAML": "yaml", "SQL (SQLite)": "sql", "HTML": "html", "Markdown": "md",
    }
    mime_map = {
        "CSV": "text/csv", "Excel (XLSX)": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "JSON": "application/json", "Parquet": "application/octet-stream", "XML": "application/xml",
        "YAML": "text/yaml", "SQL (SQLite)": "text/plain", "HTML": "text/html", "Markdown": "text/markdown",
    }
    ext_map = {
        "CSV": "csv", "Excel (XLSX)": "xlsx", "JSON": "json", "Parquet": "parquet",
        "XML": "xml", "YAML": "yml", "SQL (SQLite)": "sql", "HTML": "html", "Markdown": "md",
    }

    if st.button("🔄 Convert Now", key="uc_fmt_convert", type="primary"):
        with st.spinner("Converting..."):
            data = convert_dataframe(df, fmt_map[target])
            out_name = uploaded.name.rsplit(".", 1)[0]
            st.download_button(
                f"⬇️ Download {target}",
                data=data,
                file_name=f"{out_name}.{ext_map[target]}",
                mime=mime_map[target],
                key="uc_fmt_dl",
            )
            st.success(f"Conversion complete! {len(data):,} bytes generated.")


def render_encoding_tab():
    """Tab: Encoding converter."""
    section_header("🔤 Encoding Converter", "Encode/decode text between UTF-8, Base64, Hex, URL, Binary, and ASCII85.")

    mode = st.radio("Operation", ["Encode", "Decode"], horizontal=True, key="uc_enc_mode")
    source_text = st.text_area("Input text", placeholder="Text or encoded payload", height=180, key="uc_enc_input")

    target_enc = st.selectbox("Encoding", ["Base64", "Hex", "URL Encoding", "Binary", "ASCII85"], key="uc_enc_type")

    enc_map = {"Base64": "base64", "Hex": "hex", "URL Encoding": "url", "Binary": "binary", "ASCII85": "ascii85"}

    if st.button("⚡ Convert Encoding", key="uc_enc_run", type="primary"):
        if not source_text:
            st.warning("Enter some input.")
        else:
            raw = source_text.encode("utf-8")
            try:
                if mode == "Encode":
                    result = encode_data(raw, enc_map[target_enc])
                else:
                    result = decode_data(raw, enc_map[target_enc])
                result_text = result.decode("utf-8", errors="replace")
                st.success("Conversion successful!")
                st.text_area("Output", value=result_text, height=180, key="uc_enc_out")
                st.download_button("⬇️ Download Result", data=result, file_name="encoding_result.txt", key="uc_enc_dl")
            except Exception as e:
                st.error(f"Conversion error: {e}")


def render_reshape_tab():
    """Tab: Data reshaper."""
    section_header("🔀 Data Reshaper", "Pivot wide↔long, transpose, and stack columns.")

    uploaded = st.file_uploader("Upload data file to reshape", type=["csv", "xlsx", "json"], key="uc_rs_upload")
    if uploaded is None:
        st.info("Upload a dataset to reshape.")
        return

    df = _load_dataframe(uploaded)
    if df is None or df.empty:
        return

    operation = st.selectbox("Reshape operation", ["Wide → Long (melt)", "Long → Wide (pivot)", "Transpose", "Stack Columns"], key="uc_rs_op")

    if operation == "Wide → Long (melt)":
        id_cols = st.multiselect("ID variables (keep)", df.columns.tolist(), key="uc_rs_ids")
        all_cols = df.columns.tolist()
        val_cols = st.multiselect("Value variables (melt)", [c for c in all_cols if c not in id_cols], key="uc_rs_vals")
        if st.button("↔ Melt to Long Format", key="uc_rs_melt", type="primary"):
            result = wide_to_long(df, id_vars=id_cols or [], value_vars=val_cols or [])
            st.dataframe(result.head(20), use_container_width=True)
            st.download_button("⬇️ Download", dataframe_to_csv(result), file_name="long_format.csv", key="uc_rs_melt_dl")

    elif operation == "Long → Wide (pivot)":
        id_col = st.selectbox("Identifier column", df.columns.tolist(), key="uc_rs_pid")
        var_col = st.selectbox("Variable column (becomes columns)", df.columns.tolist(), key="uc_rs_pvar")
        val_col = st.selectbox("Value column", df.columns.tolist(), key="uc_rs_pval")
        if st.button("↔ Pivot to Wide Format", key="uc_rs_piv", type="primary"):
            result = long_to_wide(df, id_col, var_col, val_col)
            st.dataframe(result.head(20), use_container_width=True)
            st.download_button("⬇️ Download", dataframe_to_csv(result), file_name="wide_format.csv", key="uc_rs_piv_dl")

    elif operation == "Transpose":
        if st.button("↕ Transpose Matrix", key="uc_rs_tp", type="primary"):
            result = transpose_df(df)
            st.dataframe(result.head(20), use_container_width=True)
            st.download_button("⬇️ Download", dataframe_to_csv(result), file_name="transposed.csv", key="uc_rs_tp_dl")

    else:  # stack
        cols = st.multiselect("Columns to stack", df.columns.tolist(), key="uc_rs_stack")
        if st.button("📚 Stack Columns", key="uc_rs_stk", type="primary"):
            result = stack_columns(df, cols or list(df.columns))
            st.dataframe(result.head(20), use_container_width=True)
            st.download_button("⬇️ Download", dataframe_to_csv(result), file_name="stacked.csv", key="uc_rs_stk_dl")


def render_unit_tab():
    """Tab: Unit converter."""
    section_header("⚖️ Scientific Unit Converter", "Temperature, length, mass, and speed conversion.")

    category = st.selectbox("Category", ["Temperature", "Length / Distance", "Mass / Weight", "Speed / Velocity"], key="uc_unit_cat")
    value = st.number_input("Value", value=100.0, key="uc_unit_val")

    if category == "Temperature":
        from_units = ["Celsius", "Fahrenheit", "Kelvin"]
        to_units = from_units
    elif category in ("Length / Distance",):
        from_units = ["meters", "kilometers", "centimeters", "millimeters", "miles", "yards", "feet", "inches", "nautical_miles"]
        to_units = from_units
    elif category == "Mass / Weight":
        from_units = ["kilograms", "grams", "milligrams", "tonnes", "pounds", "ounces", "stones"]
        to_units = from_units
    else:
        from_units = ["m/s", "km/h", "mph", "knots"]
        to_units = from_units

    col_a, col_b = st.columns(2)
    with col_a:
        from_unit = st.selectbox("From", from_units, key="uc_unit_from")
    with col_b:
        to_unit = st.selectbox("To", to_units, key="uc_unit_to")

    cat_key = {"Temperature": "temperature", "Length / Distance": "length", "Mass / Weight": "mass", "Speed / Velocity": "speed"}[category]

    if st.button("⚖️ Convert", key="uc_unit_run", type="primary"):
        result = convert_unit(value, from_unit, to_unit, cat_key)
        if "error" in result:
            st.error(result["error"])
        else:
            st.success(f"{value:,.4f} {from_unit} = **{result['result']:,.6f}** {to_unit}")


def render_coord_tab():
    """Tab: Coordinate converter."""
    section_header("🗺️ Coordinate Converter", "Convert between Decimal Degrees and Degrees, Minutes, Seconds (DMS).")

    mode = st.radio("Mode", ["Decimal → DMS", "DMS → Decimal"], horizontal=True, key="uc_coord_mode")

    if mode == "Decimal → DMS":
        col_a, col_b = st.columns(2)
        with col_a:
            lat = st.number_input("Latitude (decimal)", value=0.3476, format="%.6f", key="uc_lat")
        with col_b:
            lon = st.number_input("Longitude (decimal)", value=32.5825, format="%.6f", key="uc_lon")
        if st.button("➡️ Convert to DMS", key="uc_to_dms", type="primary"):
            result = decimal_to_dms(lat, lon)
            st.success(result["formatted"])
            st.metric("Latitude DMS", result["lat_dms"])
            st.metric("Longitude DMS", result["lon_dms"])

    else:
        lat_dms = st.text_input("Latitude DMS", value="0°20′51.4″N", key="uc_dms_lat")
        lon_dms = st.text_input("Longitude DMS", value="32°34′57.0″E", key="uc_dms_lon")
        if st.button("➡️ Convert to Decimal", key="uc_to_dec", type="primary"):
            try:
                result = dms_to_decimal(lat_dms, lon_dms)
                st.success(result["formatted"])
                st.metric("Latitude", f"{result['lat']:.6f}")
                st.metric("Longitude", f"{result['lon']:.6f}")
            except Exception as e:
                st.error(f"Parse error: {e} — use format like `0°20′51.4″N`")


def render_pdf_tab():
    """Tab: PDF extraction."""
    section_header("📄 PDF Content Extractor", "Extract text and tables from PDF documents.")

    uploaded = st.file_uploader("Upload PDF", type=["pdf"], key="uc_pdf_upload")
    if uploaded is None:
        st.info("Upload a PDF to extract text.")
        return

    if st.button("📄 Extract PDF Text", key="uc_pdf_run", type="primary"):
        with st.spinner("Extracting..."):
            result = extract_pdf_text(uploaded.getvalue())
        st.metric("Pages", result.get("pages", "—"), delta=f"{result.get('extractor')}")
        st.metric("Characters", result.get("total_chars", "—"))
        text = result.get("text", "")
        if text.strip():
            st.text_area("Extracted text", value=text, height=300, key="uc_pdf_text")
            st.download_button("⬇️ Download Text", data=text.encode("utf-8"), file_name="extracted_pdf.txt", key="uc_pdf_dl")
        else:
            st.warning("No selectable text extracted (PDF may be scanned/image-based). Consider OCR.")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()  # paywall/trial gate, real DB check

    setup_page("Universal Converter", "🔄", initial_sidebar_state="expanded")

    hero_card(
        "🔄 Universal Converter & Utilities Studio",
        "Convert between 9+ data formats, encode/decode any payload, reshape data, convert scientific units & coordinates, and extract PDF content.",
        badge_text="UNIVERSAL CONVERTER • UTILITIES",
    )

    tabs = st.tabs([
        "📦 Formats",
        "🔤 Encoding",
        "🔀 Reshaper",
        "⚖️ Units",
        "🗺️ Coordinates",
        "📄 PDF",
    ])

    with tabs[0]:
        render_format_tab()
    with tabs[1]:
        render_encoding_tab()
    with tabs[2]:
        render_reshape_tab()
    with tabs[3]:
        render_unit_tab()
    with tabs[4]:
        render_coord_tab()
    with tabs[5]:
        render_pdf_tab()

    render_standard_footer("UNIVERSAL CONVERTER")


if __name__ == "__main__":
    main()
