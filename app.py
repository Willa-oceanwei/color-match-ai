from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Color-Match-AI",
    page_icon=":material/palette:",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def initialize_database():
    """Initialize the schema once per server process, not on every rerun."""
    from services.turso_db import init_color_match_tables

    init_color_match_tables()


try:
    initialize_database()
except Exception as error:
    st.error("Turso 初始化失敗")
    st.exception(error)
    st.stop()


def apply_modern_style():
    css = (Path(__file__).parent / "ui" / "styles.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_sidebar():
    menu_items = [
        ("相似色板搜尋", ":material/image_search:"),
        ("色板查詢", ":material/search:"),
        ("色板管理", ":material/inventory_2:"),
    ]
    if "menu" not in st.session_state:
        st.session_state.menu = "相似色板搜尋"

    with st.sidebar:
        st.markdown(
            "<div class='brand-mark'><span></span><span></span><span></span></div>"
            "<div class='erp-title'>Color-Match-AI</div>"
            "<div class='erp-sub'>色板與配方工作台</div>",
            unsafe_allow_html=True,
        )
        st.divider()
        for item, icon in menu_items:
            if st.button(
                item,
                icon=icon,
                key=f"navigation_{item}",
                use_container_width=True,
                type="primary" if st.session_state.menu == item else "secondary",
            ):
                st.session_state.menu = item
                st.rerun()


apply_modern_style()
render_sidebar()

menu = st.session_state.get("menu")
if menu == "色板查詢":
    from ui.board_search_page import render_board_search_page

    render_board_search_page()
elif menu == "色板管理":
    from ui.board_management_page import render_board_management_page

    render_board_management_page()
else:
    from ui.search_page import render_search_page

    render_search_page()
