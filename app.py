import traceback
import os

import streamlit as st
from ui.search_page import render_search_page
from ui.upload_page import render_upload_page
from ui.formula_search_page import render_formula_search_page
from ui.edit_page import render_edit_page
from services.turso_db import init_color_match_tables

st.set_page_config(
    page_title="color-match-ai",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)
try:
    init_color_match_tables()
except Exception as e:
    st.error("❌ Turso 初始化失敗")
    st.exception(e)
    st.stop()

# ======== 🚀 Modern Style ========
def apply_modern_style():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=DM+Mono:wght@300;400;500&display=swap');

.stApp, [data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 80% 0%, #102438 0, #0b1118 32%, #080c11 72%) !important;
    font-family: 'Inter', 'DM Mono', sans-serif !important;
}

[data-testid="stSidebar"] {
    background: #0b2f4a !important;
    min-width: 200px !important;
    max-width: 200px !important;
    padding-top: 10px !important;
}

.erp-title {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 2px;
}

.erp-sub {
    font-size: 10px;
    color: #9fb6cc;
    margin-bottom: 12px;
}

[data-testid="stSidebar"] .erp-group {
    font-size: 9.5px;
    color: #e06b3a;
    letter-spacing: 1.2px;
    margin: 10px 0 4px 0;
}

[data-testid="stSidebar"] div.stButton > button {
    background: transparent !important;
    color: #ffffff !important;
    border: 0 !important;
    width: 100%;
    text-align: left;
    font-size: 13px;
    padding: 6px 10px !important;
    border-radius: 6px;
}

[data-testid="stSidebar"] div.stButton > button:hover {
    background: #124466 !important;
}

[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
    background: #c6582f !important;
    border-left: 3px solid #ffb199 !important;
}

.block-container {
    max-width: 1180px;
    padding-top: 32px;
    padding-left: 34px;
    padding-right: 34px;
    padding-bottom: 56px;
}

.page-hero {
    display: flex;
    align-items: center;
    gap: 16px;
    margin: 0 0 26px 0;
    padding-bottom: 22px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}

.page-icon {
    display: grid;
    place-items: center;
    width: 48px;
    height: 48px;
    flex: 0 0 48px;
    border: 1px solid rgba(98,184,231,0.25);
    border-radius: 14px;
    background: linear-gradient(145deg, rgba(31,91,128,0.7), rgba(18,52,76,0.45));
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    font-size: 22px;
}

.page-eyebrow {
    margin-bottom: 3px;
    color: #62b8e7;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.6px;
}

.page-title {
    color: #f4f8fb;
    font-size: 25px;
    font-weight: 700;
    line-height: 1.25;
}

.page-description {
    margin-top: 5px;
    color: #91a4b7;
    font-size: 13px;
}

input, textarea {
    background: rgba(16,24,33,0.92) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 9px !important;
    font-family: 'DM Mono', monospace !important;
}

div.block-container .stButton > button {
    background: linear-gradient(180deg, #174f73, #103b58) !important;
    color: white !important;
    border-radius: 9px !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    font-weight: 600 !important;
}

div.block-container .stButton > button:hover {
    background: #124466 !important;
}

div.block-container .stButton > button[kind="primary"] {
    background: #1a5a84 !important;
}

div[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(17, 27, 37, 0.72);
    border-color: rgba(255,255,255,0.09) !important;
    border-radius: 12px !important;
}

[data-testid="stFileUploaderDropzone"] {
    background: rgba(16,24,33,0.72) !important;
    border: 1px dashed rgba(98,184,231,0.32) !important;
    border-radius: 12px !important;
}

[data-testid="stExpander"] {
    background: rgba(17,27,37,0.55);
    border-color: rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
}

div[data-baseweb="popover"] {
    background: #1f2630 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
}

ul[role="listbox"] li {
    color: #d7e3ef !important;
}

ul[role="listbox"] li:hover {
    background: rgba(198,88,47,0.15) !important;
}

h1 {
    color: #ffffff !important;
    font-size: 20px !important;
    font-weight: 700 !important;
    margin-bottom: 0 !important;
}

h2, h3 {
    color: #cfd8e3 !important;
}

[data-testid="stCaptionContainer"] p {
    color: #9fb6cc !important;
    font-size: 11px !important;
}

[data-testid="stAlert"] {
    border-radius: 6px !important;
    font-size: 13px !important;
}

label, [data-testid="stWidgetLabel"] p {
    color: #9fb6cc !important;
    font-size: 12px !important;
}
</style>
""", unsafe_allow_html=True)


# ======== Sidebar Menu ========
def render_sidebar():
    MENU_ITEMS = [
        {"group": "色彩", "key": "相似色搜尋",   "label": "🔍 相似色搜尋"},
        {"group": "色彩", "key": "搜尋配方色板", "label": "🧪 搜尋配方色板"},
        {"group": "色彩", "key": "上傳色板",     "label": "⬆️ 上傳色板"},
        {"group": "色彩", "key": "修改色板資料", "label": "✏️ 修改色板資料"},
    ]

    if "menu" not in st.session_state:
        st.session_state.menu = "相似色搜尋"

    with st.sidebar:
        st.markdown("<div class='erp-title' style='font-size: 24px; font-weight: bold;'>Color-Match-AI</div>", unsafe_allow_html=True)
        st.markdown("<div class='erp-sub' style='font-size: 12px; color: #888888;'>v1.0 · 色彩知識庫</div>", unsafe_allow_html=True)

        current_group = None
        for item in MENU_ITEMS:
            if item["group"] != current_group:
                st.markdown(f"<div class='erp-group'>{item['group']}</div>", unsafe_allow_html=True)
                current_group = item["group"]
            if st.button(
                item["label"],
                key=item["key"],
                use_container_width=True,
                type="primary" if st.session_state.menu == item["key"] else "secondary"
            ):
                st.session_state.menu = item["key"]
                st.rerun()


# ======== Main ========
apply_modern_style()
render_sidebar()

menu = st.session_state.get("menu")

if menu == "上傳色板":
    render_upload_page()
elif menu == "搜尋配方色板":
    render_formula_search_page()
elif menu == "修改色板資料":
    render_edit_page()
else:
    render_search_page()
