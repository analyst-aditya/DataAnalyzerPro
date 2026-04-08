"""
pg_canvas.py - Power BI Style Dashboard Canvas
"""
import copy, json, io
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
from modules.chart_utils import make_chart, CHART_TYPES, CHART_THEMES
from modules.dashboard_utils import (
    save_dashboard, load_dashboard, get_user_dashboards, export_dashboard_html
)
from modules.database import log_activity


def _init():
    defaults = {
        "canvas_charts": [], "canvas_undo": [],
        "canvas_editing": None, "canvas_theme": "Default", "canvas_cols": 2,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _push_undo():
    h = st.session_state["canvas_undo"]
    h.append(copy.deepcopy(st.session_state["canvas_charts"]))
    if len(h) > 30:
        h.pop(0)


def _get_df():
    df = st.session_state.get("active_df")
    if df is not None and len(df) > 0:
        return df
    dfs = st.session_state.get("uploaded_dfs", {})
    return list(dfs.values())[0] if dfs else None


def _drag_drop_reorder(chart_titles: list):
    if not chart_titles:
        return
    items_html = "".join(
        f'<li class="drag-item" data-idx="{i}" draggable="true">'
        f'<span class="drag-handle">⠿</span>'
        f'<span class="drag-label">{title[:45]}</span></li>'
        for i, title in enumerate(chart_titles)
    )
    theme    = st.session_state.get("app_theme", "light")
    bg       = "#1e293b" if theme == "dark" else "#ffffff"
    text     = "#e2e8f0" if theme == "dark" else "#1e293b"
    item_bg  = "#334155" if theme == "dark" else "#f1f5f9"
    item_bdr = "#475569" if theme == "dark" else "#e2e8f0"

    html = f"""
<style>
  body{{margin:0;font-family:sans-serif;background:{bg};color:{text};}}
  ul#sortable{{list-style:none;padding:0;margin:0;}}
  li.drag-item{{display:flex;align-items:center;gap:10px;background:{item_bg};
    border:1px solid {item_bdr};border-radius:8px;padding:8px 12px;margin:4px 0;
    cursor:grab;user-select:none;font-size:13px;color:{text};}}
  li.drag-item:active{{cursor:grabbing;}}
  li.drag-item.drag-over{{background:#3b82f6;border-color:#2563eb;color:#fff;}}
  .drag-handle{{font-size:16px;color:#94a3b8;}}
  #status{{font-size:11px;color:#94a3b8;margin-top:6px;}}
  button#apply-btn{{margin-top:8px;padding:6px 16px;background:#3b82f6;
    color:white;border:none;border-radius:6px;cursor:pointer;font-size:13px;}}
  button#apply-btn:hover{{background:#2563eb;}}
</style>
<ul id="sortable">{items_html}</ul>
<div id="status">Drag charts to reorder them</div>
<button id="apply-btn" onclick="applyOrder()">✅ Apply New Order</button>
<script>
  let dragged=null;
  const list=document.getElementById('sortable');
  list.addEventListener('dragstart',e=>{{dragged=e.target.closest('li');dragged.style.opacity='0.5';}});
  list.addEventListener('dragend',e=>{{e.target.style.opacity='1';
    document.querySelectorAll('li').forEach(li=>li.classList.remove('drag-over'));}});
  list.addEventListener('dragover',e=>{{e.preventDefault();
    const t=e.target.closest('li');
    if(t&&t!==dragged){{document.querySelectorAll('li').forEach(li=>li.classList.remove('drag-over'));
      t.classList.add('drag-over');
      const r=t.getBoundingClientRect();
      if(e.clientY>r.top+r.height/2) list.insertBefore(dragged,t.nextSibling);
      else list.insertBefore(dragged,t);}}}});
  list.addEventListener('dragleave',e=>{{const t=e.target.closest('li');if(t)t.classList.remove('drag-over');}});
  function applyOrder(){{
    const order=Array.from(list.querySelectorAll('li')).map(li=>parseInt(li.getAttribute('data-idx')));
    const url=new URL(window.location.href);
    url.searchParams.set('canvas_order',order.join(','));
    window.parent.location.href=url.toString();
  }}
</script>"""
    components.html(html, height=min(60 + len(chart_titles) * 48, 500), scrolling=True)


def _chart_editor(df: pd.DataFrame, edit_idx):
    cols     = list(df.columns)
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    existing = None
    if edit_idx is not None and edit_idx != -1:
        charts = st.session_state["canvas_charts"]
        if 0 <= edit_idx < len(charts):
            existing = charts[edit_idx]
    cfg = existing or {}

    with st.sidebar:
        st.markdown(f"### {'✏️ Edit Chart' if existing else '➕ Add New Chart'}")

        type_map    = {ct["id"]: f"{ct['icon']} {ct['label']}" for ct in CHART_TYPES}
        default_t   = cfg.get("type", "bar")
        chart_type  = st.selectbox("Chart Type", list(type_map.keys()),
                                    format_func=lambda x: type_map[x],
                                    index=list(type_map.keys()).index(default_t) if default_t in type_map else 0,
                                    key="ce_type")

        title = st.text_input("Chart Title",
                               value=cfg.get("title", type_map[chart_type].split(" ", 1)[1]),
                               key="ce_title")

        xcol = st.selectbox("X-Axis / Category", [""] + cols,
                             index=(cols.index(cfg.get("xcol","")) + 1) if cfg.get("xcol") in cols else 0,
                             key="ce_xcol")
        ycol = st.selectbox("Y-Axis / Value", [""] + num_cols,
                             index=(num_cols.index(cfg.get("ycol","")) + 1) if cfg.get("ycol") in num_cols else 0,
                             key="ce_ycol")
        color_col = st.selectbox("Color By (optional)", [""] + cols,
                                  index=(cols.index(cfg.get("color_col","")) + 1) if cfg.get("color_col") in cols else 0,
                                  key="ce_color")
        size_col = None
        if chart_type in ("scatter","bubble"):
            size_col = st.selectbox("Size By (optional)", [""] + num_cols,
                                    index=(num_cols.index(cfg.get("size_col","")) + 1) if cfg.get("size_col") in num_cols else 0,
                                    key="ce_size")

        agg_func = st.selectbox("Aggregation", ["sum","mean","count","min","max","median"],
                                 index=["sum","mean","count","min","max","median"].index(cfg.get("agg_func","sum")),
                                 key="ce_agg")
        chart_theme = st.selectbox("Chart Theme", list(CHART_THEMES.keys()),
                                    index=list(CHART_THEMES.keys()).index(
                                        cfg.get("theme", st.session_state["canvas_theme"])),
                                    key="ce_theme")

        st.markdown("#### 📐 Chart Size")
        span_opts  = {"Full Width": 1, "Half Width": 2, "One-Third": 3}
        curr_span  = cfg.get("span", 1)
        span_label = st.selectbox("Width", list(span_opts.keys()),
                                   index=list(span_opts.values()).index(curr_span) if curr_span in span_opts.values() else 0,
                                   key="ce_span")
        span = span_opts[span_label]

        h_opts   = {280: "Small (280px)", 380: "Medium (380px)", 480: "Large (480px)", 580: "X-Large (580px)"}
        curr_h   = cfg.get("height", 380)
        h_label  = st.selectbox("Height", list(h_opts.values()),
                                 index=list(h_opts.keys()).index(curr_h) if curr_h in h_opts else 1,
                                 key="ce_height")
        height   = list(h_opts.keys())[list(h_opts.values()).index(h_label)]

        top_n = st.number_input("Top N results (0 = all)", 0, 100,
                                 value=int(cfg.get("top_n", 0)), step=5, key="ce_topn")

        if st.button("✅ Save Chart", type="primary", use_container_width=True, key="ce_save"):
            new_cfg = {
                "type": chart_type, "title": title, "xcol": xcol, "ycol": ycol,
                "color_col": color_col or None, "size_col": size_col or None,
                "agg_func": agg_func, "theme": chart_theme,
                "span": span, "height": height, "top_n": top_n,
            }
            new_cfg["fig"] = make_chart(df, new_cfg)
            _push_undo()
            if edit_idx is not None and edit_idx != -1:
                st.session_state["canvas_charts"][edit_idx] = new_cfg
            else:
                st.session_state["canvas_charts"].append(new_cfg)
            st.session_state["canvas_editing"] = None
            st.rerun()

        if st.button("Cancel", use_container_width=True, key="ce_cancel"):
            st.session_state["canvas_editing"] = None
            st.rerun()


def page_canvas(user: dict):
    _init()
    df = _get_df()

    order_param = st.query_params.get("canvas_order", "")
    if order_param:
        try:
            new_order = [int(x) for x in order_param.split(",")]
            charts    = st.session_state["canvas_charts"]
            if sorted(new_order) == list(range(len(charts))):
                _push_undo()
                st.session_state["canvas_charts"] = [charts[i] for i in new_order]
        except Exception:
            pass
        st.query_params.clear()
        st.rerun()

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🎨 Canvas Controls")

        if st.button("➕ Add Chart", type="primary", use_container_width=True, key="sidebar_add"):
            if df is None:
                st.error("Please upload data from the Home page first.")
            else:
                st.session_state["canvas_editing"] = -1
                st.rerun()

        st.markdown("**Global Theme:**")
        gt = st.selectbox("Global Theme", list(CHART_THEMES.keys()),
                           index=list(CHART_THEMES.keys()).index(st.session_state["canvas_theme"]),
                           label_visibility="collapsed", key="sb_global_theme")
        if gt != st.session_state["canvas_theme"]:
            st.session_state["canvas_theme"] = gt
            for viz in st.session_state["canvas_charts"]:
                viz["theme"] = gt
                if df is not None:
                    viz["fig"] = make_chart(df, viz)
            st.rerun()

        ncols_opts = {"1 Column": 1, "2 Columns": 2, "3 Columns": 3}
        nc_label   = st.selectbox("Grid Layout", list(ncols_opts.keys()),
                                   index=list(ncols_opts.values()).index(
                                       st.session_state.get("canvas_cols", 2)),
                                   key="sb_ncols")
        st.session_state["canvas_cols"] = ncols_opts[nc_label]

        st.markdown("---")
        col_u, col_c = st.columns(2)
        if col_u.button("↩️ Undo", use_container_width=True,
                        disabled=not st.session_state["canvas_undo"], key="sb_undo"):
            st.session_state["canvas_charts"] = st.session_state["canvas_undo"].pop()
            st.rerun()
        if col_c.button("🗑️ Clear All", use_container_width=True, key="sb_clear"):
            _push_undo()
            st.session_state["canvas_charts"] = []
            st.rerun()

        charts = st.session_state["canvas_charts"]
        if len(charts) > 1:
            st.markdown("---")
            st.markdown("**🔀 Drag & Drop to Reorder:**")
            _drag_drop_reorder([v.get("title", f"Chart {i+1}") for i, v in enumerate(charts)])

    editing = st.session_state.get("canvas_editing")
    if editing is not None:
        if df is None:
            st.warning("Please upload data from the Home page first.")
            st.session_state["canvas_editing"] = None
        else:
            _chart_editor(df, editing)
            st.info("👈 Configure the chart in the sidebar and click Save.")

    st.title("🎨 Dashboard Canvas")
    if df is None:
        st.warning("⚠️ Please upload data from the Home page first.")
        return
    st.caption(f"📁 {st.session_state.get('active_df_name','—')} — {len(df):,} rows × {len(df.columns)} columns")

    # Toolbar
    st.markdown('<div class="canvas-toolbar">', unsafe_allow_html=True)
    tc1, tc2, tc3, tc4, tc5, tc6 = st.columns([1.5, 2, 1, 1.5, 1, 1])

    with tc1:
        if st.button("➕ Add Chart", type="primary", use_container_width=True, key="tb_add"):
            st.session_state["canvas_editing"] = -1
            st.rerun()

    with tc2:
        save_name = st.text_input("save_name_inp", value="My Dashboard",
                                   label_visibility="collapsed",
                                   placeholder="Dashboard name...", key="tb_savename")
    with tc3:
        if st.button("💾 Save", use_container_width=True, key="tb_save"):
            res = save_dashboard(user["username"], save_name, st.session_state["canvas_charts"])
            if res["success"]:
                st.success(res["message"])
                log_activity(user["id"], "save_dashboard", save_name)
            else:
                st.error(res["message"])

    with tc4:
        dashboards = get_user_dashboards(user["username"])
        if dashboards:
            dn     = [d["dashboard_name"] for d in dashboards]
            ld_sel = st.selectbox("Load dashboard", dn, label_visibility="collapsed", key="tb_loadsel")
            if st.button("📂 Load", use_container_width=True, key="tb_load"):
                res = load_dashboard(user["username"], ld_sel)
                if res["success"]:
                    loaded = res["charts"]
                    for viz in loaded:
                        if viz.get("fig_json") and not viz.get("fig"):
                            try:
                                import plotly.io as pio
                                viz["fig"] = pio.from_json(viz["fig_json"])
                            except Exception:
                                pass
                        if not viz.get("fig") and df is not None:
                            viz["fig"] = make_chart(df, viz)
                    _push_undo()
                    st.session_state["canvas_charts"] = loaded
                    st.rerun()
                else:
                    st.error(res["message"])

    with tc5:
        exp_fmt = st.selectbox("Export format", ["HTML","JSON"],
                                label_visibility="collapsed", key="tb_expfmt")
    with tc6:
        if st.button("📤 Export", use_container_width=True, key="tb_export"):
            ch = st.session_state["canvas_charts"]
            if not ch:
                st.warning("The canvas is empty.")
            elif exp_fmt == "HTML":
                html = export_dashboard_html(ch, save_name)
                st.download_button("⬇️ Download HTML", html,
                                   file_name=f"{save_name}.html", mime="text/html")
            else:
                safe = [{k: v for k, v in c.items() if k not in ("fig","fig_json")} for c in ch]
                st.download_button("⬇️ Download JSON", json.dumps(safe, indent=2),
                                   file_name=f"{save_name}.json", mime="application/json")

    st.markdown('</div>', unsafe_allow_html=True)

    charts = st.session_state["canvas_charts"]
    if not charts:
        st.markdown("""
        <div style='text-align:center;padding:80px;border:2px dashed #475569;
             border-radius:16px;margin-top:20px'>
            <div style='font-size:52px'>📊</div>
            <h3>Canvas is Empty</h3>
            <p style='opacity:.7'>Click "+ Add Chart" above or use the sidebar to add your first chart.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    ncols = st.session_state.get("canvas_cols", 2)
    i = 0
    while i < len(charts):
        row_items, space, j = [], ncols, i
        while j < len(charts) and space > 0:
            span = min(charts[j].get("span", 1), space, ncols)
            row_items.append((j, charts[j], span))
            space -= span
            j += 1
        st_cols = st.columns([s for (_, _, s) in row_items])
        for col_obj, (cidx, viz, span) in zip(st_cols, row_items):
            _render_card(col_obj, cidx, viz, df, user)
        i = j

    st.markdown("---")
    st.caption(f"📊 {len(charts)} chart(s) | 🎨 {st.session_state['canvas_theme']} | "
               f"Grid: {ncols} column(s) | Undo history: {len(st.session_state['canvas_undo'])} step(s)")


def _render_card(container, idx, viz, df, user):
    with container:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)

        h1, h2, h3, h4, h5, h6, h7 = st.columns([4, 1, 1, 1, 1, 1, 1])
        h1.markdown(f"<div class='chart-title'>{viz.get('title','Chart')}</div>", unsafe_allow_html=True)

        if h2.button("▲", key=f"up_{idx}", help="Move up"):
            if idx > 0:
                _push_undo()
                ch = st.session_state["canvas_charts"]
                ch[idx], ch[idx-1] = ch[idx-1], ch[idx]
                st.rerun()
        if h3.button("▼", key=f"dn_{idx}", help="Move down"):
            ch = st.session_state["canvas_charts"]
            if idx < len(ch) - 1:
                _push_undo()
                ch[idx], ch[idx+1] = ch[idx+1], ch[idx]
                st.rerun()
        if h4.button("✏️", key=f"ed_{idx}", help="Edit chart"):
            st.session_state["canvas_editing"] = idx
            st.rerun()
        if h5.button("📋", key=f"cp_{idx}", help="Duplicate"):
            _push_undo()
            nv = copy.deepcopy(viz)
            nv["title"] = viz.get("title","Chart") + " (copy)"
            st.session_state["canvas_charts"].insert(idx+1, nv)
            st.rerun()
        if h6.button("🔄", key=f"rf_{idx}", help="Refresh chart"):
            if df is not None:
                viz["fig"] = make_chart(df, viz)
            st.rerun()
        if h7.button("🗑️", key=f"dl_{idx}", help="Delete chart"):
            _push_undo()
            st.session_state["canvas_charts"].pop(idx)
            st.rerun()

        with st.expander("⚙️ Resize", expanded=False):
            rc1, rc2 = st.columns(2)
            span_opts  = {"Full": 1, "Half": 2, "1/3": 3}
            curr_span  = viz.get("span", 1)
            new_span_label = rc1.selectbox("Width", list(span_opts.keys()),
                index=list(span_opts.values()).index(curr_span) if curr_span in span_opts.values() else 0,
                key=f"rspan_{idx}")
            new_span = span_opts[new_span_label]

            h_opts = {280: "Small", 380: "Medium", 480: "Large", 580: "X-Large"}
            curr_h = viz.get("height", 380)
            new_h  = rc2.select_slider("Height", options=list(h_opts.keys()),
                value=curr_h if curr_h in h_opts else 380,
                format_func=lambda x: h_opts[x], key=f"rheight_{idx}")

            if (new_span != curr_span or new_h != curr_h):
                if st.button("✅ Apply Size", key=f"rsz_{idx}", type="primary"):
                    _push_undo()
                    st.session_state["canvas_charts"][idx]["span"]   = new_span
                    st.session_state["canvas_charts"][idx]["height"] = new_h
                    st.rerun()

        fig = viz.get("fig")
        if fig is None and viz.get("fig_json"):
            try:
                import plotly.io as pio
                fig = pio.from_json(viz["fig_json"])
                viz["fig"] = fig
            except Exception:
                pass
        if fig is None and df is not None:
            fig = make_chart(df, viz)
            viz["fig"] = fig

        height = viz.get("height", 380)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True,
                            key=f"fig_{idx}_{viz.get('type','x')}",
                            config={"displayModeBar": True, "displaylogo": False,
                                    "modeBarButtonsToRemove": ["pan2d","lasso2d","select2d"]})
        else:
            st.markdown(f"""
            <div style='text-align:center;padding:40px;opacity:.6;
                 border:1px dashed #475569;border-radius:8px;height:{height}px;
                 display:flex;align-items:center;justify-content:center;flex-direction:column'>
                ⚠️ Chart could not be rendered.<br>
                <small>Click Edit and set the required columns.</small>
            </div>
            """, unsafe_allow_html=True)

        if viz.get("ycol") and viz["ycol"] in df.columns and pd.api.types.is_numeric_dtype(df[viz["ycol"]]):
            col_data = df[viz["ycol"]].dropna()
            if len(col_data) > 0:
                s1, s2, s3, s4 = st.columns(4)
                s1.caption(f"Sum: **{col_data.sum():,.0f}**")
                s2.caption(f"Avg: **{col_data.mean():,.2f}**")
                s3.caption(f"Max: **{col_data.max():,.0f}**")
                s4.caption(f"Min: **{col_data.min():,.0f}**")

        st.markdown('</div>', unsafe_allow_html=True)
