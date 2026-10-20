import streamlit as st
import base64
import io
from PIL import Image
from services.formula_repository import lookup_formula_by_id
from ui.design import format_quantity


def _base64_to_image(b64: str):
    try:
        img_bytes = base64.b64decode(b64)
        return Image.open(io.BytesIO(img_bytes))
    except Exception:
        return None


def render_result_card(index: int, result: dict, *, show_color_preview=False, query_image=None):
    with st.container():
        metric = (f"照片色差 ΔE76：{result['delta_e']:.2f}（越小越接近）"
                  if 'delta_e' in result else f"影像特徵相似度：{result['score']:.2%}")
        st.markdown(f"""
        ##### Rank #{index} | {metric}
        **ID**：{result["id"]}  
        **Material**：{result["material"]}  
        **Formula**：{result["formula_id"]}  
        **Status**：{result["recipe_status"]}
        """)

        col1, col2 = st.columns(2)

        with col1:
            st.caption("查詢樣品")
            try:
                query_preview = (_base64_to_image(result.get('query_preview_base64', ''))
                                 if show_color_preview else None)
                if query_image is not None:
                    st.image(query_image, use_container_width=True)
                if query_preview is not None:
                    st.image(query_preview, use_container_width=True)
                    st.caption('桃紅色區域已排除；其餘區域參與比對')
                    st.caption(f"代表色 RGB：{result.get('query_rgb', '')}")
                elif query_image is None:
                    st.info('查詢樣品無法顯示')
            except Exception:
                st.info("查詢樣品無法顯示")

        with col2:
            board_preview = (_base64_to_image(result.get('board_preview_base64', ''))
                             if show_color_preview else None)
            if board_preview is not None:
                st.image(board_preview, caption='歷史色板取色範圍（桃紅色已排除）',
                         use_container_width=True)
                st.caption(f"代表色 RGB：{result.get('board_rgb', '')}")
            st.caption("歷史完成色板")
            b64 = result.get("image_base64", "")
            if b64:
                img = _base64_to_image(b64)
                if img:
                    st.image(img, use_container_width=True)
                else:
                    st.warning("圖片無法顯示")
            else:
                st.info("無圖片")

            st.markdown("**客戶樣品留存**")
            retained_samples = []
            for sample_index in (1, 2):
                sample_b64 = result.get(f"sample_image_{sample_index}_base64", "") or ""
                if sample_b64:
                    retained_samples.append((sample_index, sample_b64))

            if retained_samples:
                sample_columns = st.columns(len(retained_samples))
                for column, (sample_index, sample_b64) in zip(
                    sample_columns, retained_samples
                ):
                    with column:
                        sample_image = _base64_to_image(sample_b64)
                        if sample_image:
                            st.image(
                                sample_image,
                                use_container_width=True,
                                caption=f"客戶樣品照 {sample_index}",
                            )
                        else:
                            st.warning(f"客戶樣品照 {sample_index} 無法顯示")
            else:
                st.info("未留存樣品照")

            sample_description = result.get("sample_description", "") or ""
            if sample_description:
                st.markdown(f"**樣品說明：**  {sample_description}")

        with st.expander("查看配方 (Formula)"):
            formula_id = result.get("formula_id", "")

            if not formula_id:
                st.info("此色板無配方編號")

            else:
                formulas = lookup_formula_by_id(str(formula_id))

                if not formulas:
                    st.info(f"查無配方資料（FormulaID: {formula_id}）")

                else:
                    f = formulas[0]

                    # =====================
                    # 色粉資料（先顯示）
                    # =====================
                    st.markdown("**色粉明細**")

                    pigment_data = []

                    for i in range(1, 9):
                        p = f.get(f"Pigment{i}", "")
                        w = f.get(f"Weight{i}", "")

                        if p:
                            pigment_data.append({
                                "色粉編號": p,
                                "重量 (g)": format_quantity(w)
                            })

                    if pigment_data:
                        st.table(pigment_data)
                    else:
                        st.info("無色粉資料")

                    if f.get("Remark"):
                        st.caption(f"備註：{f.get('Remark')}")

                    # =====================
                    # 配方資料（後顯示）
                    # =====================
                    summary_items = [
                        ("添加比例", f"{f.get('AddRatio', '-') or '-'} g/kg"),
                        ("淨重", f"{format_quantity(f.get('NetWeight', '')) or '-'} {f.get('NetWeightUnit', '') or 'g'}"),
                        ("合計類別", f.get("TotalType", "") or "-"),
                        ("Pantone", f.get("Pantone", "") or "-"),
                    ]
                    for column, (label, value) in zip(st.columns(4), summary_items):
                        with column:
                            st.caption(label)
                            st.write(value)

        st.divider()
