import streamlit as st


def render_result_card(index: int, result: dict):

    score = result["score"]

    # 顏色判斷
    if score > 0.92:
        color = "🟢"
    elif score > 0.85:
        color = "🟡"
    else:
        color = "🔴"

    with st.container():

        st.markdown(f"""
        ### {color} Rank #{index}  | 相似度：{score:.2%}

        **ID**：{result["id"]}  
        **Material**：{result["material"]}  
        **Formula**：{result["formula_id"]}  
        **Status**：{result["recipe_status"]}
        """)

        # 圖片對比區
        col1, col2 = st.columns(2)

        with col1:
            st.caption("查詢樣品")
            st.image("tmp/query.jpg", use_container_width=True)

        with col2:
            st.caption("歷史色板")
            st.image(result["image_path"], use_container_width=True)

        # 展開配方
        with st.expander("🧪 查看配方 (Formula)"):
            st.write("（這裡接你的 Formula Sheet）")

        st.divider()
