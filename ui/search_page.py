from pathlib import Path
import streamlit as st
from ui.result_components import render_result_card
from services.search_service import search_top_k


def render_search_page() -> None:
    st.markdown("""
        <div style="
            background: linear-gradient(135deg, #0b2f4a 0%, #0f3d5e 100%);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            padding: 18px 22px;
            margin-bottom: 20px;
        ">
            <div style="font-size:13px; color:#e06b3a; font-weight:600; letter-spacing:1px; margin-bottom:4px;">
                色彩搜尋
            </div>
            <div style="font-size:20px; color:#ffffff; font-weight:700; margin-bottom:4px;">
                相似色 Top 5 搜尋
            </div>
            <div style="font-size:12px; color:#9fb6cc;">
                上傳客戶樣品照片，自動比對色板資料庫，找出最接近的歷史配方
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown("<div style='color:#9fb6cc; font-size:12px; margin-bottom:4px;'>Material</div>",
                    unsafe_allow_html=True)
        material = st.text_input(
            "Material",
            value="ABS",
            key="search_material",
            label_visibility="collapsed"
        )

        st.markdown("<div style='color:#9fb6cc; font-size:12px; margin-top:12px; margin-bottom:4px;'>上傳客戶樣品照片</div>",
                    unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "上傳客戶樣品照片",
            type=["jpg", "jpeg", "png"],
            key="query_image",
            label_visibility="collapsed"
        )

        if uploaded:
            st.image(uploaded, caption="查詢樣品", use_container_width=True)

    with col_right:
        st.markdown("""
            <div style="
                background: #111111;
                border: 1px dashed rgba(255,255,255,0.1);
                border-radius: 8px;
                padding: 24px;
                text-align: center;
                color: #4a6070;
                font-size: 13px;
                min-height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
            ">
                搜尋結果將顯示於此
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    if st.button("🔍 搜尋 Top 5", type="primary", disabled=uploaded is None, use_container_width=False):
        tmp_path = Path("tmp") / uploaded.name
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_bytes(uploaded.getvalue())

        with st.spinner("比對中..."):
            results = search_top_k(material, tmp_path, top_k=5)

        if not results:
            st.warning("目前沒有可搜尋的向量資料，請先上傳色板或重建向量。")
        else:
            st.markdown("""
                <div style="color:#e06b3a; font-size:11px; letter-spacing:1px; font-weight:600; margin: 16px 0 8px 0;">
                    搜尋結果
                </div>
            """, unsafe_allow_html=True)
            for index, result in enumerate(results, start=1):
                render_result_card(index, result)
