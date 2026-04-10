"""
pg_about.py - About & Feedback page
"""
import streamlit as st
from modules.database import get_db, log_activity


def page_about(user: dict):
    st.title("ℹ️ About & Feedback")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
## 📊 Data Analyzer Pro v3
**Enterprise-Grade Data Analysis Platform** — built with Python, Streamlit & Plotly.

---
### ✨ Core Features

#### 🏠 Home — Data Upload
- Upload **CSV and Excel** files (up to 200 MB each)
- Load multiple files simultaneously and switch between them
- Built-in **Demo datasets** (Sales, Healthcare, Finance)
- Dataset preview with memory, missing value, and shape stats

#### 🛠️ Data Cleaning Studio
- **Problem Scanner** — auto-detects empty rows, duplicates, missing values, outliers, invalid emails
- **Auto Clean** — one-click cleaning with selectable operations
- **Manual Clean** — 6 categories:
  - Handle Missing Values (mean / median / zero / forward / backward / custom fill, drop)
  - Row Operations (remove empty, duplicates, negatives, outliers)
  - Text Operations (trim, title case, lowercase, uppercase)
  - Numeric Operations (remove outliers, negatives)
  - Type Conversion (to numeric, to datetime)
  - **Column Operations** — permanently remove unwanted columns
- **Batch Operations** — queue and run multiple operations at once
- **Removed Data tab** — view and download all rows/columns removed during cleaning
- **Undo** — up to 20 undo steps, plus full Reset to Original

#### 🔍 Data Search
- Simple text, regex, value-range, and multi-column filtering with instant results

#### 📈 Dashboard Analysis
- Auto-generated bar/histogram charts for all numeric columns
- Distribution analysis (histogram + box plot) with descriptive stats
- Correlation heatmap and scatter matrix
- Cross-analysis with 5 chart types and custom aggregations

#### 🎨 Canvas Builder (Power BI-style)
- **15 chart types:** Bar, Line, Area, Scatter, Pie, Donut, Histogram, Box, Heatmap, Funnel, Violin, Bubble, Table, KPI Card, Metric Card
- **Smart field editor** — each chart shows only the axes it needs (KPI → Value + Trend; Pie/Donut → Legend + Values; Box → Y-axis + Group By; Heatmap/Table → no axes)
- **📌 Data Labels** toggle — show values directly on charts without hovering
- **KPI Card** with large value display + optional sparkline trend line
- **Metric Card** with primary + secondary metric display
- Per-chart theme, width, height, and Top-N filters
- Drag-and-drop reorder, duplicate, undo (30 steps), global theme
- Save/load dashboards, export as standalone HTML or JSON

#### 🤖 AI Insights
- Dataset summary, type breakdown, missing value visualisation
- Outlier analysis (IQR method), normality tests (Shapiro-Wilk), T-tests
- Correlation strength analysis and automated recommendations

#### 💼 My Dashboards
- View, load, rename, delete saved dashboards; export to self-contained HTML

#### 🌙 Dark / Light Theme
- Full coverage: inputs, dropdowns, file uploaders, tables, charts, modals, dialogs

#### 🔐 Security
- bcrypt password hashing (12 rounds), session timeout, rate-limited login
- Admin panel with user management and activity log
        """)

    with col2:
        st.markdown("### 📋 Your Account")
        is_dark  = st.session_state.get("app_theme") == "dark"
        card_bg  = "#1e293b" if is_dark else "#f8fafc"
        card_bdr = "#334155" if is_dark else "#e2e8f0"
        txt_col  = "#e2e8f0" if is_dark else "#1e293b"
        st.markdown(
            f"<div style='background:{card_bg};border:1px solid {card_bdr};border-radius:10px;"
            f"padding:14px;margin-bottom:12px;color:{txt_col}'>"
            f"<div style='font-size:13px'>👤 <b>{user['username']}</b>"
            f"{'&nbsp; 👑 Administrator' if user.get('is_admin') else ''}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.markdown("### 📊 Your Stats")
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM saved_dashboards WHERE user_id=?", (user["id"],))
            n_dash = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM user_activity WHERE user_id=?", (user["id"],))
            n_act  = cur.fetchone()[0]

        st.metric("Saved Dashboards", n_dash)
        st.metric("Total Actions",    n_act)

        adn = st.session_state.get("active_df_name")
        if adn:
            adf  = st.session_state.get("active_df")
            rows = f"{len(adf):,}" if adf is not None else "?"
            cols_ = len(adf.columns) if adf is not None else "?"
            st.markdown("### 📁 Active Dataset")
            st.info(f"**{adn}**\n\n{rows} rows × {cols_} columns")

        st.markdown("### 🔖 Release")
        st.markdown(
            f"<div style='background:{card_bg};border:1px solid {card_bdr};border-radius:10px;"
            f"padding:12px;color:{txt_col};font-size:12px;line-height:1.7'>"
            f"<b>Data Analyzer Pro v3</b><br>"
            f"Streamlit · Plotly · pandas<br>"
            f"15 chart types · 6 cleaning categories<br>"
            f"Dark &amp; light themes · bcrypt auth"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.markdown("### 🛠️ Stack")
        stack = [
            ("Language",   "Python 3.10+"),
            ("UI",         "Streamlit"),
            ("Charts",     "Plotly"),
            ("Data",       "pandas · NumPy"),
            ("Stats",      "SciPy"),
            ("Database",   "SQLite3"),
            ("Security",   "bcrypt"),
            ("Export",     "openpyxl · kaleido"),
        ]
        for label, val in stack:
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;font-size:12px;"
                f"color:{txt_col};padding:2px 0;border-bottom:1px solid {card_bdr}'>"
                f"<span style='color:#94a3b8'>{label}</span><span>{val}</span></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("### 💬 Submit Feedback")
    st.markdown("Your feedback helps improve the platform.")

    with st.form("feedback_form"):
        rating        = st.slider("Rating (1–5):", 1, 5, 5)
        st.markdown(f"Your rating: {'⭐' * rating}")
        feedback_text = st.text_area(
            "Feedback / Suggestions / Bug Reports:",
            placeholder="How is the app? What could be improved? Did you find a bug?",
            height=120,
        )
        submitted = st.form_submit_button("📤 Submit Feedback", type="primary", use_container_width=True)

    if submitted:
        if not feedback_text.strip():
            st.error("Feedback cannot be empty.")
        else:
            try:
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO feedback (user_id, username, feedback, rating) VALUES (?,?,?,?)",
                        (user["id"], user["username"], feedback_text.strip(), rating),
                    )
                log_activity(user["id"], "feedback", f"rating={rating}")
                st.success("✅ Thank you — your feedback has been submitted!")
                st.balloons()
            except Exception as e:
                st.error(f"Error submitting feedback: {e}")

    st.markdown("---")
    st.markdown("### ❓ Frequently Asked Questions")
    faqs = [
        (
            "Where is my data stored?",
            "All data is stored **locally** on your machine in a SQLite database (`data/app.db`). "
            "Nothing is sent to any external server or cloud service."
        ),
        (
            "What file types can I upload?",
            "CSV (.csv) and Excel (.xlsx / .xls) up to 200 MB each. Multiple files can be loaded simultaneously."
        ),
        (
            "How do I remove unwanted columns from my dataset?",
            "Go to **Cleaning Studio → Manual Clean → Column Operations**. "
            "Select the columns to remove and click 'Remove Selected Columns'. "
            "You can undo at any time using the Undo button."
        ),
        (
            "Where can I see data that was removed during cleaning?",
            "The **🗑️ Removed Data** tab in Cleaning Studio shows all rows removed during "
            "operations (duplicates, empties, outliers, etc.), plus any dropped columns. "
            "You can download the removed rows as a CSV."
        ),
        (
            "How do I show data labels on charts permanently?",
            "When adding or editing a chart in the Canvas Builder, tick the "
            "**📌 Show Data Labels** checkbox before saving."
        ),
        (
            "What is the difference between KPI Card and Metric Card?",
            "**KPI Card** shows a large aggregate (sum) with average and an optional sparkline trend line "
            "from a second numeric column. **Metric Card** shows the same primary value with a secondary "
            "metric summary — ideal for placing side-by-side comparisons on a dashboard."
        ),
        (
            "How do I share a dashboard?",
            "Export any dashboard as a self-contained **HTML file** from the Canvas or My Dashboards page. "
            "It opens in any browser without needing Python or Streamlit."
        ),
        (
            "Can I recover accidentally removed data?",
            "Yes — the Cleaning Studio has **up to 20 undo steps**. "
            "You can also click **Reset to Original Data** to restore everything. "
            "Removed rows are also visible in the Removed Data tab."
        ),
        (
            "What do I do if I forget my password?",
            "Ask an administrator to reset your password from the **Admin Panel**."
        ),
    ]
    for q, a in faqs:
        with st.expander(f"❓ {q}"):
            st.markdown(a)

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;color:#888;font-size:12px;padding:20px'>"
        "<strong>Data Analyzer Pro v2</strong> © 2026 — Developed by <strong>Aditya Kumar</strong><br>"
        "Built with Python · Streamlit · Plotly · pandas · SQLite"
        "</div>",
        unsafe_allow_html=True,
    )
