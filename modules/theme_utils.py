"""
theme_utils.py - Dark/Light theme with full visibility fix
"""
import streamlit as st

LIGHT_CSS = """
<style>
.stApp { background: #f4f6f9 !important; }
.main .block-container { max-width: 1400px; padding-top: 1rem; }
section[data-testid="stSidebar"] > div { background: #ffffff !important; border-right: 1px solid #e2e8f0; }
section[data-testid="stSidebar"] * { color: #1e293b !important; }
section[data-testid="stSidebar"] .stButton > button { background: #f1f5f9 !important; color: #1e293b !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important; font-size: 13px !important; }
section[data-testid="stSidebar"] .stButton > button[kind="primary"] { background: #3b82f6 !important; color: #ffffff !important; border: none !important; }
.stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, div[data-testid="stMarkdownContainer"] * { color: #1e293b !important; }
div[data-testid="stMetric"] { background: #ffffff; border-radius: 10px; padding: 14px 16px; border: 1px solid #e2e8f0; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
div[data-testid="stMetric"] label { color: #64748b !important; font-size: 12px !important; }
div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #1e293b !important; font-weight: 700 !important; }
.chart-card { background: #ffffff; border-radius: 12px; padding: 16px; border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 16px; }
.chart-title { font-weight: 600; color: #1e293b; font-size: 14px; }
.metric-card { background: #ffffff; border-radius: 10px; padding: 14px; border-left: 4px solid #3b82f6; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.canvas-toolbar { background: #ffffff; border-radius: 10px; padding: 12px 16px; border: 1px solid #e2e8f0; margin-bottom: 16px; }
div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input, .stTextArea textarea { background: #ffffff !important; color: #1e293b !important; border: 1px solid #cbd5e1 !important; border-radius: 8px !important; }
div[data-testid="stSelectbox"] > div > div, div[data-testid="stSelectbox"] div[role="combobox"] { background: #ffffff !important; color: #1e293b !important; border: 1px solid #cbd5e1 !important; border-radius: 8px !important; }
div[data-testid="stMultiSelect"] > div > div { background: #ffffff !important; color: #1e293b !important; border: 1px solid #cbd5e1 !important; }
/* File uploader */
div[data-testid="stFileUploader"], div[data-testid="stFileUploader"] section, div[data-testid="stFileUploaderDropzone"] { background: #f8fafc !important; border: 2px dashed #94a3b8 !important; border-radius: 8px !important; color: #475569 !important; }
div[data-testid="stFileUploader"] * { color: #475569 !important; }
div[data-testid="stTabs"] button { color: #64748b !important; font-weight: 500; }
div[data-testid="stTabs"] button[aria-selected="true"] { color: #3b82f6 !important; border-bottom: 2px solid #3b82f6; }
div[data-testid="stDataFrame"] * { color: #1e293b !important; }
div[data-testid="stExpander"] { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; }
div[data-testid="stExpander"] summary { color: #1e293b !important; }
div[data-testid="stSidebarNav"] { display: none; }
header[data-testid="stHeader"] { background: transparent; }
div[data-testid="stDownloadButton"] button { background: #f1f5f9 !important; color: #1e293b !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important; }
</style>
"""

DARK_CSS = """
<style>
.stApp { background: #0f172a !important; }
.main .block-container { max-width: 1400px; padding-top: 1rem; }
.stApp, .stApp p, .stApp span, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp div, .stApp strong, .stApp em, .stApp small, div[data-testid="stMarkdownContainer"], div[data-testid="stMarkdownContainer"] * { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] > div { background: #1e293b !important; border-right: 1px solid #334155; }
section[data-testid="stSidebar"], section[data-testid="stSidebar"] *, section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] div { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] .stButton > button { background: #334155 !important; color: #e2e8f0 !important; border: 1px solid #475569 !important; border-radius: 8px !important; font-size: 13px !important; }
section[data-testid="stSidebar"] .stButton > button[kind="primary"] { background: #3b82f6 !important; color: #ffffff !important; border: none !important; }
div[data-testid="stMetric"] { background: #1e293b !important; border-radius: 10px; padding: 14px 16px; border: 1px solid #334155; }
div[data-testid="stMetric"] label { color: #94a3b8 !important; font-size: 12px !important; }
div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #f1f5f9 !important; font-weight: 700 !important; }
div[data-testid="stMetric"] div[data-testid="stMetricDelta"] { color: #94a3b8 !important; }
.chart-card { background: #1e293b !important; border-radius: 12px; padding: 16px; border: 1px solid #334155; margin-bottom: 16px; }
.chart-title { font-weight: 600; color: #f1f5f9 !important; font-size: 14px; }
.metric-card { background: #1e293b !important; border-radius: 10px; padding: 14px; border-left: 4px solid #3b82f6; }
.canvas-toolbar { background: #1e293b !important; border-radius: 10px; padding: 12px 16px; border: 1px solid #334155; margin-bottom: 16px; }
/* ─ Input fields ─ */
div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input, .stTextArea textarea, div[data-testid="stTextInput"] > div, div[data-testid="stNumberInput"] > div { background: #1e293b !important; color: #e2e8f0 !important; border: 1px solid #475569 !important; border-radius: 8px !important; }
/* ─ Selectbox / Dropdown ─ */
div[data-testid="stSelectbox"] > div > div, div[data-testid="stSelectbox"] div[role="combobox"], div[data-testid="stSelectbox"] > div { background: #1e293b !important; color: #e2e8f0 !important; border: 1px solid #475569 !important; border-radius: 8px !important; }
div[data-testid="stSelectbox"] svg { color: #94a3b8 !important; fill: #94a3b8 !important; }
div[data-testid="stSelectbox"] input { background: #1e293b !important; color: #e2e8f0 !important; }
/* ─ Dropdown popup menu ─ */
div[data-baseweb="popover"], div[data-baseweb="popover"] *, div[data-baseweb="menu"], div[data-baseweb="menu"] * { background: #1e293b !important; color: #e2e8f0 !important; border-color: #475569 !important; }
ul[data-testid="stSelectboxVirtualDropdown"], ul[data-testid="stSelectboxVirtualDropdown"] * { background: #1e293b !important; color: #e2e8f0 !important; }
li[role="option"] { background: #1e293b !important; color: #e2e8f0 !important; }
li[role="option"]:hover { background: #334155 !important; }
li[aria-selected="true"] { background: #2d4a7a !important; }
/* ─ Multiselect ─ */
div[data-testid="stMultiSelect"] > div > div, div[data-testid="stMultiSelect"] > div { background: #1e293b !important; color: #e2e8f0 !important; border: 1px solid #475569 !important; border-radius: 8px !important; }
span[data-baseweb="tag"] { background: #334155 !important; color: #e2e8f0 !important; }
/* ─ File uploader ─ */
div[data-testid="stFileUploader"], div[data-testid="stFileUploader"] > div, div[data-testid="stFileUploader"] section, div[data-testid="stFileUploaderDropzone"] { background: #1e293b !important; border-color: #475569 !important; color: #e2e8f0 !important; border-radius: 8px !important; }
div[data-testid="stFileUploader"] button { background: #334155 !important; color: #e2e8f0 !important; border-color: #475569 !important; }
div[data-testid="stFileUploader"] * { color: #e2e8f0 !important; }
div[data-testid="stFileUploaderDropzone"] * { color: #94a3b8 !important; }
/* ─ Tabs ─ */
div[data-testid="stTabs"] button { color: #94a3b8 !important; background: transparent !important; }
div[data-testid="stTabs"] button[aria-selected="true"] { color: #60a5fa !important; border-bottom: 2px solid #60a5fa !important; }
div[data-testid="stTabs"] > div > div[role="tablist"] { background: #0f172a !important; border-bottom: 1px solid #334155; }
/* ─ Expander ─ */
div[data-testid="stExpander"] { background: #1e293b !important; border: 1px solid #334155 !important; border-radius: 10px !important; }
div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary *, div[data-testid="stExpander"] p, div[data-testid="stExpander"] span, div[data-testid="stExpander"] div { color: #e2e8f0 !important; background: transparent !important; }
div[data-testid="stExpander"] summary svg { fill: #94a3b8 !important; }
div[data-testid="stExpander"] > details > div[data-testid="stExpanderDetails"] { background: #1e293b !important; }
/* ─ DataFrame / Table ─ */
div[data-testid="stDataFrame"] { background: #1e293b !important; border-radius: 8px; border: 1px solid #334155; }
div[data-testid="stDataFrame"] *, div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th { color: #e2e8f0 !important; background: transparent !important; border-color: #334155 !important; }
div[data-testid="stDataFrame"] div[data-testid="glideDataEditor"], div[data-testid="stDataFrame"] canvas { background: #1e293b !important; }
/* ─ Buttons ─ */
.stButton > button { background: #334155 !important; color: #e2e8f0 !important; border: 1px solid #475569 !important; border-radius: 8px !important; }
.stButton > button:hover { background: #475569 !important; }
.stButton > button[kind="primary"] { background: #3b82f6 !important; color: #ffffff !important; border: none !important; }
/* ─ Radio / Checkbox ─ */
div[data-testid="stRadio"] label, div[data-testid="stCheckbox"] label { color: #e2e8f0 !important; }
div[data-testid="stRadio"] > div, div[data-testid="stCheckbox"] > div { background: transparent !important; }
/* ─ Slider ─ */
div[data-testid="stSlider"] label, div[data-testid="stSlider"] * { color: #e2e8f0 !important; }
div[data-testid="stSlider"] div[data-baseweb="slider"] > div { background: #334155 !important; }
/* ─ Alerts ─ */
div[data-testid="stAlert"] { border-radius: 8px !important; }
div[data-testid="stAlert"] * { color: #f1f5f9 !important; }
/* ─ Caption / small text ─ */
.stApp .stCaption, div[data-testid="caption"], p.stCaption, small { color: #94a3b8 !important; }
/* ─ Form ─ */
div[data-testid="stForm"] { background: #1e293b !important; border: 1px solid #334155 !important; border-radius: 10px; padding: 16px; }
div[data-testid="stForm"] * { color: #e2e8f0 !important; }
div[data-testid="stForm"] > div { background: #1e293b !important; }
/* ─ Number input steppers ─ */
button[data-testid="stNumberInputStepDown"], button[data-testid="stNumberInputStepUp"] { background: #334155 !important; color: #e2e8f0 !important; border-color: #475569 !important; }
/* ─ Code blocks ─ */
code, pre { background: #334155 !important; color: #e2e8f0 !important; border-radius: 4px; }
/* ─ Plotly charts ─ */
div[data-testid="stPlotlyChart"] { background: transparent !important; }
/* ─ Download button ─ */
div[data-testid="stDownloadButton"] button { background: #334155 !important; color: #e2e8f0 !important; border-color: #475569 !important; }
/* ─ Header / nav ─ */
header[data-testid="stHeader"] { background: transparent !important; }
div[data-testid="stSidebarNav"] { display: none !important; }
/* ─ Tooltip / popover ─ */
div[data-baseweb="tooltip"], div[data-baseweb="tooltip"] * { background: #334155 !important; color: #e2e8f0 !important; }
/* ─ Modal / dialog ─ */
div[data-testid="stModal"] > div, div[role="dialog"] { background: #1e293b !important; color: #e2e8f0 !important; border: 1px solid #334155 !important; }
div[role="dialog"] * { color: #e2e8f0 !important; }
/* ─ Select slider ─ */
div[data-testid="stSelectSlider"] * { color: #e2e8f0 !important; }
div[data-testid="stSelectSlider"] div[data-baseweb="slider"] > div { background: #334155 !important; }
/* ─ Catch-all for any remaining white backgrounds ─ */
.stApp * { color: #e2e8f0 !important; }
select, textarea, input { color: #e2e8f0 !important; background: #1e293b !important; border-color: #475569 !important; }
[class*="stWidget"] > div { background: transparent !important; }
</style>
"""


def apply_theme():
    theme = st.session_state.get("app_theme", "light")
    css = DARK_CSS if theme == "dark" else LIGHT_CSS
    st.markdown(css, unsafe_allow_html=True)


def theme_toggle_widget():
    current = st.session_state.get("app_theme", "light")
    label = "🌙 Dark Mode" if current == "light" else "🌞 Light Mode"
    if st.sidebar.button(label, use_container_width=True, key="theme_toggle_btn"):
        st.session_state["app_theme"] = "dark" if current == "light" else "light"
        st.rerun()
