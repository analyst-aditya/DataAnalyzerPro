"""
chart_utils.py - Chart generation with Power BI-style themes
"""
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, Optional

# ─── Power BI-style chart themes ─────────────────────────────────────────────

CHART_THEMES = {
    "Default": {
        "colors": ["#118DFF","#12239E","#E66C37","#6B007B","#E044A7","#744EC2","#D9B300","#D64550"],
        "bg": "rgba(0,0,0,0)", "paper_bg": "rgba(0,0,0,0)",
        "text": "#262730", "grid": "#EEEEEE", "grid_width": 0.5,
    },
    "Dark": {
        "colors": ["#4FC3F7","#81C784","#FFB74D","#F06292","#CE93D8","#80DEEA","#FFCC02","#FF8A65"],
        "bg": "#1a1a2e", "paper_bg": "#1a1a2e",
        "text": "#EAEAEA", "grid": "#333355", "grid_width": 0.5,
    },
    "Ocean": {
        "colors": ["#1A73E8","#00BCD4","#26A69A","#5C6BC0","#29B6F6","#4DD0E1","#80CBC4","#9FA8DA"],
        "bg": "rgba(0,0,0,0)", "paper_bg": "rgba(0,0,0,0)",
        "text": "#1A1A2E", "grid": "#D0E8FF", "grid_width": 0.5,
    },
    "Sunset": {
        "colors": ["#FF6B6B","#FFA500","#FFD93D","#6BCB77","#4D96FF","#C77DFF","#FF6B6B","#FF8E53"],
        "bg": "rgba(0,0,0,0)", "paper_bg": "rgba(0,0,0,0)",
        "text": "#2D1B00", "grid": "#FFE0C0", "grid_width": 0.5,
    },
    "Corporate": {
        "colors": ["#003366","#004D99","#0066CC","#0080FF","#3399FF","#66B2FF","#99CCFF","#B8D4F0"],
        "bg": "rgba(0,0,0,0)", "paper_bg": "rgba(0,0,0,0)",
        "text": "#1A1A1A", "grid": "#E0E0E0", "grid_width": 0.5,
    },
    "Forest": {
        "colors": ["#2D6A4F","#40916C","#52B788","#74C69D","#95D5B2","#B7E4C7","#D8F3DC","#1B4332"],
        "bg": "rgba(0,0,0,0)", "paper_bg": "rgba(0,0,0,0)",
        "text": "#1B4332", "grid": "#D8F3DC", "grid_width": 0.5,
    },
}

CHART_TYPES = [
    {"id": "bar",       "label": "Bar Chart",      "icon": "📊"},
    {"id": "line",      "label": "Line Chart",     "icon": "📈"},
    {"id": "area",      "label": "Area Chart",     "icon": "🏔️"},
    {"id": "scatter",   "label": "Scatter Plot",   "icon": "🔵"},
    {"id": "pie",       "label": "Pie Chart",      "icon": "🥧"},
    {"id": "donut",     "label": "Donut Chart",    "icon": "🍩"},
    {"id": "histogram", "label": "Histogram",      "icon": "📉"},
    {"id": "box",       "label": "Box Plot",       "icon": "📦"},
    {"id": "heatmap",   "label": "Heatmap",        "icon": "🗺️"},
    {"id": "funnel",    "label": "Funnel Chart",   "icon": "🔽"},
    {"id": "violin",    "label": "Violin Plot",    "icon": "🎻"},
    {"id": "bubble",    "label": "Bubble Chart",   "icon": "🫧"},
    {"id": "table",     "label": "Data Table",     "icon": "📋"},
    {"id": "kpi",       "label": "KPI Card",       "icon": "🎯"},
]


def _apply_theme(fig: go.Figure, theme_name: str, title: str = "") -> go.Figure:
    """Apply a named theme to a Plotly figure."""
    t = CHART_THEMES.get(theme_name, CHART_THEMES["Default"])
    fig.update_layout(
        title={"text": title, "font": {"size": 14, "color": t["text"]}, "x": 0.5, "xanchor": "center"},
        plot_bgcolor=t["bg"],
        paper_bgcolor=t["paper_bg"],
        font={"color": t["text"], "size": 11},
        colorway=t["colors"],
        xaxis={"gridcolor": t["grid"], "gridwidth": t["grid_width"],
                "zeroline": False, "showgrid": True, "color": t["text"]},
        yaxis={"gridcolor": t["grid"], "gridwidth": t["grid_width"],
                "zeroline": False, "showgrid": True, "color": t["text"]},
        legend={"font": {"color": t["text"]}, "bgcolor": "rgba(0,0,0,0)"},
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        hoverlabel={"bgcolor": "#1a1a2e", "font_color": "white"},
    )
    return fig


def make_chart(df: pd.DataFrame, config: Dict[str, Any]) -> Optional[go.Figure]:
    """
    Create a Plotly figure from a chart config dict.
    config keys: type, xcol, ycol, color_col, size_col, title, theme, agg_func, orientation
    """
    ctype     = config.get("type", "bar")
    xcol      = config.get("xcol", "")
    ycol      = config.get("ycol", "")
    color_col = config.get("color_col", None)
    size_col  = config.get("size_col", None)
    title     = config.get("title", "")
    theme     = config.get("theme", "Default")
    agg_func  = config.get("agg_func", "sum")
    orient    = config.get("orientation", "v")
    nbins     = config.get("nbins", 30)
    top_n     = config.get("top_n", 0)
    colors    = CHART_THEMES.get(theme, CHART_THEMES["Default"])["colors"]

    if df is None or len(df) == 0:
        return None

    # Optional top-N filter
    if top_n and xcol in df.columns and ycol in df.columns:
        agg = df.groupby(xcol)[ycol].sum().nlargest(top_n).reset_index()
        df = agg

    try:
        # ── Aggregation helper ────────────────────────────────────────────────
        def agg_df(x, y):
            if pd.api.types.is_numeric_dtype(df[y]):
                funcs = {"sum": "sum", "mean": "mean", "count": "count",
                         "min": "min", "max": "max", "median": "median"}
                return df.groupby(x)[y].agg(funcs.get(agg_func, "sum")).reset_index()
            return df

        if ctype == "bar":
            plot_df = agg_df(xcol, ycol) if xcol and ycol and xcol in df.columns and ycol in df.columns else df
            fig = px.bar(plot_df, x=xcol, y=ycol, color=color_col if color_col and color_col in df.columns else None,
                         orientation=orient, color_discrete_sequence=colors)

        elif ctype == "line":
            plot_df = agg_df(xcol, ycol) if xcol and ycol and xcol in df.columns and ycol in df.columns else df
            fig = px.line(plot_df, x=xcol, y=ycol, color=color_col if color_col and color_col in df.columns else None,
                          markers=True, color_discrete_sequence=colors)

        elif ctype == "area":
            plot_df = agg_df(xcol, ycol) if xcol and ycol and xcol in df.columns and ycol in df.columns else df
            fig = px.area(plot_df, x=xcol, y=ycol, color=color_col if color_col and color_col in df.columns else None,
                          color_discrete_sequence=colors)

        elif ctype == "scatter":
            fig = px.scatter(df, x=xcol if xcol in df.columns else None,
                             y=ycol if ycol in df.columns else None,
                             color=color_col if color_col and color_col in df.columns else None,
                             size=size_col if size_col and size_col in df.columns else None,
                             color_discrete_sequence=colors)

        elif ctype == "bubble":
            fig = px.scatter(df, x=xcol if xcol in df.columns else None,
                             y=ycol if ycol in df.columns else None,
                             size=size_col if size_col and size_col in df.columns else None,
                             color=color_col if color_col and color_col in df.columns else None,
                             color_discrete_sequence=colors)

        elif ctype in ("pie", "donut"):
            hole = 0.45 if ctype == "donut" else 0
            if xcol in df.columns and ycol in df.columns:
                grouped = df.groupby(xcol)[ycol].sum().reset_index()
                fig = go.Figure(go.Pie(labels=grouped[xcol], values=grouped[ycol],
                                       hole=hole, marker_colors=colors))
            else:
                return None

        elif ctype == "histogram":
            col = xcol if xcol and xcol in df.columns else ycol
            if col not in df.columns:
                return None
            fig = px.histogram(df, x=col, nbins=nbins, color_discrete_sequence=colors)

        elif ctype == "box":
            fig = px.box(df, x=xcol if xcol and xcol in df.columns else None,
                         y=ycol if ycol and ycol in df.columns else None,
                         color=color_col if color_col and color_col in df.columns else None,
                         color_discrete_sequence=colors)

        elif ctype == "violin":
            fig = px.violin(df, x=xcol if xcol and xcol in df.columns else None,
                            y=ycol if ycol and ycol in df.columns else None,
                            color=color_col if color_col and color_col in df.columns else None,
                            box=True, color_discrete_sequence=colors)

        elif ctype == "heatmap":
            numeric_df = df.select_dtypes(include=[np.number])
            if len(numeric_df.columns) < 2:
                return None
            corr = numeric_df.corr()
            fig = px.imshow(corr, color_continuous_scale="RdBu_r", aspect="auto",
                            zmin=-1, zmax=1)

        elif ctype == "funnel":
            if xcol in df.columns and ycol in df.columns:
                grouped = df.groupby(xcol)[ycol].sum().reset_index().sort_values(ycol, ascending=False)
                fig = go.Figure(go.Funnel(y=grouped[xcol].astype(str), x=grouped[ycol],
                                           marker_color=colors[:len(grouped)]))
            else:
                return None

        elif ctype == "table":
            display_df = df.head(100)
            fig = go.Figure(go.Table(
                header=dict(values=list(display_df.columns),
                            fill_color=colors[0], font=dict(color="white", size=11)),
                cells=dict(values=[display_df[c] for c in display_df.columns],
                           fill_color=[["#f8f9fa" if i % 2 == 0 else "white" for i in range(len(display_df))]
                                       for _ in display_df.columns])
            ))

        elif ctype == "kpi":
            if ycol and ycol in df.columns and pd.api.types.is_numeric_dtype(df[ycol]):
                val = df[ycol].sum()
                mean_val = df[ycol].mean()
                fig = go.Figure()
                fig.add_annotation(x=0.5, y=0.6, xref="paper", yref="paper",
                                   text=f"<b>{val:,.0f}</b>", font=dict(size=36, color=colors[0]),
                                   showarrow=False)
                fig.add_annotation(x=0.5, y=0.35, xref="paper", yref="paper",
                                   text=f"Avg: {mean_val:,.2f}", font=dict(size=14),
                                   showarrow=False)
                fig.update_layout(height=180)
            else:
                return None
        else:
            return None

        fig = _apply_theme(fig, theme, title)
        return fig

    except Exception as e:
        # Return error figure
        fig = go.Figure()
        fig.add_annotation(text=f"Chart error: {e}", x=0.5, y=0.5,
                           xref="paper", yref="paper", showarrow=False,
                           font=dict(size=12, color="red"))
        return fig
