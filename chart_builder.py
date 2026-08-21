
"""
Chart Builder  builds 18 interactive chart types using Plotly.
Handles all configuration, theming, and rendering.
Research-grade publication-ready visualizations.
"""
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from modules.config import RESEARCH_PALETTES, PUBLICATION_CONFIG

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Research Color Palette Loading Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
def get_color_palette(palette_name: str = "Plotly") -> list:
    """Get a color palette by name  includes research journal palettes."""
    palettes = {
        "Plotly": px.colors.qualitative.Plotly,
        "Set2": px.colors.qualitative.Set2,
        "Pastel": px.colors.qualitative.Pastel,
        "Dark2": px.colors.qualitative.Dark2,
        "Bold": px.colors.qualitative.Bold,
        "Safe": px.colors.qualitative.Safe,
        "Vivid": px.colors.qualitative.Vivid,
        "Alphabet": px.colors.qualitative.Alphabet,
        "Antique": px.colors.qualitative.Antique,
        "Prism": px.colors.qualitative.Prism,
        "Viridis": px.colors.sequential.Viridis,
        "Plasma": px.colors.sequential.Plasma,
        "Inferno": px.colors.sequential.Inferno,
        "Magma": px.colors.sequential.Magma,
        "Cividis": px.colors.sequential.Cividis,
        **RESEARCH_PALETTES,  # Inject all research palettes
    }
    return palettes.get(palette_name, px.colors.qualitative.Plotly)

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Publication-Ready Theming Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
PC = PUBLICATION_CONFIG

def _spine_style(fig: go.Figure) -> go.Figure:
    """Apply clean axis spine styling (Nature/Science style)."""
    fig.update_xaxes(
        showline=True, linewidth=PC["axis_line_width"],
        linecolor=PC["axis_line_color"],
        mirror=False,
        ticks="outside", tickwidth=1, ticklen=5,
        tickcolor=PC["axis_line_color"],
    )
    fig.update_yaxes(
        showline=True, linewidth=PC["axis_line_width"],
        linecolor=PC["axis_line_color"],
        mirror=False,
        ticks="outside", tickwidth=1, ticklen=5,
        tickcolor=PC["axis_line_color"],
    )
    return fig

def _clean_grid(fig: go.Figure) -> go.Figure:
    """Apply subtle thin grid lines (Science-style)."""
    fig.update_xaxes(
        showgrid=True, gridwidth=PC["grid_width"],
        gridcolor=PC["grid_color"], zeroline=False,
    )
    fig.update_yaxes(
        showgrid=True, gridwidth=PC["grid_width"],
        gridcolor=PC["grid_color"], zeroline=False,
    )
    return fig

def _professional_hover(fig: go.Figure) -> go.Figure:
    """Apply clean hover template."""
    fig.update_layout(
        hoverlabel=dict(
            font_size=PC["hoverlabel_font_size"],
            font_family=PC["font_family"],
            bordercolor="rgba(128,128,128,0.3)",
        ),
        hovermode="closest",
    )
    return fig

def apply_publication_theme(fig: go.Figure, title: str = None) -> go.Figure:
    """Apply full publication-ready theme to any figure."""
    fig.update_layout(
        font=dict(
            family=PC["font_family"],
            size=PC["font_size_axis_ticks"],
        ),
        title=dict(
            text=title,
            font=dict(size=PC["font_size_title"], weight=600),
            x=0.02,  # Left-aligned title like Nature/Science
            xanchor="left",
            y=0.97,
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(
            l=PC["margin_l"], r=PC["margin_r"],
            t=PC["margin_t"], b=PC["margin_b"],
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
            font=dict(size=PC["font_size_legend"]),
            bordercolor="rgba(128,128,128,0.15)",
            borderwidth=1,
        ),
    )
    fig = _spine_style(fig)
    fig = _clean_grid(fig)
    fig = _professional_hover(fig)
    return fig

def apply_research_theme(fig: go.Figure, journal: str = "Nature") -> go.Figure:
    """Apply a specific journal-style theme to a figure."""
    journal_themes = {
        "Nature": dict(
            font=dict(family="Inter, sans-serif", size=12, color="#333333"),
            plot_bgcolor="rgba(248,249,250,0.3)",
            paper_bgcolor="rgba(255,255,255,0)",
        ),
        "Science": dict(
            font=dict(family="Inter, sans-serif", size=12, color="#222222"),
            plot_bgcolor="rgba(255,255,255,0)",
            paper_bgcolor="rgba(255,255,255,0)",
        ),
        "The Lancet": dict(
            font=dict(family="'Times New Roman', Georgia, serif", size=12, color="#1a1a1a"),
            plot_bgcolor="rgba(255,255,255,0)",
            paper_bgcolor="rgba(255,255,255,0)",
        ),
        "JAMA": dict(
            font=dict(family="'IBM Plex Sans', Inter, sans-serif", size=11, color="#1a1a1a"),
            plot_bgcolor="rgba(255,255,255,0)",
            paper_bgcolor="rgba(255,255,255,0)",
        ),
    }
    theme = journal_themes.get(journal, {})
    if theme:
        fig.update_layout(**theme)
    return fig

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Base Theme Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
CHART_THEME = {
    "font": dict(family="Inter, -apple-system, BlinkMacSystemFont, sans-serif"),
    "plot_bgcolor": "rgba(0,0,0,0)",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "margin": dict(l=10, r=10, t=30, b=10),
}

def dark_theme_overrides():
    """Apply dark theme overrides."""
    return {
        "font": dict(family="Inter, sans-serif", color="#e2e8f0"),
        "plot_bgcolor": "rgba(15, 23, 42, 0.3)",
        "paper_bgcolor": "rgba(0,0,0,0)",
    }

def apply_theme(fig: go.Figure, is_dark: bool = False, publication: bool = True,
                journal: str = None, title: str = None) -> go.Figure:
    """Apply consistent theming  optionally with publication-grade styling."""
    if publication:
        fig = apply_publication_theme(fig, title=title)
        if journal:
            fig = apply_research_theme(fig, journal)
    else:
        theme = dark_theme_overrides() if is_dark else CHART_THEME
        fig.update_layout(**theme)
        fig = _clean_grid(fig)
    return fig

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Chart Builder Functions Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

def build_bar(df, x=None, y=None, color=None, barmode="group", orientation="v", **kwargs):
    """Bar chart  grouped, stacked, or horizontal."""
    if x and y:
        fig = px.bar(
            df, x=x, y=y, color=color,
            barmode=barmode, orientation=orientation,
            text_auto=True, template="plotly_white",
            color_discrete_sequence=get_color_palette(kwargs.get("palette", "Plotly")),
            height=kwargs.get("height", 430),
        )
    elif x:
        # Frequency bar
        freq_df = df[x].value_counts().reset_index()
        freq_df.columns = [x, "count"]
        fig = px.bar(
            freq_df, x=x, y="count",
            text_auto=True, template="plotly_white",
            color_discrete_sequence=get_color_palette(kwargs.get("palette", "Plotly")),
            height=kwargs.get("height", 430),
        )
    else:
        return None
    fig.update_layout(
        xaxis_title=kwargs.get("x_label", x),
        yaxis_title=kwargs.get("y_label", y or "Count"),
    )
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False),
                       title=kwargs.get("title"),
                       journal=kwargs.get("journal"))

def build_line(df, x=None, y=None, color=None, **kwargs):
    """Line chart with optional confidence bands."""
    if not x or not y:
        return None

    fig = px.line(
        df, x=x, y=y, color=color,
        markers=True, template="plotly_white",
        color_discrete_sequence=get_color_palette(kwargs.get("palette", "Plotly")),
        height=kwargs.get("height", 430),
    )
    fig.update_traces(line=dict(width=2.5))
    fig.update_layout(
        title=kwargs.get("title", None),
        xaxis_title=kwargs.get("x_label", x),
        yaxis_title=kwargs.get("y_label", y),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_pie(df, names=None, values=None, **kwargs):
    """Pie / Donut chart."""
    if names and values:
        fig = px.pie(
            df, names=names, values=values,
            hole=0 if kwargs.get("style") == "pie" else 0.45,
            template="plotly_white",
            color_discrete_sequence=get_color_palette(kwargs.get("palette", "Pastel")),
            height=kwargs.get("height", 430),
        )
    elif names:
        # Frequency pie
        freq_df = df[names].value_counts().reset_index()
        freq_df.columns = [names, "count"]
        fig = px.pie(
            freq_df, names=names, values="count",
            hole=0.45, template="plotly_white",
            color_discrete_sequence=get_color_palette(kwargs.get("palette", "Pastel")),
            height=kwargs.get("height", 430),
        )
    else:
        return None
    fig.update_traces(textposition="inside", textinfo="percentlabel")
    fig.update_layout(
        title=kwargs.get("title", None),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
    )
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_histogram(df, x=None, **kwargs):
    """Histogram with optional KDE overlay."""
    if not x:
        return None
    fig = px.histogram(
        df, x=x, nbins=kwargs.get("nbins", 30),
        marginal=kwargs.get("marginal", "box"),
        template="plotly_white",
        color_discrete_sequence=get_color_palette(kwargs.get("palette", "Plotly")),
        height=kwargs.get("height", 430),
        opacity=0.8,
    )
    fig.update_layout(
        title=kwargs.get("title", f"Distribution of {x}}"),
        xaxis_title=kwargs.get("x_label", x),
        yaxis_title="Frequency",
        bargap=0.05,
    )
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_scatter(df, x=None, y=None, color=None, size=None, **kwargs):
    """Scatter plot with optional trendline."""
    if not x or not y:
        return None
    fig = px.scatter(
        df, x=x, y=y, color=color, size=size,
        trendline=kwargs.get("trendline", "ols"),
        template="plotly_white",
        color_discrete_sequence=get_color_palette(kwargs.get("palette", "Plotly")),
        height=kwargs.get("height", 430),
        opacity=0.7,
    )
    fig.update_layout(
        title=kwargs.get("title", f"{y}} vs {x}}"),
        xaxis_title=kwargs.get("x_label", x),
        yaxis_title=kwargs.get("y_label", y),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_bubble(df, x=None, y=None, size=None, color=None, **kwargs):
    """Bubble chart."""
    if not x or not y or not size:
        return None
    fig = px.scatter(
        df, x=x, y=y, size=size, color=color,
        size_max=60, template="plotly_white",
        color_discrete_sequence=get_color_palette(kwargs.get("palette", "Plotly")),
        height=kwargs.get("height", 430),
        opacity=0.7,
    )
    fig.update_layout(
        title=kwargs.get("title", f"Bubble: {x}} vs {y}} (size: {size}})"),
        xaxis_title=kwargs.get("x_label", x),
        yaxis_title=kwargs.get("y_label", y),
    )
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_area(df, x=None, y=None, color=None, **kwargs):
    """Area chart."""
    if not x or not y:
        return None
    fig = px.area(
        df, x=x, y=y, color=color,
        template="plotly_white", groupnorm=kwargs.get("groupnorm", None),
        color_discrete_sequence=get_color_palette(kwargs.get("palette", "Plotly")),
        height=kwargs.get("height", 430),
    )
    fig.update_layout(
        title=kwargs.get("title", None),
        xaxis_title=kwargs.get("x_label", x),
        yaxis_title=kwargs.get("y_label", y),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_box(df, x=None, y=None, color=None, **kwargs):
    """Box plot."""
    if y:
        fig = px.box(
            df, x=x, y=y, color=color,
            template="plotly_white", points="outliers",
            color_discrete_sequence=get_color_palette(kwargs.get("palette", "Plotly")),
            height=kwargs.get("height", 430),
        )
    else:
        return None
    fig.update_layout(
        title=kwargs.get("title", f"Box Plot of {y}}"),
        xaxis_title=kwargs.get("x_label", x),
        yaxis_title=kwargs.get("y_label", y),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_violin(df, x=None, y=None, color=None, **kwargs):
    """Violin plot."""
    if not y:
        return None
    fig = px.violin(
        df, x=x, y=y, color=color,
        box=True, points="outliers",
        template="plotly_white",
        color_discrete_sequence=get_color_palette(kwargs.get("palette", "Plotly")),
        height=kwargs.get("height", 430),
    )
    fig.update_layout(
        title=kwargs.get("title", f"Violin Plot of {y}}"),
        xaxis_title=kwargs.get("x_label", x),
        yaxis_title=kwargs.get("y_label", y),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_heatmap(df, x=None, y=None, z=None, **kwargs):
    """Heatmap."""
    if x and y and z:
        pivot = df.pivot_table(index=y, columns=x, values=z, aggfunc="mean")
        fig = px.imshow(
            pivot, text_auto=True, aspect="auto",
            color_continuous_scale=kwargs.get("colorscale", "RdBu_r"),
            template="plotly_white",
            height=kwargs.get("height", 500),
        )
    else:
        # Correlation heatmap
        corr = df.select_dtypes(include=[np.number]).corr()
        if corr.empty:
            return None
        fig = px.imshow(
            corr, text_auto=".2f", aspect="auto",
            color_continuous_scale=kwargs.get("colorscale", "RdBu_r"),
            template="plotly_white",
            height=kwargs.get("height", 500),
            zmin=-1, zmax=1,
        )
    fig.update_layout(title=kwargs.get("title", "Heatmap"))
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_treemap(df, path=None, values=None, color=None, **kwargs):
    """Treemap."""
    if not path:
        return None
    fig = px.treemap(
        df, path=path, values=values, color=color,
        template="plotly_white",
        color_continuous_scale=kwargs.get("colorscale", "Viridis"),
        height=kwargs.get("height", 500),
    )
    fig.update_traces(textinfo="labelvaluepercent root")
    fig.update_layout(title=kwargs.get("title", "Treemap"))
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_sunburst(df, path=None, values=None, color=None, **kwargs):
    """Sunburst chart."""
    if not path:
        return None
    fig = px.sunburst(
        df, path=path, values=values, color=color,
        template="plotly_white",
        color_continuous_scale=kwargs.get("colorscale", "Viridis"),
        height=kwargs.get("height", 500),
    )
    fig.update_traces(textinfo="labelvaluepercent root")
    fig.update_layout(title=kwargs.get("title", "Sunburst"))
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_radar(df, categories=None, values=None, color=None, **kwargs):
    """Radar / Spider chart."""
    if not categories:
        return None
    if color:
        fig = px.line_polar(
            df, r=values, theta=categories, color=color,
            line_close=True, template="plotly_white",
            color_discrete_sequence=get_color_palette(kwargs.get("palette", "Plotly")),
            height=kwargs.get("height", 500),
        )
    else:
        fig = px.line_polar(
            df, r=values, theta=categories,
            line_close=True, template="plotly_white",
            height=kwargs.get("height", 500),
        )
    fig.update_traces(fill="toself", opacity=0.6)
    fig.update_layout(title=kwargs.get("title", "Radar Chart"))
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_scatter_3d(df, x=None, y=None, z=None, color=None, **kwargs):
    """3D Scatter plot."""
    if not x or not y or not z:
        return None
    fig = px.scatter_3d(
        df, x=x, y=y, z=z, color=color,
        template="plotly_white",
        color_discrete_sequence=get_color_palette(kwargs.get("palette", "Plotly")),
        height=kwargs.get("height", 550),
        opacity=0.8,
    )
    fig.update_layout(
        title=kwargs.get("title", f"3D: {x}}, {y}}, {z}}"),
        scene=dict(
            xaxis_title=x, yaxis_title=y, zaxis_title=z,
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_parallel_coordinates(df, dimensions=None, color=None, **kwargs):
    """Parallel coordinates plot."""
    if not dimensions:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        dimensions = numeric_cols
        if len(dimensions) < 2:
            return None
    fig = px.parallel_coordinates(
        df, dimensions=dimensions, color=color or dimensions[0],
        template="plotly_white",
        color_continuous_scale=kwargs.get("colorscale", "Viridis"),
        height=kwargs.get("height", 500),
    )
    fig.update_layout(title=kwargs.get("title", "Parallel Coordinates"))
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_waterfall(df, x=None, y=None, **kwargs):
    """Waterfall chart."""
    if not x or not y:
        return None
    fig = go.Figure(go.Waterfall(
        x=df[x],
        y=df[y],
        text=[f"{v:,}}" if "<change>" in str(k) else str(v) for k, v in zip(df[x], df[y])],
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
    ))
    fig.update_layout(
        title=kwargs.get("title", "Waterfall Chart"),
        xaxis_title=kwargs.get("x_label", x),
        yaxis_title=kwargs.get("y_label", y),
        height=kwargs.get("height", 430),
        template="plotly_white",
    )
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_funnel(df, x=None, y=None, **kwargs):
    """Funnel chart."""
    if not x or not y:
        return None
    fig = px.funnel(
        df, x=x, y=y,
        template="plotly_white",
        color_discrete_sequence=get_color_palette(kwargs.get("palette", "Plotly")),
        height=kwargs.get("height", 430),
    )
    fig.update_traces(textinfo="valuepercent previous")
    fig.update_layout(title=kwargs.get("title", "Funnel Chart"))
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

def build_gauge(df, value_col=None, **kwargs):
    """Gauge / Speedometer chart for a single value."""
    if value_col is None:
        value = kwargs.get("value", 50)
        title = kwargs.get("title", "Gauge")
    else:
        value = float(df[value_col].mean()) if not df[value_col].isna().all() else 0
        title = kwargs.get("title", f"Average {value_col}}")

    fig = go.Figure(go.Indicator(
        mode="gaugenumberdelta",
        value=value,
        delta={"reference": kwargs.get("reference", 0)},
        gauge={
            "axis": {"range": [kwargs.get("min", 0), kwargs.get("max", 100)]},
            "bar": {"color": kwargs.get("color", "#1d4ed8")},
            "steps": [
                {"range": [0, 33], "color": "rgba(255,100,100,0.15)"},
                {"range": [33, 66], "color": "rgba(255,255,100,0.15)"},
                {"range": [66, 100], "color": "rgba(100,255,100,0.15)"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": kwargs.get("threshold", 80),
            },
        },
    ))
    fig.update_layout(
        title=dict(text=title, x=0.5),
        height=kwargs.get("height", 350),
        template="plotly_white",
    )
    return apply_theme(fig, is_dark=kwargs.get("is_dark", False), title=kwargs.get("title"), journal=kwargs.get("journal"))

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Chart Factory Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
CHART_BUILDERS = {
    "bar": build_bar,
    "grouped_bar": build_bar,
    "stacked_bar": build_bar,
    "horizontal_bar": build_bar,
    "line": build_line,
    "pie": build_pie,
    "donut": build_pie,
    "histogram": build_histogram,
    "scatter": build_scatter,
    "bubble": build_bubble,
    "area": build_area,
    "stacked_area": build_area,
    "box": build_box,
    "violin": build_violin,
    "heatmap": build_heatmap,
    "correlation_matrix": build_heatmap,
    "treemap": build_treemap,
    "sunburst": build_sunburst,
    "radar": build_radar,
    "scatter_3d": build_scatter_3d,
    "parallel_coordinates": build_parallel_coordinates,
    "waterfall": build_waterfall,
    "funnel": build_funnel,
    "gauge": build_gauge,
}

def build_chart(chart_type: str, df: pd.DataFrame, **kwargs) -> Optional[go.Figure]:
    """Factory function to build any chart type by name."""
    builder = CHART_BUILDERS.get(chart_type)
    if builder is None:
        return None

    try:
        # Map chart subtypes
        if chart_type == "grouped_bar":
            return builder(df, barmode="group", **kwargs)
        elif chart_type == "stacked_bar":
            return builder(df, barmode="stack", **kwargs)
        elif chart_type == "horizontal_bar":
            return builder(df, orientation="h", **kwargs)
        elif chart_type == "donut":
            return builder(df, style="donut", **kwargs)
        elif chart_type == "stacked_area":
            return builder(df, groupnorm="percent", **kwargs)
        elif chart_type == "correlation_matrix":
            return builder(df, colorscale="RdBu_r", **kwargs)
        else:
            return builder(df, **kwargs)
    except Exception as e:
        import streamlit as st
        st.warning(f"Chart build error ({chart_type}}): {str(e)}}")
        return None


