"""
pg_home.py - Home page with multi-file upload
"""
import streamlit as st
import pandas as pd
from modules.database import log_activity


def page_home(user: dict):
    st.title("🏠 Home — Data Upload")
    st.markdown(f"Welcome, **{user['username']}**! Upload CSV or Excel files to get started.")

    st.markdown("### 📁 File Upload")
    uploaded_files = st.file_uploader(
        "Drag and drop CSV or Excel files here, or click to browse",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        help="Maximum 200 MB per file. Multiple files are supported.",
    )

    if uploaded_files:
        if "uploaded_dfs" not in st.session_state:
            st.session_state["uploaded_dfs"] = {}

        newly_added = []
        for file in uploaded_files:
            if file.name not in st.session_state["uploaded_dfs"]:
                try:
                    if file.name.endswith(".csv"):
                        df = pd.read_csv(file, encoding="utf-8", on_bad_lines="skip")
                    else:
                        df = pd.read_excel(file)
                    st.session_state["uploaded_dfs"][file.name] = df
                    newly_added.append(file.name)
                    log_activity(user["id"], "upload", f"File: {file.name}, Rows: {len(df)}")
                except Exception as e:
                    st.error(f"❌ Could not read {file.name}: {e}")

        if newly_added:
            st.success(f"✅ {len(newly_added)} file(s) loaded: {', '.join(newly_added)}")

    dfs = st.session_state.get("uploaded_dfs", {})
    if dfs:
        st.markdown("### 📊 Loaded Files")
        for fname, df in dfs.items():
            with st.expander(f"📄 {fname}  —  {len(df):,} rows × {len(df.columns)} columns", expanded=False):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Rows",           f"{len(df):,}")
                col2.metric("Columns",        len(df.columns))
                col3.metric("Missing Values", f"{df.isna().sum().sum():,}")
                mb = df.memory_usage(deep=True).sum() / 1024 ** 2
                col4.metric("Memory",         f"{mb:.2f} MB")

                st.markdown("**Preview (first 5 rows):**")
                st.dataframe(df.head(5), use_container_width=True)

                c1, c2 = st.columns(2)
                if c1.button("✅ Set as Active", key=f"active_{fname}"):
                    st.session_state["active_df_name"] = fname
                    st.session_state["active_df"]      = df
                    st.success(f"'{fname}' is now the active dataset.")

                if c2.button("🗑️ Remove", key=f"remove_{fname}"):
                    del st.session_state["uploaded_dfs"][fname]
                    if st.session_state.get("active_df_name") == fname:
                        st.session_state.pop("active_df_name", None)
                        st.session_state.pop("active_df", None)
                    st.rerun()

        active = st.session_state.get("active_df_name")
        if active:
            st.info(f"🎯 **Active Dataset:** {active} — this data will be used across all analysis pages.")
        else:
            st.warning("⚠️ No active dataset selected. Click **Set as Active** on a file above.")

    else:
        st.markdown("---")
        st.markdown("### 🧪 Try Demo Data")
        col1, col2, col3 = st.columns(3)
        if col1.button("📊 Sales Demo",      use_container_width=True):
            _load_demo("sales")
        if col2.button("🏥 Healthcare Demo", use_container_width=True):
            _load_demo("health")
        if col3.button("📈 Finance Demo",    use_container_width=True):
            _load_demo("finance")

    st.markdown("---")
    st.markdown("### 🚀 Quick Start Guide")
    cols  = st.columns(5)
    steps = [
        ("1️⃣", "Upload",  "Upload a CSV or Excel file"),
        ("2️⃣", "Clean",   "Fix issues in Cleaning Studio"),
        ("3️⃣", "Search",  "Search and filter your data"),
        ("4️⃣", "Analyze", "Explore charts and statistics"),
        ("5️⃣", "Build",   "Create a Power BI-style dashboard"),
    ]
    for col, (num, title, desc) in zip(cols, steps):
        col.markdown(f"""
        <div class='metric-card' style='text-align:center;padding:12px'>
            <div style='font-size:24px'>{num}</div>
            <div style='font-weight:600;margin:4px 0'>{title}</div>
            <div style='font-size:12px;color:#888'>{desc}</div>
        </div>
        """, unsafe_allow_html=True)


def _load_demo(demo_type: str):
    import numpy as np
    rng = np.random.default_rng(42)

    if demo_type == "sales":
        months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"] * 3
        df = pd.DataFrame({
            "Month":   months,
            "Region":  rng.choice(["North","South","East","West"], size=36),
            "Product": rng.choice(["A","B","C","D"], size=36),
            "Sales":   rng.integers(10000, 100000, size=36),
            "Units":   rng.integers(50, 500, size=36),
            "Profit":  rng.integers(1000, 30000, size=36),
        })
        name = "sales_demo.csv"
    elif demo_type == "health":
        n = 200
        df = pd.DataFrame({
            "Patient_ID":    range(1, n + 1),
            "Age":           rng.integers(18, 90, size=n),
            "Gender":        rng.choice(["Male","Female"], size=n),
            "BMI":           rng.uniform(18.5, 40, size=n).round(1),
            "BloodPressure": rng.integers(70, 140, size=n),
            "Cholesterol":   rng.integers(150, 300, size=n),
            "Diabetes":      rng.choice(["Yes","No"], size=n),
        })
        name = "health_demo.csv"
    else:
        n = 150
        df = pd.DataFrame({
            "Date":       pd.date_range("2024-01-01", periods=n, freq="D").astype(str),
            "Stock":      rng.choice(["AAPL","GOOG","MSFT","AMZN"], size=n),
            "Open":       rng.uniform(100, 500, size=n).round(2),
            "Close":      rng.uniform(100, 500, size=n).round(2),
            "Volume":     rng.integers(100000, 5000000, size=n),
            "Change_Pct": rng.uniform(-5, 5, size=n).round(2),
        })
        name = "finance_demo.csv"

    if "uploaded_dfs" not in st.session_state:
        st.session_state["uploaded_dfs"] = {}
    st.session_state["uploaded_dfs"][name]  = df
    st.session_state["active_df_name"]      = name
    st.session_state["active_df"]           = df
    st.success(f"✅ Demo dataset '{name}' loaded successfully!")
    st.rerun()
