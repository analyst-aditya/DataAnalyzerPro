"""
dashboard_utils.py - Dashboard persistence and export
"""
import json
import copy
import datetime
import numpy as np
import pandas as pd
import streamlit as st
from modules.database import get_db


def _json_safe(obj):
    """Recursively make object JSON-serializable."""
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    if isinstance(obj, (pd.Series, np.ndarray)):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(i) for i in obj]
    try:
        if pd.isna(obj):
            return None
    except Exception:
        pass
    return obj


def save_dashboard(username: str, dashboard_name: str, charts: list, description: str = "") -> dict:
    """Save canvas charts to database. Returns {success, message}."""
    if not charts:
        return {"success": False, "message": "Canvas pe koi chart nahi hai"}

    serialized = []
    for viz in charts:
        v = copy.deepcopy(viz)
        # Store Plotly figure as JSON string
        if v.get("fig") is not None:
            try:
                v["fig_json"] = v["fig"].to_json()
            except Exception:
                v["fig_json"] = None
        v.pop("fig", None)
        serialized.append(_json_safe(v))

    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username=?", (username,))
            row = cur.fetchone()
            if not row:
                return {"success": False, "message": "User not found"}
            user_id = row["id"]

            cur.execute(
                "SELECT id FROM saved_dashboards WHERE user_id=? AND dashboard_name=?",
                (user_id, dashboard_name),
            )
            existing = cur.fetchone()
            config_json = json.dumps(serialized, default=str)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if existing:
                conn.execute(
                    "UPDATE saved_dashboards SET dashboard_config=?, description=?, updated_at=? WHERE id=?",
                    (config_json, description, now, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO saved_dashboards (user_id,dashboard_name,dashboard_config,description) VALUES (?,?,?,?)",
                    (user_id, dashboard_name, config_json, description),
                )
        return {"success": True, "message": f"✅ Dashboard '{dashboard_name}' save ho gaya!"}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}


def load_dashboard(username: str, dashboard_name: str) -> dict:
    """Load charts from a saved dashboard. Returns {success, charts, message}."""
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username=?", (username,))
            row = cur.fetchone()
            if not row:
                return {"success": False, "charts": [], "message": "User not found"}
            user_id = row["id"]

            cur.execute(
                "SELECT dashboard_config FROM saved_dashboards WHERE user_id=? AND dashboard_name=?",
                (user_id, dashboard_name),
            )
            dash = cur.fetchone()
            if not dash:
                return {"success": False, "charts": [], "message": "Dashboard not found"}

        charts = json.loads(dash["dashboard_config"])
        return {"success": True, "charts": charts, "message": "Loaded!"}
    except Exception as e:
        return {"success": False, "charts": [], "message": f"Error: {e}"}


def get_user_dashboards(username: str) -> list:
    """Return list of dashboards for a user."""
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username=?", (username,))
            row = cur.fetchone()
            if not row:
                return []
            user_id = row["id"]
            cur.execute(
                "SELECT id,dashboard_name,description,created_at,updated_at "
                "FROM saved_dashboards WHERE user_id=? ORDER BY updated_at DESC",
                (user_id,),
            )
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return []


def delete_dashboard(username: str, dashboard_name: str) -> dict:
    """Delete a saved dashboard."""
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username=?", (username,))
            row = cur.fetchone()
            if not row:
                return {"success": False, "message": "User not found"}
            conn.execute(
                "DELETE FROM saved_dashboards WHERE user_id=? AND dashboard_name=?",
                (row["id"], dashboard_name),
            )
        return {"success": True, "message": f"'{dashboard_name}' delete ho gaya"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def export_dashboard_html(charts: list, dashboard_name: str) -> str:
    """Export dashboard as a self-contained HTML string with embedded Plotly charts."""
    chart_htmls = []
    for viz in charts:
        fig = viz.get("fig")
        if fig is None and viz.get("fig_json"):
            import plotly.io as pio
            import json as _json
            fig = pio.from_json(viz["fig_json"])
        if fig:
            chart_htmls.append(
                f'<div class="chart-wrapper"><h3>{viz.get("title","Chart")}</h3>'
                + fig.to_html(full_html=False, include_plotlyjs="cdn")
                + "</div>"
            )

    style = """
    <style>
    body{font-family:sans-serif;background:#f0f2f6;padding:20px}
    h1{text-align:center;color:#1f77b4}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(500px,1fr));gap:20px;margin-top:20px}
    .chart-wrapper{background:white;border-radius:10px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,0.1)}
    .chart-wrapper h3{margin:0 0 10px;color:#333;font-size:14px}
    </style>
    """
    charts_grid = "\n".join(chart_htmls)
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
    <title>{dashboard_name}</title>{style}</head>
    <body><h1>📊 {dashboard_name}</h1><div class="grid">{charts_grid}</div></body></html>"""
