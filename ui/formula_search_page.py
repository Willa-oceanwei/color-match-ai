import streamlit as st
import base64
import io
from PIL import Image
from services.google_sheet import lookup_formula_by_id
from services.google_sheet import read_colorboard
from services.turso_db import (
    get_color_match_board_by_id,
    get_color_match_boards_by_formula_id,
    get_recent_color_match_boards,
    import_color_match_boards,
    search_color_match_boards,
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
        "搜尋配方編號、色板 ID、公司名稱或顏色",
        placeholder="例如：52824、公司名稱或紅色",
    )

    with st.expander("📥 匯入 Google Sheet 舊色板"):
        st.caption("只補進 Turso 尚未存在的色板 ID，不會覆蓋目前資料。")
        if st.button("開始匯入舊色板", type="secondary"):
            try:
                with st.spinner("正在讀取 Google Sheet 並匯入 Turso…"):
                    sheet_rows = read_colorboard()
                    migration = import_color_match_boards(sheet_rows)
                st.success(
                    f"匯入完成：新增 {migration['inserted']} 筆、"
                    f"略過 {migration['skipped']} 筆，共檢查 {migration['total']} 筆。"
                )
            except Exception as error:
                st.error("Google Sheet 舊資料匯入失敗。")
                st.caption(f"診斷訊息：{error}")

    if not search_id.strip():
        st.info("請輸入配方編號、色板 ID、公司名稱或顏色。")
        st.markdown("### 最近一筆記錄")
        try:
            recent_rows = get_recent_color_match_boards(limit=1)
        except Exception as error:
            st.error("無法讀取色板資料庫；這不是正常的同步等待。")
            st.caption(f"診斷訊息：{error}")
            return

        if recent_rows:
            st.dataframe(
                [
                    {
                        "顏色（料號）": (
                            f"{row.get('ColorName', '') or '（未填顏色）'}"
                            f"（{row.get('FormulaID', '') or row.get('ID', '')}）"
                        ),
                        "色板 ID": row.get("ID", ""),
                        "原料": row.get("Material", ""),
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
        if not matched:
            matched = search_color_match_boards(search_id)
    except Exception as error:
        st.error("無法讀取色板資料庫；這不是正常的同步等待。")
        st.caption(f"診斷訊息：{error}")
        return

    if not matched:
        st.warning(f"查無配方、色板、公司或顏色：{search_id}")
        return

    st.success(f"找到 {len(matched)} 筆色板")

    # 配方資料
    matched_formula_ids = {
        str(row.get("FormulaID", "") or "").strip()
        for row in matched
        if str(row.get("FormulaID", "") or "").strip()
    }
    matched_formula_id = (
        next(iter(matched_formula_ids)) if len(matched_formula_ids) == 1 else ""
    )
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
            item_number = row.get("FormulaID", "") or row.get("ID", "")
            st.caption(
                f"ColorName: {row.get('ColorName', '')}（料號：{item_number}）"
            )
