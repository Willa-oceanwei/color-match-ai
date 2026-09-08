import streamlit as st
import base64
import io
from PIL import Image
from services.google_sheet import lookup_formula_by_id
from services.turso_db import (
    get_color_match_board_by_id,
    get_color_match_boards_by_formula_id,
    get_recent_color_match_boards,
)

def _base64_to_image(b64: str):
    try:
        img_bytes = base64.b64decode(b64)
        return Image.open(io.BytesIO(img_bytes))
    except Exception:
        return None


def render_formula_search_page():
    st.markdown(
        "<h2 style='font-size: 24px; font-weight: bold;'>搜尋配方色板</h2>",
        unsafe_allow_html=True
    )

    search_id = st.text_input(
        "輸入配方編號或色板 ID",
        placeholder="例如：52824 或 ABS_TRIAL_20260908_143000",
    )

    if not search_id.strip():
        st.info("請輸入配方編號或色板 ID，也可從下方最近新增紀錄確認。")
        st.markdown("### 最近新增的色板")
        try:
            recent_rows = get_recent_color_match_boards(limit=20)
        except Exception:
            st.warning(
                "暫時無法載入最近新增紀錄，可能正在同步 Turso。"
                "您仍可在上方輸入配方編號查詢，或稍後重新整理。"
            )
            return

        if recent_rows:
            st.dataframe(
                [
                    {
                        "配方編號": row.get("FormulaID", "") or "（未填）",
                        "色板 ID": row.get("ID", ""),
                        "原料": row.get("Material", ""),
                        "色名": row.get("ColorName", ""),
                        "客戶": row.get("Customer", ""),
                        "新增時間": row.get("LastUpdate", "")
                        or row.get("CreateDate", ""),
                    }
                    for row in recent_rows
                ],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.caption("目前還沒有色板紀錄。")
        return

    # 可用配方編號或上傳完成時顯示的色板 ID 查詢。沒有配方編號的
    # 留樣仍可透過色板 ID 找回。
    try:
        matched = get_color_match_boards_by_formula_id(search_id)
        if not matched:
            board = get_color_match_board_by_id(search_id)
            matched = [board] if board else []
    except Exception:
        st.error("配方色板暫時無法讀取，可能正在同步 Turso，請稍後再試。")
        return

    if not matched:
        st.warning(f"查無配方編號或色板 ID：{search_id}")
        return

    st.success(f"找到 {len(matched)} 筆色板")

    # 配方資料
    matched_formula_id = str(matched[0].get("FormulaID", "") or "").strip()
    try:
        formulas = lookup_formula_by_id(matched_formula_id) if matched_formula_id else []
    except Exception:
        formulas = []
        st.warning("色板已找到，但目前無法從配方表載入色粉明細。")

    if formulas:
        f = formulas[0]

        # =====================
        # 色粉明細（先顯示）
        # =====================
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
            st.markdown("### 🧬 色粉明細")
            st.table(pigment_data)

        if f.get("Remark"):
            st.caption(f"備註：{f.get('Remark')}")

        st.divider()

        # =====================
        # 配方資料（後顯示）
        # =====================
        col_a, col_b, col_c, col_d = st.columns(4)

        with col_a:
            st.markdown(
                f"<div style='font-size:15px;color:#9fb6cc;'>添加比例</div>"
                f"<div style='font-size:15px;color:#ffffff;'>{f.get('AddRatio', '-')} g/kg</div>",
                unsafe_allow_html=True
            )

        with col_b:
            st.markdown(
                f"<div style='font-size:15px;color:#9fb6cc;'>淨重</div>"
                f"<div style='font-size:15px;color:#ffffff;'>{f.get('NetWeight', '-')} g</div>",
                unsafe_allow_html=True
            )

        with col_c:
            st.markdown(
                f"<div style='font-size:15px;color:#9fb6cc;'>合計類別</div>"
                f"<div style='font-size:15px;color:#ffffff;'>{f.get('TotalType', '-')}</div>",
                unsafe_allow_html=True
            )

        with col_d:
            st.markdown(
                f"<div style='font-size:15px;color:#9fb6cc;'>Pantone</div>"
                f"<div style='font-size:15px;color:#ffffff;'>{f.get('Pantone', '-')}</div>",
                unsafe_allow_html=True
            )

    # 色板圖片
    cols = st.columns(3)

    for i, row in enumerate(matched):
        with cols[i % 3]:

            b64 = row.get("ImageBase64", "")

            if b64:
                img = _base64_to_image(b64)

                if img:
                    st.image(img, use_container_width=True)

            st.caption(f"**{row.get('ID', '')}**")
            st.caption(f"Material: {row.get('Material', '')}")
            st.caption(f"Status: {row.get('RecipeStatus', '')}")
            st.caption(f"Customer: {row.get('Customer', '')}")
            st.caption(f"ColorName: {row.get('ColorName', '')}")
