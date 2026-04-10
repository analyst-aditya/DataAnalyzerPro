"""
pg_cleaning.py - Data Cleaning Studio
"""
import io
import streamlit as st
import pandas as pd
import numpy as np
from modules.data_utils import detect_data_problems, clean_data
from modules.i18n import t


def _col_selector(label: str, options: list, key: str, default=None) -> list:
    """Multiselect with a Select All checkbox."""
    if st.checkbox("Select All Columns", key=f"sel_all_{key}"):
        st.caption(f"All {len(options)} columns selected")
        return options
    return st.multiselect(label, options, default=default or [], key=key)


def page_cleaning(user: dict):
    st.title("🛠️ Data Cleaning Studio")

    dfs = st.session_state.get("uploaded_dfs", {})
    if not dfs:
        st.warning("⚠️ Please upload data from the Home page first.")
        return

    selected = st.selectbox("Select Dataset:", list(dfs.keys()))
    df_original = dfs[selected]

    key_clean = f"cleaned_{selected}"
    key_removed = f"removed_rows_{selected}"
    if key_clean not in st.session_state:
        st.session_state[key_clean] = df_original.copy()
    if key_removed not in st.session_state:
        st.session_state[key_removed] = pd.DataFrame()
    df = st.session_state[key_clean]

    orig_cols = len(df_original.columns)
    curr_cols = len(df.columns)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Original Rows", f"{len(df_original):,}")
    c2.metric("Current Rows",  f"{len(df):,}")
    c3.metric("Rows Removed",  f"{len(df_original) - len(df):,}")
    c4.metric("Columns Removed", f"{orig_cols - curr_cols:,}")
    c5.metric("Missing Values",f"{int(df.isna().sum().sum()):,}")

    undo_key = f"clean_undo_{selected}"
    if undo_key not in st.session_state:
        st.session_state[undo_key] = []

    def push_undo():
        hist = st.session_state[undo_key]
        hist.append(st.session_state[key_clean].copy())
        if len(hist) > 20:
            hist.pop(0)

    def apply_ops(ops):
        if not ops:
            st.info("No operations selected.")
            return
        push_undo()
        before_df = st.session_state[key_clean].copy()
        cleaned, summary = clean_data(st.session_state[key_clean].copy(), ops)
        # Track removed rows (those in before but not in cleaned, by index)
        removed_idx = before_df.index.difference(cleaned.index)
        if len(removed_idx) > 0:
            new_removed = before_df.loc[removed_idx]
            existing = st.session_state.get(key_removed, pd.DataFrame())
            st.session_state[key_removed] = pd.concat([existing, new_removed], ignore_index=True)
        st.session_state[key_clean]       = cleaned
        st.session_state["active_df"]     = cleaned
        st.session_state["active_df_name"] = selected
        st.success(f"✅ Done — {summary['changes']} row(s)/column(s) changed across {len(summary['operations'])} operation(s).")
        for m in summary["operations"]:
            st.markdown(f"  - {m}")
        st.rerun()

    undo_hist = st.session_state[undo_key]
    if undo_hist:
        if st.button(f"↩️ Undo ({len(undo_hist)} step(s))", key="clean_undo_btn"):
            st.session_state[key_clean] = undo_hist.pop()
            st.rerun()

    all_cols  = list(df.columns)
    num_cols  = [c for c in all_cols if pd.api.types.is_numeric_dtype(df[c])]
    text_cols = [c for c in all_cols if df[c].dtype == object]

    tabs = st.tabs([
        "🔍 Problem Scanner", "⚡ Auto Clean",
        "✏️ Manual Clean", "📦 Batch Operations", "👁️ Preview & Export", "🗑️ Removed Data"
    ])

    # ── Problem Scanner ───────────────────────────────────────────────────────
    with tabs[0]:
        if st.button("🔍 Scan for Problems", type="primary"):
            with st.spinner("Analyzing dataset..."):
                st.session_state[f"prob_{selected}"] = detect_data_problems(df)

        p = st.session_state.get(f"prob_{selected}")
        if p:
            sev  = p["summary"]["severity"]
            icon = {"None": "🟢", "Low": "🟡", "Medium": "🟠", "High": "🔴"}.get(sev, "⚪")
            st.markdown(f"### {icon} Severity: **{sev}**")
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("Empty Rows",     p["summary"]["total_empty_rows"])
            sc2.metric("Duplicate Rows", p["summary"]["total_duplicate_rows"])
            sc3.metric("Missing Values", p["summary"]["total_missing_values"])

            if p["missing_values"]:
                st.markdown("#### Missing Values by Column")
                st.dataframe(pd.DataFrame([
                    {"Column": x["column"], "Count": x["count"], "Percentage": f"{x['percentage']}%"}
                    for x in p["missing_values"]
                ]), use_container_width=True)

            if p["outliers"]:
                st.markdown("#### Outliers Detected (IQR Method)")
                st.dataframe(pd.DataFrame([
                    {"Column": x["column"], "Outlier Count": x["count"]}
                    for x in p["outliers"]
                ]), use_container_width=True)

            if p["invalid_emails"]:
                st.markdown("#### Invalid Email Addresses")
                for x in p["invalid_emails"]:
                    st.warning(f"Column '{x['column']}': {x['count']} invalid email(s) found.")

            if p["duplicate_rows"]:
                st.markdown(f"#### {len(p['duplicate_rows'])} Duplicate Rows Found")

    # ── Auto Clean ────────────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("### ⚡ One-Click Auto Clean")
        with st.form("auto_clean"):
            r1 = st.checkbox("Remove empty rows",                            value=True)
            r2 = st.checkbox("Remove duplicate rows",                        value=True)
            r3 = st.checkbox("Trim whitespace from text columns",            value=True)
            r4 = st.checkbox(f"Remove outliers ({len(num_cols)} numeric columns)", value=False)
            r5 = st.checkbox("Fill missing numeric values with column mean", value=False)
            go = st.form_submit_button("🚀 Run Auto Clean", type="primary", use_container_width=True)

        if go:
            ops = []
            if r1: ops.append({"type": "remove_empty_rows"})
            if r2: ops.append({"type": "remove_duplicates"})
            if r3 and text_cols: ops.append({"type": "trim_spaces", "columns": text_cols})
            if r4 and num_cols:  ops.append({"type": "remove_outliers", "columns": num_cols})
            if r5 and num_cols:  ops.append({"type": "fill_missing_mean", "columns": num_cols})
            apply_ops(ops)

    # ── Manual Clean ─────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown("### ✏️ Manual Cleaning Operations")
        cat = st.selectbox("Category:", [
            "Handle Missing Values",
            "Row Operations",
            "Text Operations",
            "Numeric Operations",
            "Type Conversion",
            "Column Operations",
        ])

        if cat == "Handle Missing Values":
            sel = _col_selector("Columns:", all_cols, "miss_col")
            method = st.selectbox("Fill Method:", [
                "Fill with mean",   "Fill with median", "Fill with zero",
                "Forward fill",     "Backward fill",
                "Fill with custom value", "Drop rows with missing values"
            ])
            cv = st.text_input("Custom fill value:") if method == "Fill with custom value" else ""
            if st.button("Apply", type="primary") and sel:
                mp = {
                    "Fill with mean":               "fill_missing_mean",
                    "Fill with median":             "fill_missing_median",
                    "Fill with zero":               "fill_missing_zero",
                    "Forward fill":                 "fill_missing_forward",
                    "Backward fill":                "fill_missing_backward",
                    "Fill with custom value":       "fill_missing_custom",
                    "Drop rows with missing values":"remove_missing_cols",
                }
                op = {"type": mp[method], "columns": sel}
                if method == "Fill with custom value":
                    op["value"] = cv
                apply_ops([op])

        elif cat == "Row Operations":
            rop = st.selectbox("Operation:", [
                "Remove empty rows", "Remove duplicate rows",
                "Remove rows with negative values", "Remove outlier rows (IQR)"
            ])
            needs_cols = rop in ["Remove rows with negative values", "Remove outlier rows (IQR)"]
            sel = _col_selector("Numeric Columns:", num_cols, "row_cols") if needs_cols else []
            if st.button("Apply", type="primary"):
                mp = {
                    "Remove empty rows":                "remove_empty_rows",
                    "Remove duplicate rows":            "remove_duplicates",
                    "Remove rows with negative values": "remove_negative",
                    "Remove outlier rows (IQR)":        "remove_outliers",
                }
                apply_ops([{"type": mp[rop], "columns": sel}])

        elif cat == "Text Operations":
            sel = _col_selector("Text Columns:", text_cols, "txt_cols")
            top = st.selectbox("Operation:", ["Trim whitespace", "Title Case", "Lowercase", "UPPERCASE"])
            if st.button("Apply", type="primary") and sel:
                mp = {
                    "Trim whitespace": "trim_spaces",
                    "Title Case":      "proper_case",
                    "Lowercase":       "lowercase",
                    "UPPERCASE":       "uppercase",
                }
                apply_ops([{"type": mp[top], "columns": sel}])

        elif cat == "Numeric Operations":
            sel = _col_selector("Numeric Columns:", num_cols, "numop_cols")
            nop = st.selectbox("Operation:", ["Remove outliers (IQR)", "Remove negative values"])
            if st.button("Apply", type="primary") and sel:
                mp = {
                    "Remove outliers (IQR)": "remove_outliers",
                    "Remove negative values":"remove_negative",
                }
                apply_ops([{"type": mp[nop], "columns": sel}])

        elif cat == "Type Conversion":
            sel = _col_selector("Columns:", all_cols, "typeconv_cols")
            to  = st.selectbox("Convert to:", ["Numeric", "Datetime"])
            if st.button("Apply", type="primary") and sel:
                mp = {"Numeric": "convert_numeric", "Datetime": "convert_datetime"}
                apply_ops([{"type": mp[to], "columns": sel}])

        elif cat == "Column Operations":
            st.markdown("**Remove unused or unwanted columns from the dataset.**")
            cols_to_remove = _col_selector("Select Columns to Remove:", all_cols, "col_remove_sel")
            if cols_to_remove:
                st.warning(f"⚠️ This will permanently remove {len(cols_to_remove)} column(s): {', '.join(cols_to_remove)}")
            if st.button("🗑️ Remove Selected Columns", type="primary") and cols_to_remove:
                apply_ops([{"type": "remove_columns", "columns": cols_to_remove}])

        st.markdown("---")
        r1c, r2c = st.columns(2)
        if r1c.button("🔄 Reset to Original Data", type="secondary", use_container_width=True):
            push_undo()
            st.session_state[key_clean] = df_original.copy()
            st.rerun()
        if r2c.button("↩️ Undo Last Step", use_container_width=True, disabled=not undo_hist):
            if undo_hist:
                st.session_state[key_clean] = undo_hist.pop()
                st.rerun()

    # ── Batch Operations ──────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("### 📦 Batch Operations")
        st.markdown("Queue multiple operations and run them all at once.")

        if "batch_ops" not in st.session_state:
            st.session_state["batch_ops"] = []

        bc1, bc2 = st.columns([2, 2])
        with bc1:
            bop = st.selectbox("Add operation:", [
                "remove_empty_rows", "remove_duplicates",
                "remove_columns",
                "trim_spaces", "proper_case", "lowercase", "uppercase",
                "fill_missing_mean", "fill_missing_median", "fill_missing_zero",
                "fill_missing_forward", "fill_missing_backward",
                "remove_outliers", "remove_negative",
            ], key="batch_op_sel")
        with bc2:
            bcols = _col_selector("Columns:", all_cols, "batch_cols_multi")

        if st.button("➕ Add to Queue"):
            st.session_state["batch_ops"].append({"type": bop, "columns": bcols})
            st.rerun()

        if st.session_state["batch_ops"]:
            st.markdown("**Queued Operations:**")
            for i, op in enumerate(st.session_state["batch_ops"]):
                x1, x2 = st.columns([4, 1])
                x1.markdown(f"`{i+1}. {op['type']}` — columns: {op.get('columns', [])}")
                if x2.button("❌", key=f"bq_{i}"):
                    st.session_state["batch_ops"].pop(i)
                    st.rerun()

            b1, b2 = st.columns(2)
            if b1.button("🚀 Run All Operations", type="primary", use_container_width=True):
                ops = st.session_state["batch_ops"].copy()
                st.session_state["batch_ops"] = []
                apply_ops(ops)
            if b2.button("🗑️ Clear Queue", use_container_width=True):
                st.session_state["batch_ops"] = []
                st.rerun()

    # ── Preview & Export ──────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("### 👁️ Data Preview")
        disp = _col_selector("Display Columns:", all_cols, "prev_cols", default=all_cols[:10])
        if not disp:
            disp = all_cols
        st.dataframe(df[disp].head(100), use_container_width=True)

        try:
            st.markdown("#### Descriptive Statistics")
            st.dataframe(df[disp].describe(include="all").round(3), use_container_width=True)
        except Exception:
            pass

        st.markdown("#### 📥 Export Cleaned Data")
        e1, e2, e3 = st.columns(3)

        buf = io.StringIO()
        df.to_csv(buf, index=False)
        e1.download_button("⬇️ Download CSV", buf.getvalue(),
                           file_name=f"cleaned_{selected}.csv",
                           mime="text/csv", use_container_width=True)

        buf2 = io.BytesIO()
        df.to_excel(buf2, index=False, engine="openpyxl")
        e2.download_button("⬇️ Download Excel", buf2.getvalue(),
                           file_name=f"cleaned_{selected}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)

        if e3.button("✅ Set as Active Dataset", type="primary", use_container_width=True):
            st.session_state["active_df"]      = df
            st.session_state["active_df_name"] = selected
            st.success("✅ This cleaned dataset is now the active dataset.")

    # ── Removed Data ──────────────────────────────────────────────────────────
    with tabs[5]:
        st.markdown("### 🗑️ Removed / Cleaned Out Data")
        removed_df = st.session_state.get(key_removed, pd.DataFrame())
        col_diff = [c for c in df_original.columns if c not in df.columns]
        if col_diff:
            st.markdown(f"#### 🗂️ Removed Columns ({len(col_diff)})")
            st.info(f"The following columns were removed: **{', '.join(col_diff)}**")
            st.markdown("**Sample data from removed columns (original dataset):**")
            st.dataframe(df_original[col_diff].head(50), use_container_width=True)
        if removed_df is not None and len(removed_df) > 0:
            st.markdown(f"#### 📋 Removed Rows ({len(removed_df):,} total)")
            st.caption("These are rows that were removed during cleaning operations (duplicates, empties, outliers, etc.)")
            st.dataframe(removed_df.head(200), use_container_width=True)
            buf = io.StringIO()
            removed_df.to_csv(buf, index=False)
            st.download_button("⬇️ Download Removed Rows (CSV)", buf.getvalue(),
                               file_name=f"removed_rows_{selected}.csv",
                               mime="text/csv")
            if st.button("🧹 Clear Removed Data Log", key="clear_removed"):
                st.session_state[key_removed] = pd.DataFrame()
                st.rerun()
        elif not col_diff:
            st.info("No data has been removed yet. Perform cleaning operations to see removed rows/columns here.")
