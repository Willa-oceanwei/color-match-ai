from pathlib import Path
import streamlit as st
from ui.result_components import render_result_card
from services.search_service import search_top_k


def render_search_page() -> None:
    st.header("相似色 Top 5 搜尋")
    material = st.text_input("Material", value="ABS", key="search_material")
    uploaded = st.file_uploader("上傳客戶樣品照片", type=["jpg", "jpeg", "png"], key="query_image")
    if uploaded:
        st.image(uploaded, caption="查詢樣品", width=260)
    if st.button("搜尋 Top 5", type="primary", disabled=uploaded is None):
        tmp_path = Path("tmp") / uploaded.name
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_bytes(uploaded.getvalue())
        results = search_top_k(material, tmp_path, top_k=5)
        if not results:
            st.warning("目前沒有可搜尋的向量資料，請先上傳色板或重建向量。")
        for index, result in enumerate(results, start=1):
            render_result_card(index, result)
