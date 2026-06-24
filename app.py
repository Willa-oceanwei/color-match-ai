import streamlit as st
from ui.search_page import render_search_page
from ui.upload_page import render_upload_page

st.set_page_config(page_title="color-match-ai", page_icon="💡", layout="wide")

# ======== 🚀 Modern Style ========
def apply_modern_style():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=DM+Mono:wght@300;400;500&display=swap');

.stApp, [data-testid="stAppViewContainer"] {
    background: #0a0a0a !important;
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
    padding-top: 4px;
    padding-left: 22px;
    padding-right: 22px;
}

input, textarea {
    background: #161616 !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 6px !important;
    font-family: 'DM Mono', monospace !important;
}

div.block-container .stButton > button {
    background: #0b2f4a !important;
    color: white !important;
    border-radius: 6px !important;
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

/* page title */
h1 {
    color: #ffffff !important;
    font-size: 20px !important;
    font-weight: 700 !important;
    margin-bottom: 0 !important;
}

/* header / subheader */
h2, h3 {
    color: #cfd8e3 !important;
}

/* caption */
[data-testid="stCaptionContainer"] p {
    color: #9fb6cc !important;
    font-size: 11px !important;
}

/* info / warning / success boxes */
[data-testid="stAlert"] {
    border-radius: 6px !important;
    font-size: 13px !important;
}

/* label text */
label, [data-testid="stWidgetLabel"] p {
    color: #9fb6cc !important;
    font-size: 12px !important;
}
</style>
""", unsafe_allow_html=True)


# ======== Sidebar Menu ========
def render_sidebar():
    MENU_ITEMS = [
        {"group": "色彩", "key": "相似色搜尋", "label": "🔍 相似色搜尋"},
        {"group": "色彩", "key": "上傳色板",   "label": "⬆️ 上傳色板"},
    ]

    if "menu" not in st.session_state:
        st.session_state.menu = "相似色搜尋"

    with st.sidebar:
        # 修改 erp-title 的字體大小（例如改為 28px）
        st.markdown("<div class='erp-title' style='font-size: 24px; font-weight: bold;'>Color-Match-Ai</div>", unsafe_allow_html=True)
    
        # 修改 erp-sub 的字體大小（例如改為 14px）
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

st.title("🎨 color-match-ai")
st.caption("色彩案例知識庫：樣品 → 拍照 → 上傳 → 找最相似色板 → 顯示配方")

if st.session_state.get("menu") == "上傳色板":
    render_upload_page()
else:
    render_search_page()
