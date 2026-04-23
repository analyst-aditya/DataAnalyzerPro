"""
app.py - Data Analysis App 2.0 — Main Entry Point
Author: Aditya Kumar
Run: streamlit run app.py
"""
import os
import warnings
import streamlit as st

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Data Analysis App",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Data Analysis App 2.0 — by Aditya Kumar"},
)

from modules.database import init_database
from modules.auth import current_user, logout_user, refresh_session
from modules.theme_utils import apply_theme, theme_toggle_widget
from modules.i18n import t

from pages.pg_login import show_login, show_signup, show_forgot_password, show_admin_login
from pages.pg_home import page_home
from pages.pg_cleaning import page_cleaning
from pages.pg_analysis import page_analysis
from pages.pg_canvas import page_canvas
from pages.pg_mydashboards import page_my_dashboards
from pages.pg_search import page_search
from pages.pg_insights import page_insights
from pages.pg_about import page_about
from pages.pg_admin import page_admin

os.makedirs("data", exist_ok=True)
init_database()


def main():
    # Init defaults
    for k, v in [
        ("mode", "login"), ("app_theme", "light"),
        ("page", "Home"), ("uploaded_dfs", {}),
    ]:
        if k not in st.session_state:
            st.session_state[k] = v

    apply_theme()

    user = current_user()

    # ── Pre-auth pages ─────────────────────────────────────────────────────────
    if not user:
        mode = st.session_state.get("mode", "login")
        if mode == "signup":
            show_signup()
        elif mode == "forgot":
            show_forgot_password()
        elif mode == "admin_login":
            show_admin_login()
        else:
            show_login()
        return

    refresh_session()

    # ── Sidebar navigation ─────────────────────────────────────────────────────
    with st.sidebar:
        is_dark   = st.session_state.get("app_theme") == "dark"
        badge_bg  = "#334155" if is_dark else "#f1f5f9"
        admin_badge = " 👑" if user.get("is_admin") else ""
        st.markdown(f"""
        <div style='background:{badge_bg};border-radius:10px;
             padding:12px;text-align:center;margin-bottom:8px'>
            <div style='font-size:26px'>👤</div>
            <div style='font-weight:600;font-size:14px'>{user['username']}{admin_badge}</div>
        </div>
        """, unsafe_allow_html=True)

        adn = st.session_state.get("active_df_name")
        if adn:
            adf   = st.session_state.get("active_df")
            rows  = f"{len(adf):,}" if adf is not None else "?"
            short = adn[:22] + "…" if len(adn) > 22 else adn
            st.markdown(f"""
            <div style='background:#1d4ed8;color:#fff;border-radius:8px;
                 padding:6px 10px;font-size:11px;margin-bottom:8px;text-align:center'>
                📁 {short}<br><span style='opacity:.8'>{rows} rows</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        pages = [
            (t("nav_home"),       "Home"),
            (t("nav_cleaning"),   "Cleaning"),
            (t("nav_search"),     "Search"),
            (t("nav_analysis"),   "Analysis"),
            (t("nav_canvas"),     "Canvas"),
            (t("nav_dashboards"), "My Dashboards"),
            (t("nav_insights"),   "AI Insights"),
            (t("nav_about"),      "About"),
        ]
        if user.get("is_admin"):
            pages.append((t("nav_admin"), "Admin"))

        for label, key in pages:
            is_active = st.session_state["page"] == key
            btype = "primary" if is_active else "secondary"
            if st.button(label, use_container_width=True, type=btype, key=f"nav_{key}"):
                st.session_state["page"] = key
                st.rerun()

        st.markdown("---")
        theme_toggle_widget()
        st.markdown("---")

        if st.button(t("nav_logout"), use_container_width=True, key="logout_main"):
            logout_user()
            st.session_state["mode"] = "login"
            st.rerun()

        st.markdown("""
        <div style='font-size:10px;opacity:.5;text-align:center;margin-top:12px'>
            Data Analysis App v2.0<br>by Aditya Kumar
        </div>
        """, unsafe_allow_html=True)

    # ── Page routing ───────────────────────────────────────────────────────────
    page = st.session_state.get("page", "Home")
    routes = {
        "Home":          lambda: page_home(user),
        "Search":        lambda: page_search(user),
        "Cleaning":      lambda: page_cleaning(user),
        "Analysis":      lambda: page_analysis(user),
        "Canvas":        lambda: page_canvas(user),
        "My Dashboards": lambda: page_my_dashboards(user),
        "AI Insights":   lambda: page_insights(user),
        "About":         lambda: page_about(user),
        "Admin":         lambda: page_admin(user),
    }
    fn = routes.get(page)
    if fn:
        fn()
    else:
        st.session_state["page"] = "Home"
        st.rerun()


if __name__ == "__main__":
    main()
