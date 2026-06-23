import streamlit as st
from ui.search_page import render_search_page
from ui.upload_page import render_upload_page

st.set_page_config(page_title="color-match-ai", page_icon="🎨", layout="wide")
st.title("🎨 color-match-ai")
st.caption("色彩案例知識庫：樣品 → 拍照 → 上傳 → 找以前最像的相同料色板 → 顯示以前配方")

page = st.sidebar.radio("功能", ["相似色搜尋", "上傳色板"])

if page == "上傳色板":
    render_upload_page()
else:
    render_search_page()
