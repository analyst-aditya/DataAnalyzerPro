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
        ## 📊 Data Analyzer Pro 2.0

        **Enterprise-Grade Data Analysis Platform** — built with Python, Streamlit, and Plotly.

        ### ✨ Features
        - 🏠 **Multi-file Upload** — CSV and Excel support, multiple files simultaneously
        - 🛠️ **Data Cleaning Studio** — 15+ cleaning operations with undo support
        - 🔍 **Data Search** — Simple, regex, range, and multi-column filtering
        - 📈 **Dashboard Analysis** — Auto charts, statistics, and correlation analysis
        - 🎨 **Canvas Builder** — Power BI-style drag-and-drop dashboard creation
        - 🤖 **AI Insights** — Statistical analysis, outlier detection, and recommendations
        - 💼 **Dashboard Manager** — Save, load, and export dashboards as HTML
        - 🌙 **Dark / Light Theme** — Toggle from the sidebar
        - 🔐 **Secure Authentication** — bcrypt hashing, rate limiting, session timeout

        ### 📖 How to Use
        1. **Home** → Upload a CSV or Excel file
        2. **Cleaning Studio** → Detect and fix data quality issues
        3. **Data Search** → Search and filter your cleaned data
        4. **Analysis** → Explore charts and statistics
        5. **Canvas** → Build a custom dashboard
        6. **AI Insights** → Get automated recommendations

        ### 🛠️ Technology Stack
        - **Language:** Python 3.10+
        - **Framework:** Streamlit
        - **Charts:** Plotly
        - **Database:** SQLite3
        - **Security:** bcrypt (12 rounds)
        """)

    with col2:
        st.markdown("### 📋 Your Account")
        st.info(f"""
        **Username:** {user['username']}
        **Role:** {'Administrator 👑' if user.get('is_admin') else 'Standard User'}
        """)

        st.markdown("### 🔢 Your Stats")
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM saved_dashboards WHERE user_id=?", (user["id"],))
            n_dash = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM user_activity WHERE user_id=?", (user["id"],))
            n_act  = cur.fetchone()[0]

        st.metric("Saved Dashboards", n_dash)
        st.metric("Total Actions",    n_act)

    st.markdown("---")
    st.markdown("### 💬 Submit Feedback")
    st.markdown("Your feedback helps us improve the platform.")

    with st.form("feedback_form"):
        rating        = st.slider("Rating (1–5):", 1, 5, 5)
        stars         = "⭐" * rating
        st.markdown(f"Your rating: {stars}")
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
            "All data is stored locally on your machine in a SQLite database. "
            "No data is sent to any external server or cloud service."
        ),
        (
            "What is the maximum file size I can upload?",
            "The default limit is 200 MB per file. An administrator can change this in the Streamlit config file."
        ),
        (
            "How do I share a dashboard?",
            "Export any dashboard as an HTML file from the Canvas or My Dashboards page. "
            "The HTML file is self-contained and opens in any web browser."
        ),
        (
            "What do I do if I forget my password?",
            "Ask an administrator to reset your password from the Admin Panel."
        ),
        (
            "Can I recover data I accidentally deleted during cleaning?",
            "Yes — the Cleaning Studio supports up to 20 undo steps. "
            "You can also click 'Reset to Original Data' to restore the original uploaded file."
        ),
    ]
    for q, a in faqs:
        with st.expander(f"❓ {q}"):
            st.markdown(a)

    st.markdown("---")
    st.markdown("""
    <div style='text-align:center;color:#888;font-size:12px;padding:20px'>
        <strong>Data Analyzer Pro 2.0</strong> © 2026 — Developed by <strong>Aditya Kumar</strong><br>
        Built with Python, Streamlit &amp; Plotly
    </div>
    """, unsafe_allow_html=True)
