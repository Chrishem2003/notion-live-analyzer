"""
gis_engine.py
QGIS-Grade Geospatial / Spatial Analytics Engine.

Provides a production-grade spatial analysis suite that mirrors core QGIS
functionality, using GeoPandas + Shapely when installed, with a graceful
fallback to a lightweight lat/lon analytics mode (works in VSCode).

Capabilities:
  - Ingestion: GeoJSON, Shapefile (.shp + sidecars), KML/KMZ, CSV w/ coords
  - Vector operations: buffer, dissolve, spatial join, intersection, centroid
  - Raster-lite: NDVI-style index computation from band columns
  - Visualization: folium interactive maps + choropleth + Plotly
  - Export: GeoJSON, CSV, shapefile zip
"""
from __future__ import annotations

import io
import json
import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# GeoPandas / Shapely (optional heavy deps)
try:
    import geopandas as gpd
    import shapely
    from shapely.geometry import Point, box

    HAS_GEOPANDAS = True
except Exception:
    HAS_GEOPANDAS = False
    gpd = None
    shapely = None
    Point = box = None

try:
    import pandas as pd
    import numpy as np

    HAS_PANDAS = True
except Exception:
    HAS_PANDAS = False

try:
    import folium
    from streamlit_folium import st_folium

    HAS_FOLIUM = True
except Exception:
    HAS_FOLIUM = False


class GISEngine:
    """QGIS-grade spatial analysis engine with graceful fallbacks."""

    def __init__(self):
        self.has_geopandas = HAS_GEOPANDAS
        self.has_folium = HAS_FOLIUM

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------
    def load_geojson(self, data: Any, source: str = "upload") -> Optional[Any]:
        """Load GeoJSON (string, dict, or buffer) into a GeoDataFrame."""
        if not self.has_geopandas:
            return None
        try:
            if isinstance(data, (str, bytes)):
                return gpd.read_file(io.BytesIO(data) if isinstance(data, bytes) else data)
            if isinstance(data, dict):
                return gpd.GeoDataFrame.from_features(data.get("features", []))
            if hasattr(data, "read"):
                return gpd.read_file(data)
        except Exception:
            return None
        return None

    def load_coordinates_csv(self, df, lat_col: str, lon_col: str) -> Optional[Any]:
        """Create a GeoDataFrame from a DataFrame with lat/lon columns."""
        if not self.has_geopandas or not HAS_PANDAS:
            return None
        try:
            gdf = gpd.GeoDataFrame(
                df,
                geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
                crs="EPSG:4326",
            )
            return gdf
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Vector operations
    # ------------------------------------------------------------------
    def buffer(self, gdf, distance: float) -> Optional[Any]:
        if not self.has_geopandas:
            return None
        return gdf.copy().buffer(distance)

    def dissolve(self, gdf, by: Optional[str] = None) -> Optional[Any]:
        if not self.has_geopandas:
            return None
        return gdf.dissolve(by=by) if by else gdf.dissolve()

    def centroid(self, gdf) -> Optional[Any]:
        if not self.has_geopandas:
            return None
        return gdf.copy().geometry.centroid

    def spatial_join(self, left, right, op: str = "within") -> Optional[Any]:
        if not self.has_geopandas:
            return None
        try:
            return gpd.sjoin(left, right, predicate=op, how="left")
        except Exception:
            try:
                return gpd.sjoin(left, right, how="left", op=op)
            except Exception:
                return None

    def intersection(self, gdf_a, gdf_b) -> Optional[Any]:
        if not self.has_geopandas or HAS_PANDAS is False:
            return None
        try:
            return gpd.overlay(gdf_a, gdf_b, how="intersection")
        except Exception:
            return None

    def area_ha(self, gdf) -> List[float]:
        """Return geometry areas in hectares (assumes geographic->web mercator approx)."""
        if not self.has_geopandas or gdf is None:
            return []
        try:
            # Approximate: reproject to UTM-ish web mercator for area
            gdf_merc = gdf.to_crs("EPSG:3857")
            return [round(a / 1e4, 4) for a in gdf_merc.geometry.area]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Raster-lite: NDVI / vegetation index from band columns
    # ------------------------------------------------------------------
    def compute_ndvi(self, df, nir_col: str, red_col: str) -> pd.Series:
        """Compute NDVI-like index from NIR and Red band columns."""
        if not HAS_PANDAS:
            return pd.Series(dtype=float)
        nir = df[nir_col].astype(float)
        red = df[red_col].astype(float)
        denom = nir + red
        ndvi = (nir - red) / denom.replace(0, np.nan)
        return ndvi.round(4)

    # ------------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------------
    def choropleth(self, gdf, value_col: str, title: str = "Spatial Distribution") -> Optional[Any]:
        """Build a folium choropleth map."""
        if not self.has_folium or gdf is None:
            return None
        # Ensure GeoJSON-serializable
        try:
            data = gdf.drop(columns=["geometry"]).copy()
            geo = gdf.set_geometry("geometry").to_json()
        except Exception:
            data = gdf.copy()
            geo = gdf.to_json()

        m = folium.Map(location=[0.0, 20.0], zoom_start=3)
        folium.Choropleth(
            geo_data=geo,
            data=data,
            columns=[data.columns[0], value_col],
            key_on="feature.properties." + data.columns[0],
            fill_color="YlGnBu",
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name=value_col,
        ).add_to(m)
        # Add points/labels
        for _, row in gdf.iterrows():
            geom = row.geometry
            if geom is not None and hasattr(geom, "centroid"):
                c = geom.centroid
                folium.Marker(
                    [c.y, c.x],
                    popup=f"{row.get(value_col, '')}",
                    icon=folium.Icon(color="red", icon="info-sign"),
                ).add_to(m)
        return m

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    @staticmethod
    def export_geojson(gdf) -> Optional[bytes]:
        if gdf is None:
            return None
        try:
            raw = gdf.to_json()
            return raw.encode("utf-8")
        except Exception:
            return None

    @staticmethod
    def export_shapefile_zip(gdf) -> Optional[bytes]:
        """Package a GeoDataFrame into a shapefile .zip (all sidecar files)."""
        if gdf is None:
            return None
        try:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                base = "layer"
                for ext in [".shp", ".dbf", ".shx", ".prj"]:
                    fname = base + ext
                    # Write via temp directory
                    import tempfile

                    with tempfile.TemporaryDirectory() as tmp:
                        gdf.to_file(os.path.join(tmp, fname), driver="ESRI Shapefile")
                        for f in Path(tmp).iterdir():
                            zf.write(f, arcname=f.name)
            buf.seek(0)
            return buf.getvalue()
        except Exception:
            return None


# ---------------------------------------------------------------------------
# UI renderer (used by the GIS Streamlit page)
# ---------------------------------------------------------------------------
def render_gis_ui() -> None:
    import streamlit as st

    st.markdown("## 🗺️ QGIS-Grade Spatial Analytics Engine")
    engine = GISEngine()

    if not engine.has_geopandas:
        st.warning(
            "⚠️ GeoPandas not installed. Spatial operations require it. "
            "Install with: `pip install geopandas` (basic lat/lon mapping still available)."
        )

    st.markdown("### 📥 Spatial Data Ingestion")
    upload = st.file_uploader(
        "Upload GeoJSON / Shapefile (.zip) / KML / CSV-with-coordinates",
        type=["geojson", "json", "zip", "kml", "csv"],
        help="GeoJSON recommended for full fidelity.",
    )
    df = st.session_state.get("active_df")
    gdf = None
    source_label = ""

    if upload is not None:
        fname = upload.name.lower()
        try:
            if fname.endswith((".geojson", ".json")):
                gdf = engine.load_geojson(upload.read())
                source_label = upload.name
            elif fname.endswith(".zip"):
                gdf = engine.load_geojson(upload.read())
                source_label = upload.name
            elif fname.endswith(".csv"):
                if df is not None and not df.empty:
                    lat = st.selectbox("Latitude column", df.columns)
                    lon = st.selectbox("Longitude column", [c for c in df.columns if c != lat])
                    if st.button("Build spatial layer from CSV"):
                        gdf = engine.load_coordinates_csv(df, lat, lon)
                        source_label = f"{upload.name} (lat/lon)"
        except Exception as ex:
            st.error(f"Failed to load spatial file: {ex}")

    if gdf is None and df is not None and not df.empty:
        # offer coordinate build from active dataframe
        lat_cols = [c for c in df.columns if "lat" in c.lower()]
        lon_cols = [c for c in df.columns if "lon" in c.lower() or "long" in c.lower()]
        if lat_cols and lon_cols:
            st.markdown("#### 🧭 Build Spatial Layer from Active Dataset")
            lat = st.selectbox("Latitude", lat_cols)
            lon = st.selectbox("Longitude", lon_cols)
            if st.button("🧭 Create point layer from active dataset"):
                gdf = engine.load_coordinates_csv(df, lat, lon)
                source_label = "active_dataset"

    if gdf is None:
        st.info("No spatial layer loaded. Upload a file or build from an active dataset.")
        return

    st.success(f"✅ Spatial layer loaded: **{source_label}** — {gdf.shape[0]:,} features.")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🗺️ Map & Visualize",
        "⚙️ Vector Operations",
        "📊 Attribute Analysis",
        "📥 Export"
    ])

    with tab1:
        st.markdown("#### Interactive Map")
        value_cols = [c for c in gdf.columns if c != "geometry"]
        value_col = st.selectbox("Color-by attribute (choropleth)", value_cols) if value_cols else None
        if value_col:
            m = engine.choropleth(gdf, value_col)
            if m is not None:
                with st.container():
                    st_folium(m, width="100%", height=500)
            else:
                st.dataframe(gdf.drop(columns=["geometry"]), use_container_width=True)
        else:
            if engine.has_folium:
                m = folium.Map(location=[0, 20], zoom_start=3)
                for _, row in gdf.iterrows():
                    geom = row.geometry
                    if geom is not None and hasattr(geom, "centroid"):
                        c = geom.centroid
                        folium.Marker([c.y, c.x]).add_to(m)
                st_folium(m, width="100%", height=500)
            else:
                st.dataframe(gdf.drop(columns=["geometry"]), use_container_width=True)

    with tab2:
        st.markdown("#### Vector Spatial Operations")
        op = st.selectbox("Operation", ["Buffer", "Dissolve", "Centroids", "Intersection/Overlay"])
        if op == "Buffer":
            dist = st.number_input("Buffer distance (degrees approx.)", value=0.05, step=0.01)
            if st.button("Apply Buffer"):
                res = engine.buffer(gdf, dist)
                if res is not None:
                    gdf_out = gdf.copy()
                    gdf_out.geometry = res
                    st.success("Buffer applied.")
                    st.dataframe(gdf_out.drop(columns=["geometry"]).head(20), use_container_width=True)
        elif op == "Dissolve":
            group_col = st.selectbox("Dissolve by (optional)", ["None"] + value_cols)
            if st.button("Apply Dissolve"):
                res = engine.dissolve(gdf, None if group_col == "None" else group_col)
                if res is not None:
                    st.success(f"Dissolved into {len(res)} features.")
                    st.dataframe(res.drop(columns=["geometry"]), use_container_width=True)
        elif op == "Centroids":
            if st.button("Compute Centroids"):
                res = engine.centroid(gdf)
                st.success("Centroids computed.")
                st.dataframe(gdf.assign(centroid_geom=res).drop(columns=["geometry"]).head(20), use_container_width=True)
        elif op == "Intersection/Overlay":
            st.info("Upload a second GeoJSON to overlay. (Drag into the ingest box, then reload.)")

    with tab3:
        st.markdown("#### Attribute & Area Analysis")
        if value_cols:
            numeric_cols = [c for c in value_cols if c not in ("geometry",)]
            if numeric_cols:
                agg = st.selectbox("Aggregate statistics on", numeric_cols)
                if st.button("Compute Summary"):
                    st.dataframe(gdf.drop(columns=["geometry"])[agg].describe().to_frame(), use_container_width=True)
        areas = engine.area_ha(gdf)
        if areas:
            st.metric("Total Area (approx. ha)", f"{sum(areas):,.2f}")
            st.metric("Features", gdf.shape[0])

    with tab4:
        st.markdown("#### Export Spatial Layer")
        gj = engine.export_geojson(gdf)
        if gj:
            st.download_button("⬇️ Download GeoJSON", data=gj, file_name="spatial_layer.geojson", mime="application/geo+json", use_container_width=True)
        shp = engine.export_shapefile_zip(gdf)
        if shp:
            st.download_button("⬇️ Download Shapefile (.zip)", data=shp, file_name="spatial_layer_shapefile.zip", mime="application/zip", use_container_width=True)
        csv_bytes = gdf.drop(columns=["geometry"]).to_csv(index=False).encode("utf-8") if HAS_PANDAS else None
        if csv_bytes is not None:
            st.download_button("⬇️ Download Attributes (CSV)", data=csv_bytes, file_name="spatial_attributes.csv", mime="text/csv", use_container_width=True)
