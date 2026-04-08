"""
pg_mydashboards.py - Saved Dashboards Management
"""
import streamlit as st
import pandas as pd
from modules.dashboard_utils import get_user_dashboards, load_dashboard, delete_dashboard, export_dashboard_html
from modules.chart_utils import make_chart
from modules.database import log_activity


def page_my_dashboards(user: dict):
    st.title("💼 My Dashboards")
    st.markdown("View, load, export, or delete your saved dashboards.")

    dashboards = get_user_dashboards(user["username"])

    if not dashboards:
        st.markdown("""
        <div style='text-align:center;padding:60px;border:2px dashed #ccc;border-radius:12px'>
            <div style='font-size:48px'>📊</div>
            <h3>No Saved Dashboards Yet</h3>
            <p style='color:#888'>Go to the Canvas page, build a dashboard, and save it.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🎨 Go to Canvas", type="primary"):
            st.session_state["page"] = "Canvas"
            st.rerun()
        return

    st.markdown(f"**{len(dashboards)}** saved dashboard(s) found.")
    st.markdown("---")

    df = st.session_state.get("active_df")
    if df is None:
        dfs = st.session_state.get("uploaded_dfs", {})
        if dfs:
            df = list(dfs.values())[0]

    for dash in dashboards:
        with st.expander(
            f"📊 **{dash['dashboard_name']}** — Last updated: {dash['updated_at'][:16]}",
            expanded=False,
        ):
            col_desc, col_meta = st.columns([3, 1])
            with col_desc:
                if dash.get("description"):
                    st.markdown(f"*{dash['description']}*")
                st.caption(f"Created: {dash['created_at'][:16]}")
            with col_meta:
                st.caption(f"ID: {dash['id']}")

            c1, c2, c3, c4 = st.columns(4)

            if c1.button("📂 Load to Canvas", key=f"load_{dash['id']}", use_container_width=True):
                result = load_dashboard(user["username"], dash["dashboard_name"])
                if result["success"]:
                    charts = result["charts"]
                    for viz in charts:
                        if viz.get("fig_json"):
                            try:
                                import plotly.io as pio
                                viz["fig"] = pio.from_json(viz["fig_json"])
                            except Exception:
                                pass
                        if not viz.get("fig") and df is not None:
                            viz["fig"] = make_chart(df, viz)
                    import copy
                    if "canvas_charts" not in st.session_state:
                        st.session_state["canvas_charts"] = []
                    if "canvas_undo" not in st.session_state:
                        st.session_state["canvas_undo"] = []
                    st.session_state["canvas_undo"].append(
                        copy.deepcopy(st.session_state["canvas_charts"])
                    )
                    st.session_state["canvas_charts"] = charts
                    st.session_state["page"]          = "Canvas"
                    log_activity(user["id"], "load_dashboard", dash["dashboard_name"])
                    st.success(f"✅ '{dash['dashboard_name']}' loaded to canvas.")
                    st.rerun()
                else:
                    st.error(result["message"])

            if c2.button("📤 Export HTML", key=f"html_{dash['id']}", use_container_width=True):
                result = load_dashboard(user["username"], dash["dashboard_name"])
                if result["success"]:
                    charts = result["charts"]
                    for viz in charts:
                        if viz.get("fig_json") and not viz.get("fig"):
                            try:
                                import plotly.io as pio
                                viz["fig"] = pio.from_json(viz["fig_json"])
                            except Exception:
                                pass
                    html = export_dashboard_html(charts, dash["dashboard_name"])
                    st.download_button("⬇️ Download HTML", html,
                                       file_name=f"{dash['dashboard_name']}.html",
                                       mime="text/html",
                                       key=f"dl_html_{dash['id']}",
                                       use_container_width=True)

            if c3.button("👁️ Preview Charts", key=f"prev_{dash['id']}", use_container_width=True):
                result = load_dashboard(user["username"], dash["dashboard_name"])
                if result["success"]:
                    charts = result["charts"]
                    st.markdown(f"**{len(charts)} chart(s):**")
                    icon_map = {"bar":"📊","line":"📈","area":"🏔️","scatter":"🔵",
                                "pie":"🥧","donut":"🍩","histogram":"📉","box":"📦",
                                "heatmap":"🗺️","kpi":"🎯","table":"📋"}
                    for viz in charts:
                        icon = icon_map.get(viz.get("type",""), "📊")
                        st.markdown(f"  {icon} {viz.get('title','Untitled')} ({viz.get('type','?')})")

            confirm_key = f"confirm_del_{dash['id']}"
            if not st.session_state.get(confirm_key, False):
                if c4.button("🗑️ Delete", key=f"del_btn_{dash['id']}", use_container_width=True):
                    st.session_state[confirm_key] = True
                    st.rerun()
            else:
                st.warning(f"⚠️ Are you sure you want to delete **{dash['dashboard_name']}**?")
                dc1, dc2 = st.columns(2)
                if dc1.button("✅ Yes, Delete", key=f"confirm_yes_{dash['id']}", use_container_width=True):
                    result = delete_dashboard(user["username"], dash["dashboard_name"])
                    st.session_state.pop(confirm_key, None)
                    if result["success"]:
                        log_activity(user["id"], "delete_dashboard", dash["dashboard_name"])
                        st.success(result["message"])
                        st.rerun()
                    else:
                        st.error(result["message"])
                if dc2.button("❌ Cancel", key=f"confirm_no_{dash['id']}", use_container_width=True):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()

    st.markdown("---")
    st.markdown("### 📦 Bulk Export")
    if st.button("📤 Export All Dashboards (Combined HTML)", use_container_width=True):
        all_charts = []
        for dash in dashboards:
            result = load_dashboard(user["username"], dash["dashboard_name"])
            if result["success"]:
                for viz in result["charts"]:
                    if viz.get("fig_json") and not viz.get("fig"):
                        try:
                            import plotly.io as pio
                            viz["fig"] = pio.from_json(viz["fig_json"])
                        except Exception:
                            pass
                    all_charts.append(viz)
        if all_charts:
            html = export_dashboard_html(all_charts, "All Dashboards")
            st.download_button("⬇️ Download Combined HTML", html,
                               file_name="all_dashboards.html",
                               mime="text/html",
                               use_container_width=True)
