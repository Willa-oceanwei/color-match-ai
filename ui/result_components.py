import streamlit as st
import base64
import io
from PIL import Image
from services.google_sheet import lookup_formula_by_id


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
        ##### {color} Rank #{index} | 相似度：{score:.2%}
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
            formula_id = result.get("formula_id", "")
            if not formula_id:
                st.info("此色板無配方編號")
            else:
                formulas = lookup_formula_by_id(str(formula_id))
                if not formulas:
                    st.info(f"查無配方資料（FormulaID: {formula_id}）")
                else:
                    f = formulas[0]

                    # 基本資料
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.markdown(f"<div style='font-size:11px;color:#9fb6cc;'>添加比例</div><div style='font-size:13px;color:#ffffff;'>{f.get('AddRatio', '-')} g/kg</div>", unsafe_allow_html=True)
                    with col_b:
                        st.markdown(f"<div style='font-size:11px;color:#9fb6cc;'>淨重</div><div style='font-size:13px;color:#ffffff;'>{f.get('NetWeight', '-')} g</div>", unsafe_allow_html=True)
                    with col_c:
                        st.markdown(f"<div style='font-size:11px;color:#9fb6cc;'>合計類別</div><div style='font-size:13px;color:#ffffff;'>{f.get('TotalType', '-')}</div>", unsafe_allow_html=True)
                    with col_d:
                        st.markdown(f"<div style='font-size:11px;color:#9fb6cc;'>Pantone</div><div style='font-size:13px;color:#ffffff;'>{f.get('Pantone', '-')}</div>", unsafe_allow_html=True)

                    # 色粉資料
                    st.markdown("**色粉明細**")
                    pigment_data = []
                    for i in range(1, 9):
                        p = f.get(f"Pigment{i}", "")
                        w = f.get(f"Weight{i}", "")
                        if p:
                            pigment_data.append({
                                "色粉編號": p,
                                "重量 (g)": w
                            })

                    if pigment_data:
                        st.table(pigment_data)
                    else:
                        st.info("無色粉資料")

                    if f.get("Remark"):
                        st.caption(f"備註：{f.get('Remark')}")

        st.divider()
