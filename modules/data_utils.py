"""
data_utils.py - Data quality detection and cleaning operations
UPDATED: Added remove_columns operation
"""
import copy
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple


# ─── Data quality detection ───────────────────────────────────────────────────

def detect_data_problems(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyse a DataFrame and return a structured problems report."""
    df_clean = df.copy().replace(r"^\s*$", np.nan, regex=True)

    problems: Dict[str, Any] = {
        "empty_rows": [],
        "duplicate_rows": [],
        "missing_values": [],
        "negative_values": [],
        "text_in_numeric": [],
        "invalid_emails": [],
        "outliers": [],
        "summary": {
            "total_empty_rows": 0,
            "total_duplicate_rows": 0,
            "total_missing_values": 0,
            "severity": "None",
        },
    }

    # Empty rows (completely empty OR >50% missing)
    completely_empty = df_clean[df_clean.isna().all(axis=1)].index.tolist()
    mostly_empty = df_clean[df_clean.isna().mean(axis=1) > 0.5].index.tolist()
    empty_rows = sorted(set(completely_empty + mostly_empty))
    problems["empty_rows"] = empty_rows
    problems["summary"]["total_empty_rows"] = len(empty_rows)

    # Duplicate rows
    dup_mask = df_clean.duplicated(keep="first")
    problems["duplicate_rows"] = df_clean[dup_mask].index.tolist()
    problems["summary"]["total_duplicate_rows"] = int(dup_mask.sum())

    # Missing values per column
    for col in df.columns:
        missing_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
        count = int(missing_mask.sum())
        if count > 0:
            problems["missing_values"].append({
                "column": col,
                "count": count,
                "percentage": round(count / len(df) * 100, 2),
                "rows": df[missing_mask].index.tolist()[:10],
            })
        problems["summary"]["total_missing_values"] += count

    # Negative values
    for col in df.select_dtypes(include=[np.number]).columns:
        neg = df[df[col] < 0].index.tolist()
        if neg:
            problems["negative_values"].append({"column": col, "count": len(neg), "rows": neg[:10]})

    # Text in numeric-looking columns
    for col in df.select_dtypes(include="object").columns:
        try:
            coerced = pd.to_numeric(df[col], errors="coerce")
            text_rows = df[coerced.isna() & df[col].notna()].index.tolist()
            if text_rows:
                problems["text_in_numeric"].append({"column": col, "count": len(text_rows), "rows": text_rows[:10]})
        except Exception:
            pass

    # Invalid emails
    email_re = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    for col in df.columns:
        if any(kw in col.lower() for kw in ("email", "mail", "e-mail")):
            invalid = df[~df[col].astype(str).str.match(email_re, na=False)].index.tolist()
            if invalid:
                problems["invalid_emails"].append({"column": col, "count": len(invalid), "rows": invalid[:10]})

    # Outliers (IQR method)
    for col in df.select_dtypes(include=[np.number]).columns:
        q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        outlier_mask = (df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)
        out_rows = df[outlier_mask].index.tolist()
        if out_rows:
            problems["outliers"].append({"column": col, "count": len(out_rows), "rows": out_rows[:10]})

    # Severity
    total = (
        len(empty_rows)
        + problems["summary"]["total_duplicate_rows"]
        + problems["summary"]["total_missing_values"]
        + sum(p["count"] for p in problems["negative_values"])
        + sum(p["count"] for p in problems["text_in_numeric"])
        + sum(p["count"] for p in problems["invalid_emails"])
        + sum(p["count"] for p in problems["outliers"])
    )
    if total == 0:
        problems["summary"]["severity"] = "None"
    elif total < len(df) * 0.05:
        problems["summary"]["severity"] = "Low"
    elif total < len(df) * 0.15:
        problems["summary"]["severity"] = "Medium"
    else:
        problems["summary"]["severity"] = "High"

    return problems


# ─── Data cleaning operations ────────────────────────────────────────────────

def clean_data(df: pd.DataFrame, operations: List[Dict]) -> Tuple[pd.DataFrame, Dict]:
    """Apply a list of cleaning operations and return (cleaned_df, summary)."""
    summary = {"operations": [], "rows_before": len(df), "rows_after": 0, "changes": 0}

    for op in operations:
        op_type = op.get("type")
        cols = op.get("columns", [])

        try:
            # NEW: Remove specific columns
            if op_type == "remove_columns" and cols:
                existing_to_drop = [c for c in cols if c in df.columns]
                if existing_to_drop:
                    df = df.drop(columns=existing_to_drop)
                    summary["operations"].append(f"Dropped columns: {', '.join(existing_to_drop)}")
                    summary["changes"] += 1

            elif op_type == "remove_empty_rows":
                before = len(df)
                df = df.dropna(how="all")
                removed = before - len(df)
                summary["operations"].append(f"Removed {removed} empty rows")
                summary["changes"] += removed

            elif op_type == "remove_duplicates":
                before = len(df)
                df = df.drop_duplicates()
                removed = before - len(df)
                summary["operations"].append(f"Removed {removed} duplicate rows")
                summary["changes"] += removed

            elif op_type == "remove_missing_all":
                before = len(df)
                df = df.replace(r"^\s*$", np.nan, regex=True).dropna()
                removed = before - len(df)
                summary["operations"].append(f"Removed {removed} rows with any missing value")
                summary["changes"] += removed

            elif op_type == "remove_missing_cols" and cols:
                before = len(df)
                df_check = df.replace(r"^\s*$", np.nan, regex=True)
                keep = df_check.dropna(subset=cols, how="any").index
                df = df.loc[keep]
                removed = before - len(df)
                summary["operations"].append(f"Removed {removed} rows with missing in {cols}")
                summary["changes"] += removed

            elif op_type == "remove_negative" and cols:
                for col in cols:
                    if col in df.columns:
                        before = len(df)
                        df = df[df[col] >= 0]
                        summary["operations"].append(f"Removed {before - len(df)} negative rows in '{col}'")
                        summary["changes"] += before - len(df)

            elif op_type == "remove_outliers" and cols:
                for col in cols:
                    if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                        q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
                        iqr = q3 - q1
                        before = len(df)
                        df = df[(df[col] >= q1 - 1.5 * iqr) & (df[col] <= q3 + 1.5 * iqr)]
                        summary["operations"].append(f"Removed {before - len(df)} outliers from '{col}'")
                        summary["changes"] += before - len(df)

            elif op_type == "fill_missing_mean" and cols:
                for col in cols:
                    if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                        n = int(df[col].isna().sum())
                        if n:
                            df[col] = df[col].fillna(df[col].mean())
                            summary["operations"].append(f"Filled {n} missing in '{col}' with mean")

            elif op_type == "fill_missing_median" and cols:
                for col in cols:
                    if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                        n = int(df[col].isna().sum())
                        if n:
                            df[col] = df[col].fillna(df[col].median())
                            summary["operations"].append(f"Filled {n} missing in '{col}' with median")

            elif op_type == "fill_missing_zero" and cols:
                for col in cols:
                    if col in df.columns:
                        n = int(df[col].isna().sum())
                        if n:
                            df[col] = df[col].fillna(0)
                            summary["operations"].append(f"Filled {n} missing in '{col}' with 0")

            elif op_type == "fill_missing_forward" and cols:
                for col in cols:
                    if col in df.columns:
                        n = int(df[col].isna().sum())
                        if n:
                            df[col] = df[col].ffill()
                            summary["operations"].append(f"Forward-filled {n} missing in '{col}'")

            elif op_type == "fill_missing_backward" and cols:
                for col in cols:
                    if col in df.columns:
                        n = int(df[col].isna().sum())
                        if n:
                            df[col] = df[col].bfill()
                            summary["operations"].append(f"Backward-filled {n} missing in '{col}'")

            elif op_type == "fill_missing_custom" and cols:
                custom = op.get("value", "")
                try:
                    val = float(custom) if "." in custom else int(custom)
                except ValueError:
                    val = custom
                for col in cols:
                    if col in df.columns:
                        n = int(df[col].isna().sum())
                        if n:
                            df[col] = df[col].fillna(val)
                            summary["operations"].append(f"Filled {n} missing in '{col}' with '{custom}'")

            elif op_type == "trim_spaces" and cols:
                for col in cols:
                    if col in df.columns and df[col].dtype == object:
                        df[col] = df[col].str.strip()
                        summary["operations"].append(f"Trimmed spaces in '{col}'")

            elif op_type == "proper_case" and cols:
                for col in cols:
                    if col in df.columns and df[col].dtype == object:
                        df[col] = df[col].str.title()
                        summary["operations"].append(f"Converted '{col}' to title case")

            elif op_type == "lowercase" and cols:
                for col in cols:
                    if col in df.columns and df[col].dtype == object:
                        df[col] = df[col].str.lower()
                        summary["operations"].append(f"Lowercased '{col}'")

            elif op_type == "uppercase" and cols:
                for col in cols:
                    if col in df.columns and df[col].dtype == object:
                        df[col] = df[col].str.upper()
                        summary["operations"].append(f"Uppercased '{col}'")

            elif op_type == "fix_emails" and cols:
                email_re = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
                for col in cols:
                    if col in df.columns:
                        before = len(df)
                        df = df[df[col].astype(str).str.match(email_re, na=False)]
                        summary["operations"].append(f"Removed {before - len(df)} invalid emails in '{col}'")
                        summary["changes"] += before - len(df)

            elif op_type == "convert_numeric" and cols:
                for col in cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                        summary["operations"].append(f"Converted '{col}' to numeric")

            elif op_type == "convert_datetime" and cols:
                for col in cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors="coerce")
                        summary["operations"].append(f"Converted '{col}' to datetime")

        except Exception as e:
            summary["operations"].append(f"[ERROR] {op_type}: {e}")

    summary["rows_after"] = len(df)
    return df, summary