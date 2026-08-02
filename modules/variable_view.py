
"""
SPSS Variable View Editor  manage variable labels, value labels, measurement levels,
missing values, and column properties like SPSS Variable View.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import streamlit as st
from modules.data_processor import infer_column_types

MEASUREMENT_LEVELS = ["Scale", "Ordinal", "Nominal"]
ROLES = ["Input", "Target", "Both", "None", "Partition", "Frequency", "Record ID"]

def create_variable_metadata(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Initialize or load variable metadata from session state."""
    if "variable_metadata" not in st.session_state or st.session_state["variable_metadata"] is None:
        metadata = {}
        col_types = infer_column_types(df)
        for col in df.columns:
            ctype = col_types.get(col, "unknown")
            # Determine default measurement level
            if ctype in ("numeric", "integer"):
                level = "Scale"
            elif ctype == "boolean":
                level = "Nominal"
            elif ctype == "temporal":
                level = "Scale"
            else:
                level = "Nominal"

            metadata[col] = {
                "label": col,
                "measurement_level": level,
                "role": "Input",
                "missing_values": [],
                "value_labels": {},
                "width": 8,
                "align": "left" if ctype in ("categorical", "string", "text") else "right",
                "decimals": 2 if ctype in ("numeric", "integer") else 0,
                "index": df.columns.get_loc(col),
            }
        st.session_state["variable_metadata"] = metadata
    return st.session_state["variable_metadata"]

def render_variable_view_editor(df: pd.DataFrame):
    """Render the SPSS-like Variable View editor UI."""
    metadata = create_variable_metadata(df)

    st.markdown("""
    <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
    .var-view-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    .var-view-table th { 
        background: rgba(29, 78, 216, 0.1); padding: 8px 6px; text-align: left; 
        font-weight: 700; border-bottom: 2px solid rgba(29, 78, 216, 0.3);
        position: sticky; top: 0; z-index: 10;
    }
    .var-view-table td { padding: 4px 6px; border-bottom: 1px solid rgba(0,0,0,0.05); }
    .var-view-table tr:hover td { background: rgba(29, 78, 216, 0.03); }
    .var-view-table input, .var-view-table select {
        border: 1px solid rgba(148,163,184,0.3); border-radius: 6px; padding: 3px 6px;
        font-size: 0.8rem; width: 100%; background: rgba(255,255,255,0.6);
    }
    </style>
    """, unsafe_allow_html=True)

    # Action buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
    with col1:
        if st.button("➕ Add Variable", use_container_width=True):
            new_name = f"var_{len(metadata)}"
            df[new_name] = None
            metadata[new_name] = {
                "label": new_name, "measurement_level": "Scale", "role": "Input",
                "missing_values": [], "value_labels": {},
                "width": 8, "align": "right", "decimals": 2, "index": len(metadata),
            }
            st.rerun()
    with col2:
        if st.button("✂️ Delete Selected", use_container_width=True):
            for col in list(metadata.keys()):
                if st.session_state.get(f"del_{col}"):
                    df.drop(columns=[col], inplace=True, errors="ignore")
                    del metadata[col]
                    st.rerun()
    with col3:
        if st.button("🔄 Reset Metadata", use_container_width=True):
            if "variable_metadata" in st.session_state:
                del st.session_state["variable_metadata"]
            st.rerun()

    # Build table
    html = [
        '<table class="var-view-table">',
        "<thead><tr>",
        "<th style='width:30px'>#</th>",
        "<th style='width:30px'>Del</th>",
        "<th>Name</th><th>Label</th><th>Type</th><th>Width</th><th>Decimals</th>",
        "<th>Measurement</th><th>Role</th><th>Missing</th><th>Values</th><th>Align</th>",
        "</tr></thead><tbody>"
    ]

    for idx, (col, meta) in enumerate(metadata.items()):
        ctype = str(df[col].dtype) if col in df.columns else "unknown"
        col_type_short = "numeric" if "float" in ctype or "int" in ctype else "string"

        html.append(f"<tr>")
        html.append(f"<td>{idx1}</td>")
        # Delete checkbox
        checked = "checked" if st.session_state.get(f"del_{col}") else ""
        html.append(f'<td><input type="checkbox" {"onchange" if not checked else ""} '
                    f'onclick="this.form.submit()" name="del_{col}" {checked}></td>')
        # Name
        html.append(f"<td><strong>{col}</strong></td>")
        # Label
        label_val = st.session_state.get(f"label_{col}", meta["label"])
        html.append(f'<td><input type="text" value="{label_val}" '
                    f'onchange="this.form.submit()" name="label_{col}"></td>')
        # Type
        html.append(f"<td>{col_type_short}</td>")
        # Width
        width_val = st.session_state.get(f"width_{col}", meta["width"])
        html.append(f'<td><input type="number" value="{width_val}" min="1" max="255" '
                    f'onchange="this.form.submit()" name="width_{col}" style="width:50px"></td>')
        # Decimals
        dec_val = st.session_state.get(f"dec_{col}", meta["decimals"])
        html.append(f'<td><input type="number" value="{dec_val}" min="0" max="10" '
                    f'onchange="this.form.submit()" name="dec_{col}" style="width:50px"></td>')
        # Measurement level
        measure_val = st.session_state.get(f"measure_{col}", meta["measurement_level"])
        measure_options = "".join(
            f'<option value="{m}" {"selected" if m == measure_val else ""}>{m}</option>'
            for m in MEASUREMENT_LEVELS
        )
        html.append(f'<td><select onchange="this.form.submit()" name="measure_{col}">{measure_options}</select></td>')
        # Role
        role_val = st.session_state.get(f"role_{col}", meta["role"])
        role_options = "".join(
            f'<option value="{r}" {"selected" if r == role_val else ""}>{r}</option>' for r in ROLES
        )
        html.append(f'<td><select onchange="this.form.submit()" name="role_{col}">{role_options}</select></td>')
        # Missing
        missing_str = ", ".join(str(m) for m in meta.get("missing_values", []))
        html.append(f'<td style="max-width:80px;overflow:hidden;text-overflow:ellipsis">{missing_str or ""}</td>')
        # Value labels
        vl = meta.get("value_labels", {})
        vl_str = ", ".join(f"{k}={v}" for k, v in list(vl.items())[:2])
        if len(vl) > 2:
            vl_str = "..."
        html.append(f'<td style="max-width:80px;overflow:hidden">{vl_str or ""}</td>')
        # Alignment
        align_val = st.session_state.get(f"align_{col}", meta["align"])
        align_options = "".join(
            f'<option value="{a}" {"selected" if a == align_val else ""}>{a}</option>'
            for a in ["left", "center", "right"]
        )
        html.append(f'<td><select onchange="this.form.submit()" name="align_{col}">{align_options}</select></td>')
        html.append("</tr>")

    html.append("</tbody></table>")
    st.markdown("\n".join(html), unsafe_allow_html=True)

    # Value Labels Editor (selected variable)
    st.markdown("---")
    st.subheader("🏷️ Value Labels Editor")
    val_label_col = st.selectbox("Select variable to edit value labels", options=list(metadata.keys()))
    if val_label_col:
        meta = metadata[val_label_col]
        st.caption(f"Editing value labels for: **{val_label_col}**  {meta.get('measurement_level', 'Scale')}")

        existing_labels = meta.get("value_labels", {})
        col1, col2 = st.columns([1, 3])
        with col1:
            val_key = st.text_input("Value", placeholder="e.g., 1", key="vl_key")
        with col2:
            val_label = st.text_input("Label", placeholder="e.g., Male", key="vl_label")

        if st.button("➕ Add/Update Label"):
            if val_key and val_label:
                existing_labels[val_key] = val_label
                meta["value_labels"] = existing_labels
                st.rerun()

        if existing_labels:
            st.markdown("**Current value labels:**")
            for k, v in existing_labels.items():
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"`{k}` → **{v}**")
                with c2:
                    if st.button(f"🗑️", key=f"del_vl_{val_label_col}_{k}"):
                        del existing_labels[k]
                        meta["value_labels"] = existing_labels
                        st.rerun()

    # Missing Values Editor
    st.markdown("---")
    st.subheader("⬜ Missing Values Editor")
    miss_col = st.selectbox("Select variable to define missing values", 
                            options=list(metadata.keys()), key="miss_col_select")
    if miss_col:
        meta = metadata[miss_col]
        current_missing = meta.get("missing_values", [])
        miss_input = st.text_input(
            "Missing values (comma-separated, e.g.: 999, -1, NA)",
            value=", ".join(str(m) for m in current_missing),
            key="miss_input"
        )
        if st.button("💾 Save Missing Values"):
            parsed = [m.strip() for m in miss_input.split(",") if m.strip()]
            meta["missing_values"] = parsed
            st.success(f"Saved missing values for {miss_col}: {parsed}")

    # Summary
    st.markdown("---")
    st.subheader(" Variable Summary")
    summary_data = []
    for col, meta in metadata.items():
        summary_data.append({
            "Variable": col,
            "Label": meta["label"],
            "Measurement": meta["measurement_level"],
            "Role": meta["role"],
            "Values": len(meta.get("value_labels", {})),
            "Missing Defs": len(meta.get("missing_values", [])),
        })
    if summary_data:
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)


def apply_variable_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Apply variable metadata transformations to DataFrame."""
    metadata = st.session_state.get("variable_metadata", {})
    if not metadata:
        return df

    df = df.copy()
    for col, meta in metadata.items():
        if col not in df.columns:
            continue
        # Apply value labels replacement (if values match)
        value_labels = meta.get("value_labels", {})
        if value_labels:
            reverse_map = {}
            for k, v in value_labels.items():
                try:
                    reverse_map[k] = v
                except Exception:
                    pass
            if reverse_map:
                # Try numeric keys first
                try:
                    numeric_map = {float(k) if "." in k else int(k): v for k, v in reverse_map.items()}
                    df[col] = df[col].replace(numeric_map)
                except (ValueError, TypeError):
                    df[col] = df[col].replace(reverse_map)

        # Apply missing values
        missing_vals = meta.get("missing_values", [])
        for mv in missing_vals:
            try:
                mv_converted = float(mv) if "." in mv else int(mv)
                df.loc[df[col] == mv_converted, col] = None
            except (ValueError, TypeError):
                df.loc[df[col] == mv, col] = None

    return df


