"""
pg_analysis.py - Dashboard Analysis Page
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from modules.chart_utils import CHART_THEMES, _apply_theme


def page_analysis(user: dict):
    st.title("📈 Dashboard Analysis")

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

    theme_name = st.selectbox("Chart Theme:", list(CHART_THEMES.keys()), key="analysis_theme")
    colors     = CHART_THEMES[theme_name]["colors"]

    def style_fig(fig, title=""):
        if fig is None:
            return fig
        title_text = title
        if not title_text:
            if getattr(fig.layout, "title", None) is not None:
                title_text = fig.layout.title.text or ""
            else:
                title_text = ""
        dark_mode = st.session_state.get("app_theme") == "dark"
        return _apply_theme(fig, theme_name, title_text, dark_mode=dark_mode)

    tabs = st.tabs(["📊 Overview", "📉 Distribution", "🔗 Correlation", "📋 Statistics", "🔄 Cross Analysis"])

    # ── Overview ──────────────────────────────────────────────────────────────
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
                        grouped = df.groupby(cat)[col].mean().sort_values(ascending=False).head(15).reset_index()
                        fig     = px.bar(grouped, x=cat, y=col, title=f"{col} by {cat}",
                                         color_discrete_sequence=colors)
                    else:
                        fig = px.histogram(df, x=col, title=f"{col} Distribution",
                                           color_discrete_sequence=colors)
                    fig = style_fig(fig)
                    fig.update_layout(showlegend=False, height=300, margin=dict(l=20,r=10,t=40,b=20))
                    st.plotly_chart(fig, use_container_width=True)

    # ── Distribution ──────────────────────────────────────────────────────────
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
                fig_hist = px.histogram(df, x=sel_col, nbins=nbins,
                                        title=f"{sel_col} — Histogram",
                                        color_discrete_sequence=colors,
                                        marginal="violin" if show_box else None)
                fig_hist = style_fig(fig_hist)
                fig_hist.update_layout(height=350)
                st.plotly_chart(fig_hist, use_container_width=True)
            with col2:
                fig_box = px.box(df, y=sel_col, title=f"{sel_col} — Box Plot",
                                  color_discrete_sequence=colors)
                fig_box = style_fig(fig_box)
                fig_box.update_layout(height=350)
                st.plotly_chart(fig_box, use_container_width=True)

            stats = df[sel_col].describe()
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Mean",     f"{stats['mean']:.3f}")
            sc2.metric("Median",   f"{df[sel_col].median():.3f}")
            sc3.metric("Std Dev",  f"{stats['std']:.3f}")
            sc4.metric("Skewness", f"{df[sel_col].skew():.3f}")

    # ── Correlation ───────────────────────────────────────────────────────────
    with tabs[2]:
        if len(num_cols) < 2:
            st.info("At least 2 numeric columns are required for correlation analysis.")
        else:
            corr     = df[num_cols].corr()
            fig_heat = px.imshow(corr, title="Correlation Heatmap",
                                  color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                                  aspect="auto", text_auto=".2f")
            fig_heat = style_fig(fig_heat)
            fig_heat.update_layout(height=500)
            st.plotly_chart(fig_heat, use_container_width=True)

            st.markdown("#### Scatter Matrix")
            sc_cols  = st.multiselect("Columns:", num_cols, default=num_cols[:4], key="scatter_cols")
            if len(sc_cols) >= 2:
                color_by = st.selectbox("Color by:", ["None"] + cat_cols, key="scatter_color")
                fig_sm   = px.scatter_matrix(df, dimensions=sc_cols,
                                              color=color_by if color_by != "None" else None,
                                              color_discrete_sequence=colors)
                fig_sm = style_fig(fig_sm)
                fig_sm.update_layout(height=600)
                st.plotly_chart(fig_sm, use_container_width=True)

    # ── Statistics ────────────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("#### Descriptive Statistics")
        st.dataframe(df.describe(include="all").round(3), use_container_width=True)

        if cat_cols:
            st.markdown("#### Value Counts — Categorical Columns")
            sel_cat = st.selectbox("Column:", cat_cols, key="vc_cat")
            top_n   = st.slider("Top N values:", 5, 30, 10, key="vc_top")
            vc      = df[sel_cat].value_counts().head(top_n).reset_index()
            vc.columns = [sel_cat, "Count"]

            col1, col2 = st.columns(2)
            with col1:
                fig_bar = px.bar(vc, x=sel_cat, y="Count",
                                  title=f"Top {top_n} — {sel_cat}",
                                  color_discrete_sequence=colors)
                fig_bar = style_fig(fig_bar)
                st.plotly_chart(fig_bar, use_container_width=True)
            with col2:
                fig_pie = px.pie(vc, names=sel_cat, values="Count",
                                  title=f"{sel_cat} Distribution",
                                  color_discrete_sequence=colors)
                fig_pie = style_fig(fig_pie)
                st.plotly_chart(fig_pie, use_container_width=True)

    # ── Cross Analysis ────────────────────────────────────────────────────────
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
                if chart_t == "bar":
                    grouped = df.groupby(x_col)[y_col].agg(agg_f).reset_index()
                    fig = px.bar(
                        grouped, x=x_col, y=y_col,
                        title=f"{agg_f.title()} of {y_col} by {x_col}",
                        color_discrete_sequence=colors,
                    )
                elif chart_t == "line":
                    grouped = df.groupby(x_col)[y_col].agg(agg_f).reset_index()
                    fig = px.line(
                        grouped, x=x_col, y=y_col,
                        title=f"{agg_f.title()} of {y_col} by {x_col}",
                        color_discrete_sequence=colors,
                        markers=True,
                    )
                elif chart_t == "box":
                    fig = px.box(df, x=x_col if x_col in cat_cols else None, y=y_col,
                                  color=color_c if color_c != "None" else None,
                                  title=f"{y_col} by {x_col}",
                                  color_discrete_sequence=colors)
                elif chart_t == "violin":
                    fig = px.violin(df, x=x_col if x_col in cat_cols else None, y=y_col,
                                     color=color_c if color_c != "None" else None,
                                     box=True, title=f"{y_col} by {x_col}",
                                     color_discrete_sequence=colors)
                else:
                    fig = px.scatter(df, x=x_col, y=y_col,
                                      color=color_c if color_c != "None" else None,
                                      title=f"{x_col} vs {y_col}",
                                      color_discrete_sequence=colors)

                fig = style_fig(fig)
                fig.update_layout(height=450)
                st.plotly_chart(fig, use_container_width=True)
