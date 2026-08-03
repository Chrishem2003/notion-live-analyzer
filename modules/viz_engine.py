import security_guard

"""
Visualization Engine  intelligent auto-chart recommendation and selection.
Analyzes data types and suggests the best visualization automatically.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from modules.data_processor import infer_column_types, infer_column_type

# â”€â”€â”€ Chart Category Definitions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
CHART_CATEGORIES = {
    "Distribution": ["histogram", "box", "violin", "density"],
    "Comparison": ["bar", "grouped_bar", "stacked_bar", "horizontal_bar"],
    "Trend": ["line", "area", "stacked_area"],
    "Correlation": ["scatter", "bubble", "heatmap", "correlation_matrix"],
    "Part-to-Whole": ["pie", "donut", "treemap", "sunburst", "funnel"],
    "Multi-Dimensional": ["scatter_3d", "parallel_coordinates", "radar"],
    "Hierarchical": ["treemap", "sunburst", "icicle"],
    "Specialized": ["waterfall", "gauge", "candlestick"],
}

CHART_DESCRIPTIONS = {
    "histogram": "Histogram with optional KDE  shows distribution of a numeric variable",
    "box": "Box plot  shows median, quartiles, and outliers",
    "violin": "Violin plot  combines box plot with density distribution",
    "density": "Density plot  smooth distribution estimate",
    "bar": "Bar chart  compare values across categories",
    "grouped_bar": "Grouped bar chart  compare multiple series across categories",
    "stacked_bar": "Stacked bar chart  show composition across categories",
    "horizontal_bar": "Horizontal bar chart  good for many categories",
    "line": "Line chart  show trends over time or ordered categories",
    "area": "Area chart  emphasize magnitude of change",
    "stacked_area": "Stacked area chart  show composition over time",
    "scatter": "Scatter plot  relationship between two numeric variables",
    "bubble": "Bubble chart  scatter with 3rd dimension as bubble size",
    "heatmap": "Heatmap  color-coded matrix of values",
    "correlation_matrix": "Correlation matrix  strength of relationships",
    "pie": "Pie chart  proportions of a whole (limited categories recommended)",
    "donut": "Donut chart  pie chart with center hole",
    "treemap": "Treemap  hierarchical data as nested rectangles",
    "sunburst": "Sunburst  hierarchical data as concentric rings",
    "funnel": "Funnel chart  progressive reduction through stages",
    "scatter_3d": "3D Scatter plot  three numeric dimensions",
    "parallel_coordinates": "Parallel coordinates  multi-dimensional comparison",
    "radar": "Radar / Spider chart  multi-dimensional profiles",
    "waterfall": "Waterfall chart  sequential contribution to total",
    "gauge": "Gauge chart  single value against a target range",
    "icicle": "Icicle chart  hierarchical data as cascading rectangles",
}

ALL_CHART_TYPES = list(CHART_DESCRIPTIONS.keys())


def auto_recommend_chart(
    df: pd.DataFrame,
    columns: List[str] = None,
) -> List[Dict[str, Any]]:
    """
    Intelligently recommend charts based on column types.
    Returns ranked list of chart recommendations with confidence scores.
    """
    if df is None or df.empty:
        return []

    if columns is None:
        columns = df.columns.tolist()

    col_types = infer_column_types(df[columns])
    recommendations = []

    # Count types
    numeric_cols = [c for c, t in col_types.items() if t in ("numeric", "integer")]
    cat_cols = [c for c, t in col_types.items() if t in ("categorical", "string")]
    temporal_cols = [c for c, t in col_types.items() if t == "temporal"]
    bool_cols = [c for c, t in col_types.items() if t == "boolean"]

    # --- Recommendations based on available columns ---
    all_cols = columns

    # 1. Single numeric column â†’ Distribution plots
    if len(numeric_cols) >= 1:
        recommendations.extend([
            {"chart": "histogram", "x": numeric_cols[0], "y": None,
             "reason": f"Distribution of {numeric_cols[0]}", "score": 95},
            {"chart": "box", "x": None, "y": numeric_cols[0],
             "reason": f"Box plot of {numeric_cols[0]}", "score": 85},
            {"chart": "violin", "x": None, "y": numeric_cols[0],
             "reason": f"Distribution density of {numeric_cols[0]}", "score": 80},
        ])

    # 2. Categorical  Numeric â†’ Bar/comparison charts
    if cat_cols and numeric_cols:
        for cat in cat_cols[:2]:
            for num in numeric_cols[:2]:
                recommendations.extend([
                    {"chart": "bar", "x": cat, "y": num,
                     "reason": f"Compare {num} across {cat}", "score": 95},
                    {"chart": "box", "x": cat, "y": num,
                     "reason": f"Distribution of {num} by {cat}", "score": 88},
                    {"chart": "violin", "x": cat, "y": num,
                     "reason": f"Density of {num} by {cat}", "score": 82},
                ])
                if len(cat_cols) >= 2:
                    recommendations.append(
                        {"chart": "grouped_bar", "x": cat_cols[0], "y": num, "color": cat_cols[1],
                         "reason": f"Compare {num} by {cat_cols[0]} and {cat_cols[1]}", "score": 90}
                    )

    # 3. Categorical only â†’ Frequency charts
    if cat_cols and not numeric_cols:
        for cat in cat_cols[:2]:
            recommendations.extend([
                {"chart": "bar", "x": cat, "y": None,
                 "reason": f"Frequency of {cat}", "score": 90},
                {"chart": "pie", "x": cat, "y": None,
                 "reason": f"Proportion of {cat}", "score": 80},
                {"chart": "treemap", "x": cat, "y": None,
                 "reason": f"Hierarchy of {cat}", "score": 75},
            ])

    # 4. Temporal  Numeric â†’ Trend charts
    if temporal_cols and numeric_cols:
        for temp in temporal_cols[:1]:
            for num in numeric_cols[:2]:
                recommendations.extend([
                    {"chart": "line", "x": temp, "y": num,
                     "reason": f"Trend of {num} over time", "score": 98},
                    {"chart": "area", "x": temp, "y": num,
                     "reason": f"Area trend of {num}", "score": 85},
                ])

    # 5. Two numeric columns â†’ Correlation charts
    if len(numeric_cols) >= 2:
        recommendations.extend([
            {"chart": "scatter", "x": numeric_cols[0], "y": numeric_cols[1],
             "reason": f"Relationship: {numeric_cols[0]} vs {numeric_cols[1]}", "score": 95},
            {"chart": "bubble", "x": numeric_cols[0], "y": numeric_cols[1],
             "reason": f"Bubble: {numeric_cols[0]} vs {numeric_cols[1]}",
             "size": numeric_cols[2] if len(numeric_cols) >= 3 else None, "score": 85},
            {"chart": "heatmap", "x": None, "y": None,
             "reason": "Correlation heatmap of numeric variables", "score": 80},
        ])

    # 6. Three numeric columns â†’ Multi-dimensional
    if len(numeric_cols) >= 3:
        recommendations.append(
            {"chart": "scatter_3d", "x": numeric_cols[0], "y": numeric_cols[1], "z": numeric_cols[2],
             "reason": f"3D: {numeric_cols[0]}, {numeric_cols[1]}, {numeric_cols[2]}", "score": 85}
        )
    if len(numeric_cols) >= 4:
        recommendations.append(
            {"chart": "parallel_coordinates", "dimensions": numeric_cols,
             "reason": "Multi-dimensional parallel coordinates", "score": 78}
        )

    # 7. Categorical  Temporal â†’ Stacked area
    if cat_cols and temporal_cols and numeric_cols:
        recommendations.append(
            {"chart": "stacked_area", "x": temporal_cols[0], "y": numeric_cols[0], "color": cat_cols[0],
             "reason": f"Composition of {numeric_cols[0]} over time by {cat_cols[0]}", "score": 85}
        )

    # 8. Hierarchical (two categoricals) â†’ Treemap, Sunburst
    if len(cat_cols) >= 2:
        recommendations.extend([
            {"chart": "treemap", "path": cat_cols[:3], "values": numeric_cols[0] if numeric_cols else None,
             "reason": "Hierarchical treemap", "score": 82},
            {"chart": "sunburst", "path": cat_cols[:3], "values": numeric_cols[0] if numeric_cols else None,
             "reason": "Hierarchical sunburst", "score": 78},
        ])

    # 9. Radar for multi-dimensional profiles
    if len(numeric_cols) >= 3 and cat_cols:
        recommendations.append(
            {"chart": "radar", "categories": numeric_cols, "color": cat_cols[0],
             "reason": f"Multi-dimensional profiles by {cat_cols[0]}", "score": 75}
        )

    # Sort by score descending and remove duplicates
    seen = set()
    unique_recs = []
    for rec in sorted(recommendations, key=lambda x: x["score"], reverse=True):
        key = (rec["chart"], str(rec.get("x")), str(rec.get("y")))
        if key not in seen:
            seen.add(key)
            unique_recs.append(rec)

    return unique_recs[:15]  # Top 15 recommendations


def explain_chart_recommendation(rec: Dict[str, Any]) -> str:
    """Generate a human-readable explanation of why a chart was recommended."""
    chart_name = rec.get("chart", "").replace("_", " ").title()
    reason = rec.get("reason", "")
    score = rec.get("score", 0)

    confidence = "ðŸ”µ Highly Recommended" if score >= 90 else "ðŸŸ¢ Recommended" if score >= 80 else "ðŸŸ¡ Suggested"
    return f"{confidence}  **{chart_name}**: {reason}"


def get_chart_search_results(query: str) -> List[Tuple[str, str]]:
    """Search chart types by keyword."""
    query = query.lower()
    results = []
    for chart_type, desc in CHART_DESCRIPTIONS.items():
        if query in chart_type.lower() or query in desc.lower():
            results.append((chart_type, desc))
    return results

