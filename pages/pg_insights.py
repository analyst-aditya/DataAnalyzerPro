"""
pg_insights.py - Statistical Insights Page
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats as scipy_stats
from modules.chart_utils import CHART_THEMES


def page_insights(user: dict):
    st.title("🤖 AI Insights & Analysis")
    st.markdown("Discover deep statistical insights and patterns in your data.")

    df = st.session_state.get("active_df")
    if df is None:
        st.warning("⚠️ Please upload data from the Home page first.")
        return

    name      = st.session_state.get("active_df_name", "Dataset")
    num_cols  = list(df.select_dtypes(include=[np.number]).columns)
    cat_cols  = list(df.select_dtypes(include="object").columns)
    theme_name = st.selectbox("Theme:", list(CHART_THEMES.keys()), key="insights_theme")
    colors    = CHART_THEMES[theme_name]["colors"]

    if st.button("🧠 Generate Insights", type="primary"):
        with st.spinner("Analyzing your dataset..."):
            _show_insights(df, num_cols, cat_cols, colors, name)
    else:
        _show_insights(df, num_cols, cat_cols, colors, name)


def _show_insights(df, num_cols, cat_cols, colors, name):
    tabs = st.tabs([
        "📊 Dataset Summary", "📈 Trends & Patterns",
        "🔍 Outlier Analysis", "📐 Statistical Tests", "💡 Recommendations"
    ])

    with tabs[0]:
        st.markdown(f"### Dataset: {name}")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Rows",             f"{len(df):,}")
        c2.metric("Columns",          len(df.columns))
        c3.metric("Numeric Columns",  len(num_cols))
        c4.metric("Categorical Cols", len(cat_cols))
        c5.metric("Missing %",        f"{df.isna().mean().mean() * 100:.1f}%")

        mem_mb = df.memory_usage(deep=True).sum() / 1024 ** 2
        st.caption(f"Memory usage: {mem_mb:.2f} MB")

        dtype_counts = df.dtypes.value_counts()
        fig_types = px.pie(
            values=dtype_counts.values,
            names=[str(d) for d in dtype_counts.index],
            color_discrete_sequence=colors,
            title="Column Data Types"
        )
        fig_types.update_layout(height=300)
        st.plotly_chart(fig_types, use_container_width=True)

        if df.isna().sum().sum() > 0:
            st.markdown("#### Missing Values")
            miss_df = df.isna().sum().reset_index()
            miss_df.columns = ["Column", "Missing Count"]
            miss_df = miss_df[miss_df["Missing Count"] > 0].sort_values("Missing Count", ascending=False)
            if len(miss_df):
                fig_miss = px.bar(miss_df, x="Column", y="Missing Count",
                                  title="Missing Values per Column",
                                  color_discrete_sequence=colors)
                st.plotly_chart(fig_miss, use_container_width=True)
        else:
            st.success("✅ No missing values found in this dataset!")

    with tabs[1]:
        if not num_cols:
            st.info("No numeric columns available for trend analysis.")
            return

        date_cols = [c for c in df.columns if any(k in c.lower() for k in ("date","time","year","month","day"))]
        if date_cols and num_cols:
            st.markdown("#### Time-based Trends")
            dc = st.selectbox("Date column:", date_cols, key="trend_date")
            vc = st.selectbox("Value column:", num_cols, key="trend_val")
            try:
                trend_df = df[[dc, vc]].copy()
                trend_df[dc] = pd.to_datetime(trend_df[dc], errors="coerce")
                trend_df = trend_df.dropna().sort_values(dc)
                fig_trend = px.line(trend_df, x=dc, y=vc, title=f"{vc} Over Time",
                                    markers=True, color_discrete_sequence=colors)
                st.plotly_chart(fig_trend, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not render trend chart: {e}")

        if cat_cols:
            st.markdown("#### Category Patterns")
            sel_cat = st.selectbox("Categorical column:", cat_cols, key="pattern_cat")
            if num_cols:
                sel_num = st.selectbox("Numeric column:", num_cols, key="pattern_num")
                grouped = df.groupby(sel_cat)[sel_num].mean().sort_values(ascending=False).head(20)
                fig_cat = px.bar(grouped.reset_index(), x=sel_cat, y=sel_num,
                                 title=f"Average {sel_num} by {sel_cat}",
                                 color_discrete_sequence=colors)
                st.plotly_chart(fig_cat, use_container_width=True)

        if len(num_cols) >= 2:
            st.markdown("#### Top Correlations")
            corr  = df[num_cols].corr()
            pairs = []
            for i in range(len(corr.columns)):
                for j in range(i + 1, len(corr.columns)):
                    pairs.append({
                        "Column 1":    corr.columns[i],
                        "Column 2":    corr.columns[j],
                        "Correlation": round(corr.iloc[i, j], 4),
                        "Abs":         abs(corr.iloc[i, j]),
                    })
            if pairs:
                corr_df = pd.DataFrame(pairs).sort_values("Abs", ascending=False).head(10)
                corr_df["Strength"] = corr_df["Abs"].apply(
                    lambda x: "Very Strong" if x > 0.8 else
                              "Strong"      if x > 0.6 else
                              "Moderate"    if x > 0.4 else "Weak"
                )
                st.dataframe(corr_df[["Column 1","Column 2","Correlation","Strength"]],
                             use_container_width=True)

    with tabs[2]:
        if not num_cols:
            st.info("No numeric columns available for outlier analysis.")
            return

        outlier_col = st.selectbox("Select column:", num_cols, key="outlier_col")
        col_data    = df[outlier_col].dropna()
        q1, q3      = col_data.quantile(0.25), col_data.quantile(0.75)
        iqr         = q3 - q1
        lower       = q1 - 1.5 * iqr
        upper       = q3 + 1.5 * iqr
        outliers    = col_data[(col_data < lower) | (col_data > upper)]

        oc1, oc2, oc3 = st.columns(3)
        oc1.metric("Total Values",   f"{len(col_data):,}")
        oc2.metric("Outliers Found", f"{len(outliers):,}")
        oc3.metric("Outlier %",      f"{len(outliers) / max(len(col_data), 1) * 100:.2f}%")

        fig_box = go.Figure()
        fig_box.add_trace(go.Box(y=col_data, name=outlier_col, boxpoints="outliers",
                                  marker_color=colors[0]))
        fig_box.add_hline(y=lower, line_dash="dash", line_color="red",
                          annotation_text=f"Lower bound: {lower:.2f}")
        fig_box.add_hline(y=upper, line_dash="dash", line_color="red",
                          annotation_text=f"Upper bound: {upper:.2f}")
        fig_box.update_layout(title=f"{outlier_col} — Outlier Analysis", height=400)
        st.plotly_chart(fig_box, use_container_width=True)

        if len(outliers):
            with st.expander("View outlier rows"):
                st.dataframe(df[df[outlier_col].isin(outliers)], use_container_width=True)

    with tabs[3]:
        if len(num_cols) < 2:
            st.info("At least 2 numeric columns are required for statistical tests.")
            return

        st.markdown("#### Normality Test (Shapiro–Wilk)")
        test_col  = st.selectbox("Column:", num_cols, key="test_col")
        col_data  = df[test_col].dropna()

        if len(col_data) > 5000:
            sample = col_data.sample(5000, random_state=42)
            st.caption("Using a random sample of 5,000 rows for performance.")
        else:
            sample = col_data

        if len(sample) >= 3:
            try:
                stat, p_val = scipy_stats.shapiro(sample)
                st.metric("Shapiro–Wilk Statistic", f"{stat:.4f}")
                st.metric("P-value", f"{p_val:.4f}")
                if p_val > 0.05:
                    st.success("✅ Data appears to be normally distributed (p > 0.05).")
                else:
                    st.warning("⚠️ Data does not follow a normal distribution (p ≤ 0.05).")
            except Exception as e:
                st.error(f"Test could not be completed: {e}")

        if len(num_cols) >= 2 and cat_cols:
            st.markdown("#### Independent Samples T-Test")
            t1, t2, t3 = st.columns(3)
            group_col     = t1.selectbox("Group column:", cat_cols, key="ttest_grp")
            value_col     = t2.selectbox("Value column:", num_cols, key="ttest_val")
            unique_groups = df[group_col].unique()
            if len(unique_groups) >= 2:
                g1 = t3.selectbox("Group 1:", unique_groups[:10], key="grp1")
                g2 = st.selectbox("Group 2:", [g for g in unique_groups[:10] if g != g1], key="grp2")
                if st.button("Run T-Test"):
                    d1 = df[df[group_col] == g1][value_col].dropna()
                    d2 = df[df[group_col] == g2][value_col].dropna()
                    t_stat, t_p = scipy_stats.ttest_ind(d1, d2)
                    st.metric("T-Statistic", f"{t_stat:.4f}")
                    st.metric("P-Value",     f"{t_p:.4f}")
                    if t_p < 0.05:
                        st.success(f"✅ Statistically significant difference between '{g1}' and '{g2}' (p < 0.05).")
                    else:
                        st.info(f"No statistically significant difference between '{g1}' and '{g2}' (p ≥ 0.05).")

    with tabs[4]:
        st.markdown("### 💡 Data Quality Recommendations")
        recs     = []
        miss_pct = df.isna().mean().mean() * 100

        if miss_pct > 10:
            recs.append(("🔴 High",   f"{miss_pct:.1f}% of values are missing — use the Cleaning Studio to address this."))
        elif miss_pct > 0:
            recs.append(("🟡 Medium", f"Some missing values detected ({miss_pct:.1f}%) — review and handle as needed."))

        dup = int(df.duplicated().sum())
        if dup > 0:
            recs.append(("🟠 Medium", f"{dup} duplicate row(s) detected — consider removing them."))

        if num_cols:
            for col in num_cols[:5]:
                skew = df[col].skew()
                if abs(skew) > 2:
                    recs.append(("🟡 Info",
                                  f"'{col}' is highly skewed (skew = {skew:.2f}). Consider a log transformation."))

        if len(num_cols) >= 2:
            corr = df[num_cols].corr()
            for i in range(len(num_cols)):
                for j in range(i + 1, len(num_cols)):
                    val = abs(corr.iloc[i, j])
                    if val > 0.9:
                        recs.append(("🟡 Info",
                                      f"'{num_cols[i]}' and '{num_cols[j]}' are highly correlated ({val:.2f}). "
                                      "This may indicate multicollinearity."))

        if not recs:
            recs.append(("🟢 Good", "The dataset looks clean and well-structured!"))

        color_map = {
            "🔴 High":   "#fee2e2", "🟠 Medium": "#fef3c7",
            "🟡 Medium": "#fef3c7", "🟡 Info":   "#eff6ff",
            "🟢 Good":   "#d1fae5",
        }
        for severity, msg in recs:
            bg = color_map.get(severity, "#f3f4f6")
            st.markdown(f"""
            <div style='background:{bg};padding:10px 16px;border-radius:8px;margin:6px 0'>
                <strong>{severity}</strong> — {msg}
            </div>
            """, unsafe_allow_html=True)
