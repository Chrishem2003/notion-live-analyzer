"""
🔄 Universal Converter Studio — Enterprise Production Grade (Upgraded)
Comprehensive enterprise-grade conversion, reshaping, scientific unit conversion, geodesic coordinate transformation, 
and PDF content extraction engine with live batch processing, schema mapping, and robust error recovery.
"""

import io
import json
import datetime
import numpy as np
import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import hero_card, section_header, metric_card, render_export_buttons
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

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def _load_dataframe(uploaded):
    """Parse an uploaded file into a DataFrame with comprehensive format handling."""
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
        st.error(f"⚠️ Parsing Error: {e}")
    return None


def render_format_tab():
    section_header("📦 Enterprise Format Converter", "Convert structured datasets seamlessly between CSV, Excel, JSON, Parquet, XML, YAML, SQLite SQL, HTML, and Markdown.")

    uploaded = st.file_uploader("Upload source tabular or dataset file", type=["csv", "xlsx", "xls", "json", "parquet", "sav", "dta"], key="uc_fmt_upload_upg")
    if uploaded is None:
        st.info("ℹ️ Upload a structured data file to initiate conversion.")
        return

    df = _load_dataframe(uploaded)
    if df is None or df.empty:
        st.error("⚠️ Failed to parse uploaded file. Verify file schema and structure.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Rows", f"{df.shape[0]:,}")
    c2.metric("Total Columns", f"{df.shape[1]:,}")
    c3.metric("Memory Footprint", f"{df.memory_usage(deep=True).sum() / 1024:.2f} KB")

    st.markdown("#### Dataset Preview")
    st.dataframe(df.head(5), use_container_width=True, hide_index=True)

    target = st.selectbox("Target Output Format", [
        "CSV", "Excel (XLSX)", "JSON", "Parquet", "XML", "YAML", "SQL (SQLite)", "HTML", "Markdown",
    ], key="uc_fmt_target_upg")

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

    if st.button("🔄 Execute Format Conversion", key="uc_fmt_convert_upg", type="primary"):
        with st.spinner("Converting dataset schema and payload..."):
            data = convert_dataframe(df, fmt_map[target])
            out_name = uploaded.name.rsplit(".", 1)[0]
            st.success(f"✅ Conversion successful! Generated `{len(data):,}` bytes.")
            st.download_button(
                f"⬇️ Download Converted {target} File",
                data=data,
                file_name=f"{out_name}_converted.{ext_map[target]}",
                mime=mime_map[target],
                key="uc_fmt_dl_upg",
            )


def render_encoding_tab():
    section_header("🔤 Multi-Encoding & Payload Converter", "Encode and decode binary payloads, API secrets, and text blocks across Base64, Hex, URL Encoding, Binary, and ASCII85.")

    mode = st.radio("Operation Mode", ["Encode", "Descending Decode"], horizontal=True, key="uc_enc_mode_upg")
    source_text = st.text_area("Input Payload / Text String", placeholder="Enter raw text or encoded cipher payload...", height=160, key="uc_enc_input_upg")

    target_enc = st.selectbox("Encoding Scheme", ["Base64", "Hex", "URL Encoding", "Binary", "ASCII85"], key="uc_enc_type_upg")
    enc_map = {"Base64": "base64", "Hex": "hex", "URL Encoding": "url", "Binary": "binary", "ASCII85": "ascii85"}

    if st.button("⚡ Process Encoding Transformation", key="uc_enc_run_upg", type="primary"):
        if not source_text.strip():
            st.warning("⚠️ Please provide valid input payload.")
        else:
            raw = source_text.encode("utf-8")
            try:
                if mode == "Encode":
                    result = encode_data(raw, enc_map[target_enc])
                else:
                    result = decode_data(raw, enc_map[target_enc])
                result_text = result.decode("utf-8", errors="replace")
                st.success("✅ Transformation executed successfully.")
                st.text_area("Transformation Result Output", value=result_text, height=160, key="uc_enc_out_upg")
                st.download_button("⬇️ Download Result Payload", data=result, file_name="transformed_payload.txt", mime="text/plain", key="uc_enc_dl_upg")
            except Exception as e:
                st.error(f"🚨 Transformation Error: {e}")


def render_reshape_tab():
    section_header("🔀 Advanced Data Reshaping Studio", "Reshape analytical datasets between wide and long formats, pivot tables, transpose matrices, and stack column hierarchies.")

    uploaded = st.file_uploader("Upload dataset for restructuring", type=["csv", "xlsx", "json"], key="uc_rs_upload_upg")
    if uploaded is None:
        st.info("ℹ️ Upload a dataset to begin reshaping operations.")
        return

    df = _load_dataframe(uploaded)
    if df is None or df.empty:
        return

    operation = st.selectbox("Reshape Transformation Operator", ["Wide → Long (Melt)", "Long → Wide (Pivot)", "Transpose Matrix", "Stack Columns"], key="uc_rs_op_upg")

    if operation == "Wide → Long (Melt)":
        id_cols = st.multiselect("Identifier Columns (Retain)", df.columns.tolist(), key="uc_rs_ids_upg")
        all_cols = df.columns.tolist()
        val_cols = st.multiselect("Value Columns (Melt Target)", [c for c in all_cols if c not in id_cols], key="uc_rs_vals_upg")
        if st.button("↔ Execute Melt Transformation", key="uc_rs_melt_upg", type="primary"):
            result = wide_to_long(df, id_vars=id_cols or [], value_vars=val_cols or [])
            st.dataframe(result.head(20), use_container_width=True, hide_index=True)
            render_export_buttons(result, base_name="melted_long_format")

    elif operation == "Long → Wide (Pivot)":
        id_col = st.selectbox("Row Identifier Column", df.columns.tolist(), key="uc_rs_pid_upg")
        var_col = st.selectbox("Variable Column (Becomes Headers)", df.columns.tolist(), key="uc_rs_pvar_upg")
        val_col = st.selectbox("Value Aggregation Column", df.columns.tolist(), key="uc_rs_pval_upg")
        if st.button("↔ Execute Pivot Transformation", key="uc_rs_piv_upg", type="primary"):
            result = long_to_wide(df, id_col, var_col, val_col)
            st.dataframe(result.head(20), use_container_width=True, hide_index=True)
            render_export_buttons(result, base_name="pivoted_wide_format")

    elif operation == "Transpose Matrix":
        if st.button("↕ Execute Matrix Transposition", key="uc_rs_tp_upg", type="primary"):
            result = transpose_df(df)
            st.dataframe(result.head(20), use_container_width=True, hide_index=True)
            render_export_buttons(result, base_name="transposed_matrix")

    else:
        cols = st.multiselect("Select Columns to Stack", df.columns.tolist(), key="uc_rs_stack_upg")
        if st.button("📚 Execute Column Stacking", key="uc_rs_stk_upg", type="primary"):
            result = stack_columns(df, cols or list(df.columns))
            st.dataframe(result.head(20), use_container_width=True, hide_index=True)
            render_export_buttons(result, base_name="stacked_columns")


def render_unit_tab():
    section_header("⚖️ Scientific Unit & Measurement Converter", "Convert precision scientific measurements across temperature, length, mass, and velocity dimensions.")

    category = st.selectbox("Measurement Category", ["Temperature", "Length / Distance", "Mass / Weight", "Speed / Velocity"], key="uc_unit_cat_upg")
    value = st.number_input("Input Measurement Value", value=100.0, format="%.4f", key="uc_unit_val_upg")

    if category == "Temperature":
        from_units = ["Celsius", "Fahrenheit", "Kelvin"]
        to_units = from_units
    elif category == "Length / Distance":
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
        from_unit = st.selectbox("From Unit", from_units, key="uc_unit_from_upg")
    with col_b:
        to_unit = st.selectbox("To Unit", to_units, key="uc_unit_to_upg")

    cat_key = {"Temperature": "temperature", "Length / Distance": "length", "Mass / Weight": "mass", "Speed / Velocity": "speed"}[category]

    if st.button("⚖️ Calculate Conversion", key="uc_unit_run_upg", type="primary"):
        result = convert_unit(value, from_unit, to_unit, cat_key)
        if "error" in result:
            st.error(f"🚨 {result['error']}")
        else:
            st.success(f"✅ `{value:,.4f} {from_unit}` = **{result['result']:,.6f} {to_unit}**")


def render_coord_tab():
    section_header("🗺️ Geodetic Coordinate Transformation Studio", "Convert precision geographic coordinates between Decimal Degrees and Degrees, Minutes, Seconds (DMS) notation with interactive mapping.")

    mode = st.radio("Coordinate Mode", ["Decimal → DMS", "DMS → Decimal"], horizontal=True, key="uc_coord_mode_upg")

    if mode == "Decimal → DMS":
        col_a, col_b = st.columns(2)
        with col_a:
            lat = st.number_input("Latitude (Decimal Degrees)", value=0.3476, format="%.6f", key="uc_lat_upg")
        with col_b:
            lon = st.number_input("Longitude (Decimal Degrees)", value=32.5825, format="%.6f", key="uc_lon_upg")
        if st.button("➡️ Convert to DMS Format", key="uc_to_dms_upg", type="primary"):
            result = decimal_to_dms(lat, lon)
            st.success(f"Formatted: `{result['formatted']}`")
            c1, c2 = st.columns(2)
            c1.metric("Latitude (DMS)", result["lat_dms"])
            c2.metric("Longitude (DMS)", result["lon_dms"])
            st.map(pd.DataFrame([{"lat": lat, "lon": lon}]))

    else:
        lat_dms = st.text_input("Latitude DMS String", value="0°20′51.4″N", key="uc_dms_lat_upg")
        lon_dms = st.text_input("Longitude DMS String", value="32°34′57.0″E", key="uc_dms_lon_upg")
        if st.button("➡️ Convert to Decimal Degrees", key="uc_to_dec_upg", type="primary"):
            try:
                result = dms_to_decimal(lat_dms, lon_dms)
                st.success(f"Formatted: `{result['formatted']}`")
                c1, c2 = st.columns(2)
                c1.metric("Latitude (Decimal)", f"{result['lat']:.6f}")
                c2.metric("Longitude (Decimal)", f"{result['lon']:.6f}")
                st.map(pd.DataFrame([{"lat": result["lat"], "lon": result["lon"]}]))
            except Exception as e:
                st.error(f"🚨 Parse Error: {e} — ensure standard format like `0°20′51.4″N`")


def render_pdf_tab():
    section_header("📄 PDF Content & Text Extraction Engine", "Extract selectable text streams, document metadata, and tabular structures from PDF documents.")

    uploaded = st.file_uploader("Upload PDF document", type=["pdf"], key="uc_pdf_upload_upg")
    if uploaded is None:
        st.info("ℹ️ Upload a PDF document to extract text streams.")
        return

    if st.button("📄 Extract PDF Text Content", key="uc_pdf_run_upg", type="primary"):
        with st.spinner("Parsing document byte streams..."):
            result = extract_pdf_text(uploaded.getvalue())
        
        c1, c2 = st.columns(2)
        c1.metric("Total Pages", result.get("pages", "—"))
        c2.metric("Character Count", f"{result.get('total_chars', 0):,}")
        
        text = result.get("text", "")
        if text.strip():
            st.text_area("Extracted Document Text", value=text, height=320, key="uc_pdf_text_upg")
            st.download_button("⬇️ Download Extracted Text", data=text.encode("utf-8"), file_name="extracted_document_text.txt", mime="text/plain", key="uc_pdf_dl_upg")
        else:
            st.warning("⚠️ No selectable text extracted. The document may be scanned or image-based.")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()

    setup_page("Universal Converter", "🔄", initial_sidebar_state="expanded")

    hero_card(
        "🔄 Universal Converter & Utilities Studio — Enterprise Suite",
        "Enterprise-grade conversion suite supporting 9+ tabular formats, binary payload encoding, matrix reshaping, scientific unit transformations, geodetic coordinate conversion, and PDF text extraction.",
        badge_text="UNIVERSAL CONVERTER • UTILITIES STUDIO",
    )

    tabs = st.tabs([
        "📦 Format Converter",
        "🔤 Multi-Encoding",
        "🔀 Data Reshaper",
        "⚖️ Scientific Units",
        "🗺️ Coordinates",
        "📄 PDF Extractor",
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

    render_standard_footer("UNIVERSAL CONVERTER STUDIO")


if __name__ == "__main__":
    main()