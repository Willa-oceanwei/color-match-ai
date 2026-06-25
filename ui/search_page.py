from pathlib import Path
import streamlit as st

from ui.result_components import render_result_card
from services.search_service import search_top_k


def render_search_page():

    st.markdown(
        "<h2 style='font-size: 24px; font-weight: bold; color: #333333;'>相近色板搜尋</h2>",
        unsafe_allow_html=True
    )

    material = st.selectbox(
        "Material",
        ["PP", "ABS", "TPR", "NY", "PC", "PE", "PVC", "PS"]
    )

    uploaded = st.file_uploader(
        "上傳樣品",
        type=["jpg", "png", "jpeg"]
    )

    if uploaded:
        st.image(uploaded, caption="Query Sample")

    # =====================
    # BUTTON
    # =====================
    if st.button("🔍 Start Matching", disabled=uploaded is None):
        try:
            tmp_path = Path("tmp/query.jpg")
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_bytes(uploaded.getvalue())

            results = search_top_k(material, tmp_path, top_k=5)

            if not results:
                st.warning("⚠️ 沒有搜尋結果")
                return

            st.success(f"找到 {len(results)} 筆結果")
            for i, r in enumerate(results, 1):
                render_result_card(i, r)

        except Exception as e:
            st.error(f"SEARCH ERROR: {e}")

            # =====================
            # NO DATA
            # =====================
            if results is None:
                st.error("❌ results = None（search crash）")
                return

            if len(results) == 0:
                st.warning("⚠️ 沒有搜尋結果（results = []）")
                return

            # =====================
            # RENDER
            # =====================
            st.success(f"找到 {len(results)} 筆結果")

            for i, r in enumerate(results, 1):
                try:
                    render_result_card(i, r)
                except Exception as e:
                    st.error(f"render card error: {e}")
                    st.write(r)

        except Exception as e:
            st.error(f"SEARCH ERROR: {e}")
