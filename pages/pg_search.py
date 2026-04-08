"""
pg_search.py - Data Search
Placed after Cleaning Studio — uses active (cleaned) dataset by default.
"""
import re
import io
import streamlit as st
import pandas as pd
import numpy as np
from modules.i18n import t


def page_search(user: dict):
    st.title(t("search_title"))

    # ── Dataset selection: prefer cleaned/active, fallback to uploaded ────────
    active_df   = st.session_state.get("active_df")
    active_name = st.session_state.get("active_df_name", "")
    uploaded    = st.session_state.get("uploaded_dfs", {})

    if active_df is None and not uploaded:
        st.warning(t("warning_upload"))
        return

    # Build source options
    source_opts = {}
    if active_df is not None:
        label = f"✅ {active_name} (active / cleaned)"
        source_opts[label] = ("active", active_df, active_name)
    for fname, fdf in uploaded.items():
        if fname != active_name:
            source_opts[f"📄 {fname}"] = ("uploaded", fdf, fname)

    # Show notice about what data is being searched
    if active_df is not None:
        st.info(
            f"Searching in **active dataset**: `{active_name}` "
            f"({len(active_df):,} rows). "
            "This is your cleaned/processed data. "
            "You can switch to another dataset below."
        )

    sel_label = st.selectbox(t("search_in"), list(source_opts.keys()), key="search_source_sel")
    _, df, ds_name = source_opts[sel_label]

    st.caption(f"Dataset: **{ds_name}** — {len(df):,} rows × {len(df.columns)} columns")

    # ── Search mode ────────────────────────────────────────────────────────────
    mode = st.selectbox(t("search_mode"), [
        "🔎 Simple Search",
        "🔧 Regex Search",
        "📊 Column Filter",
        "🔢 Numeric Range",
        "🌐 Multi-column Search",
    ], key="search_mode_sel")

    st.markdown("---")
    result_df = None
    match_info = ""

    # ── 1. Simple Search ───────────────────────────────────────────────────────
    if mode == "🔎 Simple Search":
        c1, c2, c3 = st.columns([3, 2, 1])
        query   = c1.text_input(t("search_query"), placeholder="Type any text or number...", key="sq")
        s_cols  = c2.multiselect("Columns (empty = all):", list(df.columns), key="sq_cols")
        case_s  = c3.checkbox("Case Sensitive", value=False, key="sq_case")

        if query:
            search_in = s_cols if s_cols else list(df.columns)
            mask = pd.Series([False] * len(df), index=df.index)
            for col in search_in:
                try:
                    col_str = df[col].astype(str)
                    if case_s:
                        mask |= col_str.str.contains(query, na=False, regex=False)
                    else:
                        mask |= col_str.str.contains(query, case=False, na=False, regex=False)
                except Exception:
                    pass
            result_df  = df[mask]
            match_info = f"**{len(result_df):,}** rows matched '{query}' (out of {len(df):,})"

    # ── 2. Regex Search ────────────────────────────────────────────────────────
    elif mode == "🔧 Regex Search":
        c1, c2 = st.columns([3, 2])
        rx   = c1.text_input("Regex Pattern:", placeholder=r"e.g.  ^\d{3}  or  [A-Z]{2,}", key="rx_q")
        rcols = c2.multiselect("Columns:", list(df.columns), key="rx_cols")
        if rx:
            try:
                search_in = rcols if rcols else list(df.columns)
                mask = pd.Series([False] * len(df), index=df.index)
                for col in search_in:
                    mask |= df[col].astype(str).str.contains(rx, na=False, regex=True)
                result_df  = df[mask]
                match_info = f"**{len(result_df):,}** rows matched the regex pattern"
            except re.error as e:
                st.error(f"Invalid regex: {e}")

    # ── 3. Column Filter ───────────────────────────────────────────────────────
    elif mode == "📊 Column Filter":
        c1, c2, c3 = st.columns([2, 2, 2])
        fcol = c1.selectbox("Column:", list(df.columns), key="cf_col")
        is_num = pd.api.types.is_numeric_dtype(df[fcol])
        operators = ["==","!=",">",">=","<","<="] if is_num else \
                    ["Contains","Not Contains","Equals","Not Equals",
                     "Starts With","Ends With","Is Empty","Is Not Empty"]
        op   = c2.selectbox("Operator:", operators, key="cf_op")
        fval = c3.text_input("Value:", key="cf_val") if op not in ("Is Empty","Is Not Empty") else ""

        if st.button(t("search_btn"), type="primary"):
            try:
                if is_num:
                    nv = float(fval) if fval else 0
                    ops_map = {"==": df[fcol]==nv, "!=": df[fcol]!=nv,
                               ">":  df[fcol]>nv,  ">=": df[fcol]>=nv,
                               "<":  df[fcol]<nv,  "<=": df[fcol]<=nv}
                    mask = ops_map.get(op, pd.Series([True]*len(df), index=df.index))
                else:
                    cs = df[fcol].astype(str)
                    if op == "Contains":       mask = cs.str.contains(fval, case=False, na=False)
                    elif op == "Not Contains": mask = ~cs.str.contains(fval, case=False, na=False)
                    elif op == "Equals":       mask = cs.str.lower() == fval.lower()
                    elif op == "Not Equals":   mask = cs.str.lower() != fval.lower()
                    elif op == "Starts With":  mask = cs.str.lower().str.startswith(fval.lower())
                    elif op == "Ends With":    mask = cs.str.lower().str.endswith(fval.lower())
                    elif op == "Is Empty":     mask = cs.str.strip().eq("") | df[fcol].isna()
                    elif op == "Is Not Empty": mask = cs.str.strip().ne("") & df[fcol].notna()
                    else: mask = pd.Series([True]*len(df), index=df.index)
                result_df  = df[mask]
                match_info = f"**{len(result_df):,}** rows after filter"
                st.session_state["_search_result"] = result_df
            except Exception as e:
                st.error(f"Filter error: {e}")
        result_df = st.session_state.get("_search_result")

    # ── 4. Numeric Range ───────────────────────────────────────────────────────
    elif mode == "🔢 Numeric Range":
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not num_cols:
            st.warning("No numeric columns found in this dataset.")
        else:
            c1, c2, c3 = st.columns(3)
            rcol  = c1.selectbox("Numeric Column:", num_cols, key="nr_col")
            rmin  = c2.number_input("Minimum:", value=float(df[rcol].min()), key="nr_min")
            rmax  = c3.number_input("Maximum:", value=float(df[rcol].max()), key="nr_max")
            if st.button(t("search_btn"), type="primary"):
                mask      = (df[rcol] >= rmin) & (df[rcol] <= rmax)
                result_df = df[mask]
                match_info = f"**{len(result_df):,}** rows in range [{rmin:,.2f} — {rmax:,.2f}]"
                st.session_state["_search_result"] = result_df
            result_df = st.session_state.get("_search_result")

    # ── 5. Multi-column Search ─────────────────────────────────────────────────
    elif mode == "🌐 Multi-column Search":
        st.markdown("**Multiple conditions (AND logic):**")
        n = int(st.number_input("Number of conditions:", 1, 6, 2, key="mc_n"))
        conds = []
        for i in range(n):
            cx1, cx2, cx3 = st.columns([2, 2, 3])
            cc  = cx1.selectbox(f"Column {i+1}", list(df.columns), key=f"mc_col_{i}")
            cop = cx2.selectbox(f"Op {i+1}",
                                ["Contains","Equals",">=","<=",">","<"], key=f"mc_op_{i}")
            cv  = cx3.text_input(f"Value {i+1}", key=f"mc_val_{i}")
            conds.append((cc, cop, cv))

        if st.button(t("search_btn"), type="primary"):
            mask = pd.Series([True]*len(df), index=df.index)
            for (col, op, val) in conds:
                if not val:
                    continue
                try:
                    if op == "Contains":
                        mask &= df[col].astype(str).str.contains(val, case=False, na=False)
                    elif op == "Equals":
                        mask &= df[col].astype(str).str.lower() == val.lower()
                    elif pd.api.types.is_numeric_dtype(df[col]):
                        nv = float(val)
                        if op == ">=": mask &= df[col] >= nv
                        elif op == "<=": mask &= df[col] <= nv
                        elif op == ">":  mask &= df[col] > nv
                        elif op == "<":  mask &= df[col] < nv
                except Exception:
                    pass
            result_df  = df[mask]
            match_info = f"**{len(result_df):,}** rows matched all conditions"
            st.session_state["_search_result"] = result_df
        result_df = st.session_state.get("_search_result")

    # ── Results display ────────────────────────────────────────────────────────
    if result_df is not None:
        st.markdown("---")
        st.markdown(f"### 📋 {t('results')}")
        if match_info:
            st.success(match_info)

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Matched Rows",   f"{len(result_df):,}")
        r2.metric("Total Rows",     f"{len(df):,}")
        r3.metric("Match %",        f"{len(result_df)/max(len(df),1)*100:.1f}%")
        r4.metric("Columns",        len(result_df.columns))

        # Column display selector
        disp_cols = st.multiselect(
            "Display columns:",
            list(result_df.columns),
            default=list(result_df.columns)[:10],
            key="res_disp_cols"
        )
        st.dataframe(
            result_df[disp_cols if disp_cols else result_df.columns],
            use_container_width=True,
            height=400,
        )

        # Export
        st.markdown("#### 📥 Export Results")
        ec1, ec2, ec3 = st.columns(3)

        buf_csv = io.StringIO()
        result_df.to_csv(buf_csv, index=False)
        ec1.download_button(t("download_csv"), buf_csv.getvalue(),
                             file_name="search_results.csv",
                             mime="text/csv", use_container_width=True)

        buf_xl = io.BytesIO()
        result_df.to_excel(buf_xl, index=False, engine="openpyxl")
        ec2.download_button(t("download_excel"), buf_xl.getvalue(),
                             file_name="search_results.xlsx",
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             use_container_width=True)

        if ec3.button(t("set_active_btn"), use_container_width=True):
            st.session_state["active_df"]      = result_df.reset_index(drop=True)
            st.session_state["active_df_name"] = f"search_result_{ds_name}"
            st.success("Search result is now the active dataset!")

        # Quick chart
        st.markdown("---")
        st.markdown("#### 📊 Quick Chart from Results")
        num_rc = [c for c in result_df.columns if pd.api.types.is_numeric_dtype(result_df[c])]
        cat_rc = [c for c in result_df.columns if not pd.api.types.is_numeric_dtype(result_df[c])]
        if num_rc and cat_rc:
            qc1, qc2, qc3 = st.columns(3)
            qx = qc1.selectbox("X Axis:",    cat_rc, key="qc_x")
            qy = qc2.selectbox("Y Axis:",    num_rc, key="qc_y")
            qt = qc3.selectbox("Chart Type:",["bar","line","pie","scatter"], key="qc_t")
            if st.button("📊 Generate Chart", type="primary"):
                from modules.chart_utils import make_chart
                fig = make_chart(result_df, {
                    "type": qt, "xcol": qx, "ycol": qy,
                    "title": f"{qx} vs {qy}",
                    "theme": "Default"
                })
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

        if st.button(t("clear_search"), key="clr_search"):
            st.session_state.pop("_search_result", None)
            st.rerun()

    else:
        # Default view: show column summary of selected dataset
        st.markdown("---")
        st.markdown(f"### 📄 Dataset Overview — {ds_name}")
        stats = []
        for col in df.columns:
            stats.append({
                "Column":     col,
                "Type":       str(df[col].dtype),
                "Non-Null":   int(df[col].notna().sum()),
                "Null":       int(df[col].isna().sum()),
                "Unique":     int(df[col].nunique()),
                "Sample":     str(df[col].dropna().iloc[0]) if df[col].notna().any() else "—",
            })
        st.dataframe(pd.DataFrame(stats), use_container_width=True)
        st.dataframe(df.head(20), use_container_width=True)
