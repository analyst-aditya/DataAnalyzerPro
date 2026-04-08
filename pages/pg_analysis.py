"""
pg_analysis.py - Dashboard Analysis Page
FINAL FIX: Explicitly separated Bar and Line chart logic to prevent 'markers' TypeError.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from modules.chart_utils import CHART_THEMES


def get_sample_df(df, max_rows=50000):
    """Return a sample of the DataFrame if it's too large for efficient analysis."""
    if len(df) <= max_rows:
        return df
    st.info(f"📊 Dataset is large ({len(df):,} rows). Using a sample of {max_rows:,} rows for faster visualization and analysis.")
    return df.sample(n=max_rows, random_state=42)


def page_analysis(user: dict):
    st.title("📈 Dashboard Analysis")

    # Get data
    df = st.session_state.get("active_df")
    if df is None:
        dfs = st.session_state.get("uploaded_dfs", {})
        if dfs:
            df = list(dfs.values())[0]
    
    if df is None:
        st.warning("⚠️ Please upload data from the Home page first.")
        return

    name     = st.session_state.get("active_df_name", "Dataset")
    num_cols = list(df.select_dtypes(include=[np.number]).columns)
    cat_cols = list(df.select_dtypes(include="object").columns)
    st.caption(f"Active dataset: **{name}** — {len(df):,} rows × {len(df.columns)} columns")

    # Use sampled data for visualizations if dataset is large
    sample_df = get_sample_df(df)

    theme_name = st.selectbox("Chart Theme:", list(CHART_THEMES.keys()), key="analysis_theme")
    colors     = CHART_THEMES[theme_name]["colors"]

    tabs = st.tabs(["📊 Overview", "📉 Distribution", "🔗 Correlation", "📋 Statistics", "🔄 Cross Analysis"])

    # ── Overview Tab ──────────────────────────────────────────────────────────
    with tabs[0]:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Rows",     f"{len(df):,}")
        k2.metric("Total Columns",  len(df.columns))
        k3.metric("Numeric Columns",len(num_cols))
        k4.metric("Missing %",      f"{df.isna().mean().mean() * 100:.1f}%")

        if num_cols:
            st.markdown("#### Bar Charts — Numeric Columns")
            viz_cols = num_cols[:4]
            grid     = st.columns(min(2, len(viz_cols)))
            for i, col in enumerate(viz_cols):
                with grid[i % 2]:
                    if cat_cols:
                        cat     = cat_cols[0]
                        grouped = sample_df.groupby(cat)[col].mean().sort_values(ascending=False).head(15).reset_index()
                        fig     = px.bar(grouped, x=cat, y=col, title=f"{col} by {cat}",
                                         color_discrete_sequence=colors)
                    else:
                        fig = px.histogram(sample_df, x=col, title=f"{col} Distribution",
                                           color_discrete_sequence=colors)
                    fig.update_layout(showlegend=False, height=300, margin=dict(l=20,r=10,t=40,b=20))
                    st.plotly_chart(fig, use_container_width=True)

    # ── Distribution Tab ──────────────────────────────────────────────────────
    with tabs[1]:
        if not num_cols:
            st.info("No numeric columns available.")
        else:
            sel_col  = st.selectbox("Select column:", num_cols, key="dist_col")
            c1, c2   = st.columns([2, 1])
            nbins    = c1.slider("Number of bins:", 10, 100, 30, key="dist_bins")
            show_box = c2.checkbox("Show box plot", value=True)

            col1, col2 = st.columns(2)
            with col1:
                fig_hist = px.histogram(sample_df, x=sel_col, nbins=nbins,
                                        title=f"{sel_col} — Histogram",
                                        color_discrete_sequence=colors,
                                        marginal="violin" if show_box else None)
                fig_hist.update_layout(height=350)
                st.plotly_chart(fig_hist, use_container_width=True)
            with col2:
                fig_box = px.box(sample_df, y=sel_col, title=f"{sel_col} — Box Plot",
                                  color_discrete_sequence=colors)
                fig_box.update_layout(height=350)
                st.plotly_chart(fig_box, use_container_width=True)

    # ── Correlation Tab ───────────────────────────────────────────────────────
    with tabs[2]:
        if len(num_cols) < 2:
            st.info("At least 2 numeric columns are required for correlation analysis.")
        else:
            corr     = df[num_cols].corr()
            fig_heat = px.imshow(corr, title="Correlation Heatmap",
                                  color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                                  aspect="auto", text_auto=".2f")
            fig_heat.update_layout(height=500)
            st.plotly_chart(fig_heat, use_container_width=True)

    # ── Statistics Tab ────────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("#### Descriptive Statistics")
        st.dataframe(df.describe(include="all").round(3), use_container_width=True)

    # ── Cross Analysis Tab (WHERE THE ERROR WAS) ──────────────────────────────
    with tabs[4]:
        st.markdown("#### Cross Analysis — Two Variables")
        if not num_cols or not cat_cols:
            st.info("Both numeric and categorical columns are required for cross analysis.")
        else:
            cc1, cc2, cc3 = st.columns(3)
            x_col   = cc1.selectbox("X-Axis:",    cat_cols + num_cols, key="cross_x")
            y_col   = cc2.selectbox("Y-Axis:",    num_cols,            key="cross_y")
            chart_t = cc3.selectbox("Chart Type:",["bar","line","box","violin","scatter"], key="cross_type")
            
            color_c = st.selectbox("Color by:", ["None"] + cat_cols, key="cross_color")
            agg_f   = st.selectbox("Aggregation:", ["mean","sum","count","max","min"], key="cross_agg")

            if x_col in df.columns and y_col in df.columns:
                fig = None
                
                # 1. Bar Chart Logic (No markers allowed)
                if chart_t == "bar":
                    grouped = sample_df.groupby(x_col)[y_col].agg(agg_f).reset_index()
                    fig = px.bar(
                        grouped, x=x_col, y=y_col,
                        title=f"{agg_f.title()} of {y_col} by {x_col}",
                        color_discrete_sequence=colors
                    )
                
                # 2. Line Chart Logic (Markers allowed)
                elif chart_t == "line":
                    grouped = sample_df.groupby(x_col)[y_col].agg(agg_f).reset_index()
                    fig = px.line(
                        grouped, x=x_col, y=y_col,
                        title=f"{agg_f.title()} of {y_col} by {x_col}",
                        color_discrete_sequence=colors,
                        markers=True
                    )
                
                # 3. Box Plot Logic
                elif chart_t == "box":
                    fig = px.box(sample_df, x=x_col if x_col in cat_cols else None, y=y_col,
                                  color=color_c if color_c != "None" else None,
                                  title=f"{y_col} by {x_col}",
                                  color_discrete_sequence=colors)
                
                # 4. Violin Plot Logic
                elif chart_t == "violin":
                    fig = px.violin(sample_df, x=x_col if x_col in cat_cols else None, y=y_col,
                                     color=color_c if color_c != "None" else None,
                                     box=True, title=f"{y_col} by {x_col}",
                                     color_discrete_sequence=colors)
                
                # 5. Scatter Plot Logic
                elif chart_t == "scatter":
                    fig = px.scatter(sample_df, x=x_col, y=y_col,
                                      color=color_c if color_c != "None" else None,
                                      title=f"{x_col} vs {y_col}",
                                      color_discrete_sequence=colors)

                # Render the chart if created
                if fig:
                    fig.update_layout(height=450)
                    st.plotly_chart(fig, use_container_width=True)