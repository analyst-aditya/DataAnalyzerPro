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
    {"id": "card",      "label": "Metric Card",    "icon": "🃏"},
]

# Fields required by chart type
CHART_FIELD_REQUIREMENTS = {
    "bar":       {"required": ["xcol", "ycol"], "optional": ["color_col"], "labels": ["X-Axis / Category", "Y-Axis / Value"]},
    "line":      {"required": ["xcol", "ycol"], "optional": ["color_col"], "labels": ["X-Axis", "Y-Axis / Value"]},
    "area":      {"required": ["xcol", "ycol"], "optional": ["color_col"], "labels": ["X-Axis", "Y-Axis / Value"]},
    "scatter":   {"required": ["xcol", "ycol"], "optional": ["color_col", "size_col"], "labels": ["X-Axis", "Y-Axis"]},
    "bubble":    {"required": ["xcol", "ycol"], "optional": ["color_col", "size_col"], "labels": ["X-Axis", "Y-Axis"]},
    "pie":       {"required": ["xcol", "ycol"], "optional": [], "labels": ["Legend / Category", "Values"]},
    "donut":     {"required": ["xcol", "ycol"], "optional": [], "labels": ["Legend / Category", "Values"]},
    "histogram": {"required": ["xcol"],         "optional": [], "labels": ["Column"]},
    "box":       {"required": ["ycol"],         "optional": ["xcol", "color_col"], "labels": ["Y-Axis / Value", "X-Axis (group by)"]},
    "violin":    {"required": ["ycol"],         "optional": ["xcol", "color_col"], "labels": ["Y-Axis / Value", "X-Axis (group by)"]},
    "heatmap":   {"required": [],               "optional": [], "labels": []},
    "funnel":    {"required": ["xcol", "ycol"], "optional": [], "labels": ["Stage / Category", "Values"]},
    "table":     {"required": [],               "optional": [], "labels": []},
    "kpi":       {"required": ["ycol"],         "optional": ["xcol"], "labels": ["Value Column", "Trend Column (optional)"]},
    "card":      {"required": ["ycol"],         "optional": ["xcol"], "labels": ["Primary Metric", "Secondary Metric (optional)"]},
}


def _apply_theme(fig: go.Figure, theme_name: str, title: str = "", dark_mode: bool = False,
                 hide_axes: bool = False) -> go.Figure:
    """Apply a named theme to a Plotly figure."""
    t = CHART_THEMES.get(theme_name, CHART_THEMES["Default"]).copy()
    if dark_mode:
        t["text"] = "#EAEAEA"
        t["grid"] = t.get("grid", "#333355")
        if t["bg"] == "rgba(0,0,0,0)":
            t["bg"] = "#0f172a"
        if t["paper_bg"] == "rgba(0,0,0,0)":
            t["paper_bg"] = "#0f172a"

    if hide_axes:
        axis_update = {
            "xaxis": dict(visible=False, showgrid=False, zeroline=False),
            "yaxis": dict(visible=False, showgrid=False, zeroline=False),
        }
    else:
        axis_update = {
            "xaxis": {"gridcolor": t["grid"], "gridwidth": t["grid_width"],
                      "zeroline": False, "showgrid": True, "color": t["text"]},
            "yaxis": {"gridcolor": t["grid"], "gridwidth": t["grid_width"],
                      "zeroline": False, "showgrid": True, "color": t["text"]},
        }

    fig.update_layout(
        title={"text": title, "font": {"size": 14, "color": t["text"]}, "x": 0.5, "xanchor": "center"},
        plot_bgcolor=t["bg"],
        paper_bgcolor=t["paper_bg"],
        font={"color": t["text"], "size": 11},
        colorway=t["colors"],
        legend={"font": {"color": t["text"]}, "bgcolor": "rgba(0,0,0,0)"},
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        hoverlabel={"bgcolor": "#111827" if dark_mode else "#1a1a2e", "font_color": "white"},
        **axis_update,
    )
    return fig


def make_chart(df: pd.DataFrame, config: Dict[str, Any]) -> Optional[go.Figure]:
    """
    Create a Plotly figure from a chart config dict.
    config keys: type, xcol, ycol, color_col, size_col, title, theme, agg_func, orientation,
                 show_labels (bool), label_position
    """
    ctype       = config.get("type", "bar")
    xcol        = config.get("xcol", "")
    ycol        = config.get("ycol", "")
    color_col   = config.get("color_col", None)
    size_col    = config.get("size_col", None)
    title       = config.get("title", "")
    theme       = config.get("theme", "Default")
    agg_func    = config.get("agg_func", "sum")
    orient      = config.get("orientation", "v")
    nbins       = config.get("nbins", 30)
    top_n       = config.get("top_n", 0)
    show_labels = config.get("show_labels", False)
    colors      = CHART_THEMES.get(theme, CHART_THEMES["Default"])["colors"]

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
                         orientation=orient, color_discrete_sequence=colors,
                         text=ycol if show_labels else None)
            if show_labels:
                fig.update_traces(texttemplate="%{text:,.1f}", textposition="outside")

        elif ctype == "line":
            plot_df = agg_df(xcol, ycol) if xcol and ycol and xcol in df.columns and ycol in df.columns else df
            fig = px.line(plot_df, x=xcol, y=ycol, color=color_col if color_col and color_col in df.columns else None,
                          markers=True, color_discrete_sequence=colors,
                          text=ycol if show_labels else None)
            if show_labels:
                fig.update_traces(texttemplate="%{text:,.1f}", textposition="top center")

        elif ctype == "area":
            plot_df = agg_df(xcol, ycol) if xcol and ycol and xcol in df.columns and ycol in df.columns else df
            fig = px.area(plot_df, x=xcol, y=ycol, color=color_col if color_col and color_col in df.columns else None,
                          color_discrete_sequence=colors)
            if show_labels:
                fig.update_traces(text=plot_df[ycol] if ycol in plot_df.columns else None,
                                  texttemplate="%{text:,.1f}", textposition="top center", mode="lines+markers+text")

        elif ctype == "scatter":
            fig = px.scatter(df, x=xcol if xcol in df.columns else None,
                             y=ycol if ycol in df.columns else None,
                             color=color_col if color_col and color_col in df.columns else None,
                             size=size_col if size_col and size_col in df.columns else None,
                             color_discrete_sequence=colors,
                             text=xcol if show_labels and xcol in df.columns else None)
            if show_labels:
                fig.update_traces(textposition="top center")

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
                text_info = "label+percent+value" if show_labels else "label+percent"
                fig = go.Figure(go.Pie(labels=grouped[xcol], values=grouped[ycol],
                                       hole=hole, marker_colors=colors,
                                       textinfo=text_info))
            else:
                return None

        elif ctype == "histogram":
            col = xcol if xcol and xcol in df.columns else ycol
            if col not in df.columns:
                return None
            fig = px.histogram(df, x=col, nbins=nbins, color_discrete_sequence=colors,
                               text_auto=show_labels)

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
                            zmin=-1, zmax=1, text_auto=".2f" if show_labels else False)

        elif ctype == "funnel":
            if xcol in df.columns and ycol in df.columns:
                grouped = df.groupby(xcol)[ycol].sum().reset_index().sort_values(ycol, ascending=False)
                fig = go.Figure(go.Funnel(y=grouped[xcol].astype(str), x=grouped[ycol],
                                           marker_color=colors[:len(grouped)],
                                           textinfo="value+percent total" if show_labels else "value"))
            else:
                return None

        elif ctype == "table":
            display_df = df.head(100)
            is_dark_theme = theme in ("Dark",)
            cell_even = "#1e293b" if is_dark_theme else "#f8f9fa"
            cell_odd  = "#0f172a" if is_dark_theme else "#ffffff"
            cell_font = "#e2e8f0" if is_dark_theme else "#1e293b"
            fig = go.Figure(go.Table(
                header=dict(values=list(display_df.columns),
                            fill_color=colors[0], font=dict(color="white", size=11),
                            align="left"),
                cells=dict(values=[display_df[c] for c in display_df.columns],
                           fill_color=[[cell_even if i % 2 == 0 else cell_odd for i in range(len(display_df))]
                                       for _ in display_df.columns],
                           font=dict(color=cell_font, size=11),
                           align="left")
            ))

        elif ctype == "kpi":
            if ycol and ycol in df.columns and pd.api.types.is_numeric_dtype(df[ycol]):
                val      = df[ycol].sum()
                mean_val = df[ycol].mean()
                max_val  = df[ycol].max()
                trend_col = xcol if xcol and xcol in df.columns and pd.api.types.is_numeric_dtype(df[xcol]) else None

                if trend_col:
                    # Two-row subplot: annotation on top, sparkline on bottom
                    from plotly.subplots import make_subplots
                    fig = make_subplots(
                        rows=2, cols=1,
                        row_heights=[0.65, 0.35],
                        vertical_spacing=0.05,
                    )
                    # Invisible dummy trace in row 1 to hold layout
                    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers",
                                             marker=dict(opacity=0), showlegend=False,
                                             hoverinfo="skip"), row=1, col=1)
                    # Sparkline in row 2
                    trend_vals = df[trend_col].dropna().tail(20).tolist()
                    fig.add_trace(go.Scatter(
                        x=list(range(len(trend_vals))), y=trend_vals,
                        mode="lines", line=dict(color=colors[0], width=2),
                        fill="tozeroy", fillcolor=f"rgba({int(colors[0][1:3],16)},{int(colors[0][3:5],16)},{int(colors[0][5:7],16)},0.15)",
                        showlegend=False, hovertemplate=f"{trend_col}: %{{y:,.2f}}<extra></extra>"
                    ), row=2, col=1)
                    fig.update_xaxes(visible=False)
                    fig.update_yaxes(visible=False, showgrid=False, zeroline=False)
                    # Main value annotation
                    fig.add_annotation(x=0.5, y=0.90, xref="paper", yref="paper",
                                       text=f"<b>{val:,.0f}</b>",
                                       font=dict(size=34, color=colors[0]), showarrow=False)
                    fig.add_annotation(x=0.5, y=0.70, xref="paper", yref="paper",
                                       text=f"Avg: {mean_val:,.2f}  |  Max: {max_val:,.0f}",
                                       font=dict(size=12), showarrow=False)
                    fig.add_annotation(x=0.02, y=0.28, xref="paper", yref="paper",
                                       text=f"<i>Trend: {trend_col}</i>",
                                       font=dict(size=10, color="#94a3b8"),
                                       showarrow=False, xanchor="left")
                    fig.update_layout(height=240)
                else:
                    fig = go.Figure()
                    fig.add_annotation(x=0.5, y=0.62, xref="paper", yref="paper",
                                       text=f"<b>{val:,.0f}</b>",
                                       font=dict(size=40, color=colors[0]), showarrow=False)
                    fig.add_annotation(x=0.5, y=0.38, xref="paper", yref="paper",
                                       text=f"Avg: {mean_val:,.2f}  |  Max: {max_val:,.0f}",
                                       font=dict(size=13), showarrow=False)
                    fig.update_layout(height=180)

                fig = _apply_theme(fig, theme, title, hide_axes=(not trend_col))
                if trend_col:
                    # After theme: force-hide both axis layers
                    fig.update_xaxes(visible=False, showgrid=False, zeroline=False)
                    fig.update_yaxes(visible=False, showgrid=False, zeroline=False)
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                )
            else:
                return None

        elif ctype == "card":
            if ycol and ycol in df.columns and pd.api.types.is_numeric_dtype(df[ycol]):
                primary_val   = df[ycol].sum()
                primary_avg   = df[ycol].mean()
                primary_label = ycol
                secondary_col = xcol if xcol and xcol in df.columns and pd.api.types.is_numeric_dtype(df[xcol]) else None
                fig = go.Figure()
                y_main = 0.65 if secondary_col else 0.60
                fig.add_annotation(x=0.5, y=y_main, xref="paper", yref="paper",
                                   text=f"<b>{primary_val:,.0f}</b>",
                                   font=dict(size=42, color=colors[0]), showarrow=False)
                fig.add_annotation(x=0.5, y=y_main - 0.22, xref="paper", yref="paper",
                                   text=primary_label,
                                   font=dict(size=13, color="#94a3b8"), showarrow=False)
                fig.add_annotation(x=0.5, y=y_main - 0.40, xref="paper", yref="paper",
                                   text=f"avg {primary_avg:,.2f}",
                                   font=dict(size=11, color="#64748b"), showarrow=False)
                if secondary_col:
                    sec_val = df[secondary_col].sum()
                    fig.add_annotation(x=0.5, y=0.08, xref="paper", yref="paper",
                                       text=f"◆ {secondary_col}: {sec_val:,.0f}",
                                       font=dict(size=12, color=colors[1] if len(colors) > 1 else colors[0]),
                                       showarrow=False)
                fig.update_layout(height=180, margin=dict(l=16, r=16, t=40, b=16))
                fig = _apply_theme(fig, theme, title, hide_axes=True)
                fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            else:
                return None

        else:
            return None

        # KPI and Card already called _apply_theme internally
        if ctype not in ("kpi", "card"):
            fig = _apply_theme(fig, theme, title)
        return fig

    except Exception as e:
        # Return error figure
        fig = go.Figure()
        fig.add_annotation(text=f"Chart error: {e}", x=0.5, y=0.5,
                           xref="paper", yref="paper", showarrow=False,
                           font=dict(size=12, color="red"))
        return fig
