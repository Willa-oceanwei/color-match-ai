import streamlit as st
import base64
import io
from PIL import Image


def _base64_to_image(b64: str):
    try:
        img_bytes = base64.b64decode(b64)
        return Image.open(io.BytesIO(img_bytes))
    except Exception:
        return None


def render_result_card(index: int, result: dict):
    score = result["score"]
    if score > 0.92:
        color = "🟢"
    elif score > 0.85:
        color = "🟡"
    else:
        color = "🔴"

    with st.container():
        st.markdown(f"""
        ### {color} Rank #{index} | 相似度：{score:.2%}
        **ID**：{result["id"]}  
        **Material**：{result["material"]}  
        **Formula**：{result["formula_id"]}  
        **Status**：{result["recipe_status"]}
        """)

        col1, col2 = st.columns(2)
        with col1:
            st.caption("查詢樣品")
            try:
                st.image("tmp/query.jpg", use_container_width=True)
            except Exception:
                st.info("查詢樣品無法顯示")

        with col2:
            st.caption("歷史色板")
            b64 = result.get("image_base64", "")
            if b64:
                img = _base64_to_image(b64)
                if img:
                    st.image(img, use_container_width=True)
                else:
                    st.warning("圖片無法顯示")
            else:
                st.info("無圖片")

        with st.expander("🧪 查看配方 (Formula)"):
            st.write("（這裡接你的 Formula Sheet）")

        st.divider()
