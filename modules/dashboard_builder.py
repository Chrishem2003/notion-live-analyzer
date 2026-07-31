"""
Dashboard Builder  interactive drag-and-drop dashboard creation tool.
Create custom multi-chart dashboards with cross-filtering.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import streamlit as st
import json
from datetime import datetime

from modules.chart_builder import build_chart
from modules.viz_engine import ALL_CHART_TYPES, auto_recommend_chart
from modules.data_processor import infer_column_types


class DashboardBuilder:
    """Interactive dashboard builder for creating custom multi-chart layouts."""

    @staticmethod
    def create_dashboard(
        df: pd.DataFrame,
        name: str = "My Dashboard",
        layout: str = "grid",
    ) -> Dict[str, Any]:
        """Create a new dashboard configuration."""
        return {
            "name": name,
            "layout": layout,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "charts": [],
            "filters": [],
            "settings": {
                "theme": "light",
                "show_title": True,
                "show_filters": True,
                "auto_refresh": False,
                "refresh_interval": 60,
            }
        }

    @staticmethod
    def add_chart(
        dashboard: Dict[str, Any],
        chart_type: str,
        title: str,
        params: Dict[str, Any],
        size: str = "medium",
        position: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Add a chart to the dashboard."""
        chart_config = {
            "id": f"chart_{len(dashboard['charts']) + 1}_{datetime.now().timestamp():.0f}",
            "type": chart_type,
            "title": title,
            "params": params,
            "size": size,
            "position": position if position is not None else len(dashboard['charts']),
        }
        dashboard["charts"].append(chart_config)
        dashboard["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return dashboard

    @staticmethod
    def remove_chart(dashboard: Dict[str, Any], chart_id: str) -> Dict[str, Any]:
        """Remove a chart from the dashboard."""
        dashboard["charts"] = [c for c in dashboard["charts"] if c.get("id") != chart_id]
        dashboard["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return dashboard

    @staticmethod
    def reorder_charts(dashboard: Dict[str, Any], chart_ids: List[str]) -> Dict[str, Any]:
        """Reorder charts based on provided list of IDs."""
        chart_map = {c["id"]: c for c in dashboard["charts"]}
        ordered = []
        for cid in chart_ids:
            if cid in chart_map:
                ordered.append(chart_map[cid])
        for c in dashboard["charts"]:
            if c["id"] not in chart_map:
                ordered.append(c)
        dashboard["charts"] = ordered
        dashboard["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return dashboard

    @staticmethod
    def add_filter(
        dashboard: Dict[str, Any],
        column: str,
        filter_type: str = "select",
    ) -> Dict[str, Any]:
        """Add a global filter to the dashboard."""
        filter_config = {
            "id": f"filter_{len(dashboard['filters']) + 1}",
            "column": column,
            "type": filter_type,
            "value": None,
        }
        dashboard["filters"].append(filter_config)
        dashboard["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return dashboard

    @staticmethod
    def apply_filters(df: pd.DataFrame, filters: List[Dict]) -> pd.DataFrame:
        """Apply global filters to a DataFrame."""
        filtered_df = df.copy()
        for f in filters:
            col = f.get("column")
            val = f.get("value")
            if col and col in filtered_df.columns and val is not None:
                if isinstance(val, list):
                    filtered_df = filtered_df[filtered_df[col].isin(val)]
                else:
                    filtered_df = filtered_df[filtered_df[col] == val]
        return filtered_df

    @staticmethod
    def save_dashboard(dashboard: Dict[str, Any], name: str = None) -> str:
        """Save dashboard configuration to session state."""
        if name:
            dashboard["name"] = name

        if "saved_dashboards" not in st.session_state:
            st.session_state["saved_dashboards"] = {}

        dash_name = dashboard.get("name", f"Dashboard_{len(st.session_state['saved_dashboards'])}")
        st.session_state["saved_dashboards"][dash_name] = dashboard
        return dash_name

    @staticmethod
    def load_dashboard(name: str) -> Optional[Dict[str, Any]]:
        """Load a saved dashboard configuration."""
        saved = st.session_state.get("saved_dashboards", {})
        return saved.get(name)

    @staticmethod
    def export_dashboard(dashboard: Dict[str, Any]) -> str:
        """Export dashboard as JSON string."""
        return json.dumps(dashboard, indent=2, default=str)

    @staticmethod
    def import_dashboard(json_str: str) -> Optional[Dict[str, Any]]:
        """Import dashboard from JSON string."""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None


# ─── UI ─────────────────────────────────────────────────────────────

def render_dashboard_builder_ui(df: pd.DataFrame):
    """Render the interactive dashboard builder UI."""
    st.markdown("## 📊 Interactive Dashboard Builder")
    st.markdown("*Create custom multi-chart dashboards with global filters*")

    if df is None or df.empty:
        st.warning("No data available. Load data first.")
        return

    # Initialize dashboard
    if "current_dashboard" not in st.session_state or st.session_state["current_dashboard"] is None:
        st.session_state["current_dashboard"] = DashboardBuilder.create_dashboard(df)

    dashboard = st.session_state["current_dashboard"]
    if dashboard is None:
        dashboard = DashboardBuilder.create_dashboard(df)
        st.session_state["current_dashboard"] = dashboard
    col_types = infer_column_types(df)
    all_cols = df.columns.tolist()

    # ─── Dashboard Controls ───────────────────────────────────────
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        dash_name = st.text_input("Dashboard name", value=dashboard.get("name", "My Dashboard"), key="dash_name")
        if dash_name != dashboard.get("name"):
            dashboard["name"] = dash_name
    with col2:
        layout = st.selectbox("Layout", options=["grid", "single_column", "two_column", "three_column"],
                              index=0, key="dash_layout")
        dashboard["layout"] = layout
    with col3:
        st.caption("")
        if st.button("💾 Save Dashboard", use_container_width=True):
            DashboardBuilder.save_dashboard(dashboard, dash_name)
            st.success(f"✅ Saved '{dash_name}'")
    with col4:
        st.caption("")
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state["current_dashboard"] = DashboardBuilder.create_dashboard(df)
            st.rerun()

    # ─── Saved Dashboards ─────────────────────────────────────────
    saved = st.session_state.get("saved_dashboards", {})
    if saved:
        with st.expander("📂 Load Saved Dashboard"):
            selected_dash = st.selectbox("Select dashboard", options=list(saved.keys()), key="load_dash")
            if st.button("📂 Load", use_container_width=True):
                loaded = DashboardBuilder.load_dashboard(selected_dash)
                if loaded:
                    st.session_state["current_dashboard"] = loaded
                    st.rerun()

    # ─── Add Chart ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("➕ Add Chart to Dashboard")

    col1, col2, col3 = st.columns(3)
    with col1:
        chart_type = st.selectbox("Chart type", options=ALL_CHART_TYPES, index=0,
                                  format_func=lambda x: x.replace("_", " ").title(), key="dash_chart_type")
    with col2:
        chart_title = st.text_input("Chart title", value="", placeholder="e.g., Sales by Region", key="dash_chart_title")
    with col3:
        chart_size = st.selectbox("Chart size", options=["small", "medium", "large"], index=1, key="dash_size")

    # Axis selections
    col1, col2, col3 = st.columns(3)
    with col1:
        x_col = st.selectbox("X-axis", options=[""] + all_cols, key="dash_x")
    with col2:
        y_col = st.selectbox("Y-axis", options=[""] + all_cols, key="dash_y")
    with col3:
        color_col = st.selectbox("Color by", options=[""] + all_cols, key="dash_color")

    if st.button("➕ Add to Dashboard", type="primary", use_container_width=True):
        params = {}
        if x_col: params["x"] = x_col
        if y_col: params["y"] = y_col
        if color_col: params["color"] = color_col
        params["height"] = {"small": 300, "medium": 430, "large": 550}.get(chart_size, 430)

        DashboardBuilder.add_chart(dashboard, chart_type, chart_title or f"{chart_type.replace('_', ' ').title()}", params, chart_size)
        st.success(f"✅ Added '{chart_title or chart_type}' to dashboard")

    # ─── Global Filters ────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔍 Global Filters")

    filter_col = st.selectbox("Add filter column", options=[""] + all_cols, key="dash_filter_col")
    if filter_col and st.button("➕ Add Filter", use_container_width=True):
        DashboardBuilder.add_filter(dashboard, filter_col)
        st.rerun()

    # Current filters
    if dashboard.get("filters"):
        for i, f in enumerate(dashboard["filters"]):
            col = f.get("column", "")
            c1, c2, c3 = st.columns([2, 3, 1])
            with c1:
                st.markdown(f"**{col}**")
            with c2:
                if col in df.columns:
                    unique_vals = df[col].dropna().unique().tolist()
                    if len(unique_vals) <= 20:
                        selected = st.selectbox("", options=["All"] + sorted([str(v) for v in unique_vals]),
                                                key=f"dash_filter_{i}")
                        f["value"] = None if selected == "All" else selected
                    else:
                        selected_range = st.select_slider("Range", options=["All", "Low", "Medium", "High"],
                                                          key=f"dash_filter_{i}")
                        f["value"] = selected_range
            with c3:
                if st.button("🗑️", key=f"dash_del_filter_{i}"):
                    dashboard["filters"].remove(f)
                    st.rerun()

    # ─── Render Dashboard ─────────────────────────────────────────
    st.markdown("---")
    st.subheader(f"📊 {dashboard.get('name', 'My Dashboard')}")

    # Apply filters
    active_filters = dashboard.get("filters", [])
    if active_filters:
        filtered_df = DashboardBuilder.apply_filters(df, active_filters)
        if len(filtered_df) < len(df):
            st.info(f"🔍 Filters active: showing {len(filtered_df)} of {len(df)} rows")
    else:
        filtered_df = df

    charts = dashboard.get("charts", [])

    if not charts:
        st.info("👆 Add charts to your dashboard using the controls above. You can also load a saved dashboard.")

        # Auto-recommend
        if st.button("🤖 Auto-Generate Starter Dashboard"):
            recs = auto_recommend_chart(df)[:6]
            for rec in recs:
                ct = rec.get("chart", "bar")
                params = {k: rec[k] for k in ("x", "y", "color", "size", "z", "path", "values", "dimensions")
                         if rec.get(k) is not None}
                params["height"] = 350
                DashboardBuilder.add_chart(
                    dashboard, ct, rec.get("reason", ct.replace("_", " ").title()),
                    params, "medium"
                )
            st.success("✅ Auto-generated 6 charts! Scroll down to view.")
            st.rerun()
    else:
        # Render charts based on layout
        layout_map = {
            "single_column": [1],
            "two_column": [2],
            "three_column": [3],
            "grid": [3, 2, 2],
        }
        cols_per_row = layout_map.get(dashboard.get("layout", "grid"), [3])

        chart_idx = 0
        for n_cols in cols_per_row:
            while chart_idx < len(charts):
                row_charts = charts[chart_idx:chart_idx + n_cols]
                if not row_charts:
                    break

                cols = st.columns(n_cols)
                for i, chart_config in enumerate(row_charts):
                    with cols[i]:
                        ct = chart_config.get("type", "bar")
                        title = chart_config.get("title", ct)
                        params = chart_config.get("params", {})

                        # Remove size-specific height if overridden
                        if "height" not in params:
                            params["height"] = {"small": 300, "medium": 400, "large": 500}.get(
                                chart_config.get("size", "medium"), 400
                            )

                        fig = build_chart(ct, filtered_df, **params)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info(f"Could not render: {title}")

                        # Chart controls
                        c1, c2 = st.columns(2)
                        with c1:
                            st.caption(title)
                        with c2:
                            if st.button("🗑️", key=f"dash_rm_{chart_config.get('id', chart_idx)}"):
                                DashboardBuilder.remove_chart(dashboard, chart_config.get("id", ""))
                                st.rerun()

                chart_idx += n_cols
                if chart_idx >= len(charts):
                    break

        # Export / Import
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export Dashboard JSON", use_container_width=True):
                json_str = DashboardBuilder.export_dashboard(dashboard)
                st.code(json_str, language="json")
                st.download_button("📥 Download", json_str, file_name=f"{dashboard.get('name', 'dashboard')}.json")
        with col2:
            uploaded_json = st.file_uploader("📂 Import Dashboard JSON", type=["json"], key="dash_import")
            if uploaded_json:
                imported = DashboardBuilder.import_dashboard(uploaded_json.read().decode())
                if imported:
                    st.session_state["current_dashboard"] = imported
                    st.success("✅ Dashboard imported!")
                    st.rerun()

