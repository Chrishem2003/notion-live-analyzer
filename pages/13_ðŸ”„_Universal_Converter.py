import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
"""
ðŸ”„ Universal Converter Studio â€” Enterprise Production Grade (Hardened & De-faked)
Comprehensive conversion, reshaping, scientific unit conversion, geodesic coordinate
transformation, PDF content extraction, and real batch multi-file conversion with strict error boundaries.
"""

import io
import json
import datetime
import zipfile
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
    """Parse an uploaded file into a DataFrame with robust extension checking and exception handling."""
    if uploaded is None:
        return None
    name_parts = uploaded.name.rsplit(".", 1)
    if len(name_parts) < 2:
        st.error("âš ï¸ Invalid filename: Missing file extension.")
        return None
    ext = name_parts[-1].lower()
    
    try:
        content_bytes = uploaded.getvalue()
        if not content_bytes:
            st.error("âš ï¸ The uploaded file contains 0 bytes.")
            return None

        if ext == "csv":
            return pd.read_csv(io.BytesIO(content_bytes), encoding="utf-8", low_memory=False)
        elif ext in ("xlsx", "xls"):
            return pd.read_excel(io.BytesIO(content_bytes))
        elif ext == "json":
            return pd.read_json(io.BytesIO(content_bytes))
        elif ext == "parquet":
            return pd.read_parquet(io.BytesIO(content_bytes))
        elif ext in ("sav", "sas7bdat", "dta"):
            import pyreadstat
            df, _ = {"sav": pyreadstat.read_sav, "sas7bdat": pyreadstat.read_sas7bdat, "dta": pyreadstat.read_dta}[ext](io.BytesIO(content_bytes))
            return df
        else:
            st.error(f"âš ï¸ Unsupported file extension: `.{ext}`")
            return None
    except Exception as e:
        st.error(f"âš ï¸ Parsing Error: {e}")
    return None


def render_format_tab():
    section_header("ðŸ“¦ Enterprise Format Converter", "Convert structured datasets seamlessly between CSV, Excel, JSON, Parquet, XML, YAML, SQLite SQL, HTML, and Markdown â€” single file or real batch mode.")

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

    mode = st.radio("Mode", ["Single File", "Batch (Multiple Files â†’ ZIP)"], horizontal=True, key="uc_fmt_mode")
    target = st.selectbox("Target Output Format", list(fmt_map.keys()), key="uc_fmt_target_upg")

    if mode == "Single File":
        uploaded = st.file_uploader("Upload source tabular or dataset file", type=["csv", "xlsx", "xls", "json", "parquet", "sav", "dta"], key="uc_fmt_upload_upg")
        if uploaded is None:
            st.info("â„¹ï¸ Upload a structured data file to initiate conversion.")
            return

        df = _load_dataframe(uploaded)
        if df is None or df.empty:
            st.error("âš ï¸ Failed to parse uploaded file. Verify file schema and structure.")
            return

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Rows", f"{df.shape[0]:,}")
        c2.metric("Total Columns", f"{df.shape[1]:,}")
        c3.metric("Memory Footprint", f"{df.memory_usage(deep=True).sum() / 1024:.2f} KB")

        st.markdown("#### Dataset Preview")
        st.dataframe(df.head(5), use_container_width=True, hide_index=True)

        if st.button("ðŸ”„ Execute Format Conversion", key="uc_fmt_convert_upg", type="primary"):
            with st.spinner("Converting dataset schema and payload..."):
                try:
                    data = convert_dataframe(df, fmt_map[target])
                    out_name = uploaded.name.rsplit(".", 1)[0]
                    st.success(f"âœ… Conversion successful! Generated `{len(data):,}` bytes.")
                    st.download_button(
                        f"â¬‡ï¸ Download Converted {target} File",
                        data=data,
                        file_name=f"{out_name}_converted.{ext_map[target]}",
                        mime=mime_map[target],
                        key="uc_fmt_dl_upg",
                    )
                except Exception as e:
                    st.error(f"ðŸš¨ Conversion Engine Error: {e}")
    else:
        uploaded_files = st.file_uploader(
            "Upload multiple source files", type=["csv", "xlsx", "xls", "json", "parquet", "sav", "dta"],
            accept_multiple_files=True, key="uc_fmt_batch_upload",
        )
        if not uploaded_files:
            st.info("â„¹ï¸ Upload two or more files to batch-convert them all to the target format in one ZIP.")
            return

        st.caption(f"{len(uploaded_files)} file(s) queued for conversion to {target}.")

        if st.button(f"ðŸ”„ Convert All {len(uploaded_files)} Files & Bundle ZIP", type="primary", key="uc_fmt_batch_convert"):
            zip_buffer = io.BytesIO()
            results = []
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for uf in uploaded_files:
                    df = _load_dataframe(uf)
                    if df is None or df.empty:
                        results.append({"File": uf.name, "Status": "âŒ Failed to parse"})
                        continue
                    try:
                        data = convert_dataframe(df, fmt_map[target])
                        out_name = f"{uf.name.rsplit('.', 1)[0]}_converted.{ext_map[target]}"
                        zf.writestr(out_name, data)
                        results.append({"File": uf.name, "Status": f"âœ… Converted ({len(data):,} bytes)"})
                    except Exception as e:
                        results.append({"File": uf.name, "Status": f"âŒ Error: {e}"})

            results_df = pd.DataFrame(results)
            st.dataframe(results_df, use_container_width=True, hide_index=True)

            success_count = sum(1 for r in results if r["Status"].startswith("âœ…"))
            if success_count:
                st.success(f"âœ… {success_count}/{len(uploaded_files)} file(s) converted successfully.")
                st.download_button(
                    f"â¬‡ï¸ Download Batch ZIP ({success_count} file(s))",
                    data=zip_buffer.getvalue(),
                    file_name=f"batch_converted_{target.lower().replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    key="uc_fmt_batch_dl",
                )
            else:
                st.error("ðŸš« No files converted successfully â€” check the status table above.")


def render_encoding_tab():
    section_header("ðŸ”¤ Multi-Encoding & Payload Converter", "Encode and decode binary payloads, API secrets, and text blocks across Base64, Hex, URL Encoding, Binary, and ASCII85.")

    mode = st.radio("Operation Mode", ["Encode", "Decode"], horizontal=True, key="uc_enc_mode_upg")
    source_text = st.text_area("Input Payload / Text String", placeholder="Enter raw text or encoded cipher payload...", height=160, key="uc_enc_input_upg")

    target_enc = st.selectbox("Encoding Scheme", ["Base64", "Hex", "URL Encoding", "Binary", "ASCII85"], key="uc_enc_type_upg")
    enc_map = {"Base64": "base64", "Hex": "hex", "URL Encoding": "url", "Binary": "binary", "ASCII85": "ascii85"}

    if st.button("âš¡ Process Encoding Transformation", key="uc_enc_run_upg", type="primary"):
        if not source_text.strip():
            st.warning("âš ï¸ Please provide valid input payload.")
        else:
            raw = source_text.encode("utf-8")
            try:
                if mode == "Encode":
                    result = encode_data(raw, enc_map[target_enc])
                else:
                    result = decode_data(raw, enc_map[target_enc])
                
                if isinstance(result, bytes):
                    result_text = result.decode("utf-8", errors="replace")
                else:
                    result_text = str(result)
                    result = result_text.encode("utf-8")

                st.success("âœ… Transformation executed successfully.")
                st.text_area("Transformation Result Output", value=result_text, height=160, key="uc_enc_out_upg")
                st.download_button("â¬‡ï¸ Download Result Payload", data=result, file_name="transformed_payload.txt", mime="text/plain", key="uc_enc_dl_upg")
            except Exception as e:
                st.error(f"ðŸš¨ Transformation Error: {e} â€” verify payload formatting.")


def render_reshape_tab():
    section_header("ðŸ”€ Advanced Data Reshaping Studio", "Reshape analytical datasets between wide and long formats, pivot tables, transpose matrices, and stack column hierarchies.")

    uploaded = st.file_uploader("Upload dataset for restructuring", type=["csv", "xlsx", "json"], key="uc_rs_upload_upg")
    if uploaded is None:
        st.info("â„¹ï¸ Upload a dataset to begin reshaping operations.")
        return

    df = _load_dataframe(uploaded)
    if df is None or df.empty:
        return

    operation = st.selectbox("Reshape Transformation Operator", ["Wide â†’ Long (Melt)", "Long â†’ Wide (Pivot)", "Transpose Matrix", "Stack Columns"], key="uc_rs_op_upg")

    if operation == "Wide â†’ Long (Melt)":
        id_cols = st.multiselect("Identifier Columns (Retain)", df.columns.tolist(), key="uc_rs_ids_upg")
        all_cols = df.columns.tolist()
        val_cols = st.multiselect("Value Columns (Melt Target)", [c for c in all_cols if c not in id_cols], key="uc_rs_vals_upg")
        if st.button("â†” Execute Melt Transformation", key="uc_rs_melt_upg", type="primary"):
            try:
                result = wide_to_long(df, id_vars=id_cols or [], value_vars=val_cols or [])
                st.dataframe(result.head(20), use_container_width=True, hide_index=True)
                render_export_buttons(result, base_name="melted_long_format")
            except Exception as e:
                st.error(f"ðŸš¨ Melt Error: {e}")

    elif operation == "Long â†’ Wide (Pivot)":
        id_col = st.selectbox("Row Identifier Column", df.columns.tolist(), key="uc_rs_pid_upg")
        var_col = st.selectbox("Variable Column (Becomes Headers)", df.columns.tolist(), key="uc_rs_pvar_upg")
        val_col = st.selectbox("Value Aggregation Column", df.columns.tolist(), key="uc_rs_pval_upg")
        if st.button("â†” Execute Pivot Transformation", key="uc_rs_piv_upg", type="primary"):
            try:
                result = long_to_wide(df, id_col, var_col, val_col)
                st.dataframe(result.head(20), use_container_width=True, hide_index=True)
                render_export_buttons(result, base_name="pivoted_wide_format")
            except Exception as e:
                st.error(f"ðŸš¨ Pivot Error: {e}")

    elif operation == "Transpose Matrix":
        if st.button("â†• Execute Matrix Transposition", key="uc_rs_tp_upg", type="primary"):
            try:
                result = transpose_df(df)
                st.dataframe(result.head(20), use_container_width=True, hide_index=True)
                render_export_buttons(result, base_name="transposed_matrix")
            except Exception as e:
                st.error(f"ðŸš¨ Transposition Error: {e}")

    else:
        cols = st.multiselect("Select Columns to Stack", df.columns.tolist(), key="uc_rs_stack_upg")
        if st.button("ðŸ“š Execute Column Stacking", key="uc_rs_stk_upg", type="primary"):
            try:
                result = stack_columns(df, cols or list(df.columns))
                st.dataframe(result.head(20), use_container_width=True, hide_index=True)
                render_export_buttons(result, base_name="stacked_columns")
            except Exception as e:
                st.error(f"ðŸš¨ Stacking Error: {e}")


def render_unit_tab():
    section_header("âš–ï¸ Scientific Unit & Measurement Converter", "Convert precision scientific measurements across temperature, length, mass, and velocity dimensions.")

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

    if st.button("âš–ï¸ Calculate Conversion", key="uc_unit_run_upg", type="primary"):
        try:
            result = convert_unit(value, from_unit, to_unit, cat_key)
            if not result or "error" in result:
                st.error(f"ðŸš¨ {result.get('error', 'Conversion calculation failed.')}")
            else:
                st.success(f"âœ… `{value:,.4f} {from_unit}` = **{result['result']:,.6f} {to_unit}**")
        except Exception as e:
            st.error(f"ðŸš¨ Unit Engine Exception: {e}")


def render_coord_tab():
    section_header("ðŸ—ºï¸ Geodetic Coordinate Transformation Studio", "Convert precision geographic coordinates between Decimal Degrees and Degrees, Minutes, Seconds (DMS) notation with interactive mapping.")

    mode = st.radio("Coordinate Mode", ["Decimal â†’ DMS", "DMS â†’ Decimal"], horizontal=True, key="uc_coord_mode_upg")

    if mode == "Decimal â†’ DMS":
        col_a, col_b = st.columns(2)
        with col_a:
            lat = st.number_input("Latitude (Decimal Degrees)", value=0.3476, format="%.6f", key="uc_lat_upg")
        with col_b:
            lon = st.number_input("Longitude (Decimal Degrees)", value=32.5825, format="%.6f", key="uc_lon_upg")
        if st.button("âž¡ï¸ Convert to DMS Format", key="uc_to_dms_upg", type="primary"):
            try:
                result = decimal_to_dms(lat, lon)
                st.success(f"Formatted: `{result.get('formatted', '')}`")
                c1, c2 = st.columns(2)
                c1.metric("Latitude (DMS)", result.get("lat_dms", "â€”"))
                c2.metric("Longitude (DMS)", result.get("lon_dms", "â€”"))
                st.map(pd.DataFrame([{"lat": lat, "lon": lon}]))
            except Exception as e:
                st.error(f"ðŸš¨ Geodetic Conversion Error: {e}")

    else:
        lat_dms = st.text_input("Latitude DMS String", value="0Â°20â€²51.4â€³N", key="uc_dms_lat_upg")
        lon_dms = st.text_input("Longitude DMS String", value="32Â°34â€²57.0â€³E", key="uc_dms_lon_upg")
        if st.button("âž¡ï¸ Convert to Decimal Degrees", key="uc_to_dec_upg", type="primary"):
            try:
                result = dms_to_decimal(lat_dms, lon_dms)
                st.success(f"Formatted: `{result.get('formatted', '')}`")
                c1, c2 = st.columns(2)
                lat_val = result.get("lat", 0.0)
                lon_val = result.get("lon", 0.0)
                c1.metric("Latitude (Decimal)", f"{lat_val:.6f}")
                c2.metric("Longitude (Decimal)", f"{lon_val:.6f}")
                st.map(pd.DataFrame([{"lat": lat_val, "lon": lon_val}]))
            except Exception as e:
                st.error(f"ðŸš¨ Parse Error: {e} â€” ensure standard format like `0Â°20â€²51.4â€³N`")


def render_pdf_tab():
    section_header("ðŸ“„ PDF Content & Text Extraction Engine", "Extract selectable text streams, document metadata, and tabular structures from PDF documents.")

    uploaded = st.file_uploader("Upload PDF document", type=["pdf"], key="uc_pdf_upload_upg")
    if uploaded is None:
        st.info("â„¹ï¸ Upload a PDF document to extract text streams.")
        return

    if st.button("ðŸ“„ Extract PDF Text Content", key="uc_pdf_run_upg", type="primary"):
        with st.spinner("Parsing document byte streams..."):
            try:
                result = extract_pdf_text(uploaded.getvalue()) or {}
            except Exception as e:
                st.error(f"ðŸš¨ PDF Engine Error: {e}")
                return

        c1, c2 = st.columns(2)
        c1.metric("Total Pages", result.get("pages", "â€”"))
        c2.metric("Character Count", f"{result.get('total_chars', 0):,}")

        text = result.get("text", "")
        if text.strip():
            st.text_area("Extracted Document Text", value=text, height=320, key="uc_pdf_text_upg")
            st.download_button("â¬‡ï¸ Download Extracted Text", data=text.encode("utf-8"), file_name="extracted_document_text.txt", mime="text/plain", key="uc_pdf_dl_upg")
        else:
            st.warning("âš ï¸ No selectable text extracted. The document may be scanned or image-based.")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription(hub_id="converter")

    setup_page("Universal Converter", "ðŸ”„", initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "ðŸ”„ Universal Converter & Utilities Studio â€” Hardened Production Suite",
        "Conversion suite supporting 9+ tabular formats with real batch mode, binary payload encoding, matrix reshaping, scientific unit transformations, geodetic coordinate conversion, and PDF text extraction.",
        badge_text="UNIVERSAL CONVERTER â€¢ HARDENED SUITE",
    )

    tabs = st.tabs([
        "ðŸ“¦ Format Converter",
        "ðŸ”¤ Multi-Encoding",
        "ðŸ”€ Data Reshaper",
        "âš–ï¸ Scientific Units",
        "ðŸ—ºï¸ Coordinates",
        "ðŸ“„ PDF Extractor",
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
