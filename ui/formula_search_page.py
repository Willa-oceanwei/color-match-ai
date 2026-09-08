import streamlit as st
import base64
import io
from PIL import Image
from ui.design import format_quantity, render_page_header
from services.google_sheet import read_colorboard
from services.formula_repository import lookup_formula_by_id
from services.turso_db import (
    get_color_match_board_by_id,
    get_color_match_boards_by_formula_id,
    get_similar_formula_ids,
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


def _use_suggested_formula(formula_id: str):
    st.session_state["formula_search_query"] = formula_id


def render_formula_search_page():
    render_page_header(
        "🧪",
        "FORMULA LIBRARY",
        "搜尋配方色板",
        "以配方、色板、公司或顏色，快速找到歷史色板與配方明細。",
    )

    search_col, tool_col = st.columns([6, 1], vertical_alignment="bottom")
    with search_col:
        search_id = st.text_input(
            "搜尋資料庫",
            placeholder="輸入配方編號、公司名稱或顏色…",
            label_visibility="collapsed",
            key="formula_search_query",
        )
    with tool_col:
        with st.popover("⚙️ 資料維護", use_container_width=True):
            st.markdown("**匯入 Google Sheet 舊色板**")
            st.caption("僅補入 Turso 尚未存在的色板，不會覆蓋目前資料。")
            if st.button("開始匯入", type="secondary", use_container_width=True):
                try:
                    with st.spinner("正在匯入…"):
                        sheet_rows = read_colorboard()
                        migration = import_color_match_boards(sheet_rows)
                    st.success(
                        f"新增 {migration['inserted']} 筆，"
                        f"略過 {migration['skipped']} 筆。"
                    )
                except Exception as error:
                    st.error("舊資料匯入失敗。")
                    st.caption(f"診斷訊息：{error}")

    st.caption("可搜尋：配方編號 · 色板 ID · 公司名稱 · 顏色")

    if not search_id.strip():
        st.markdown("#### 最近一筆記錄")
        try:
            recent_rows = get_recent_color_match_boards(limit=1)
        except Exception as error:
            st.error("無法讀取色板資料庫；這不是正常的同步等待。")
            st.caption(f"診斷訊息：{error}")
            return

        if recent_rows:
            row = recent_rows[0]
            item_number = row.get("FormulaID", "") or row.get("ID", "")
            with st.container(border=True):
                title_col, meta_col = st.columns([3, 2])
                with title_col:
                    st.markdown(
                        f"**{row.get('ColorName', '') or '未命名顏色'}**　"
                        f"`{item_number}`"
                    )
                    st.caption(f"{row.get('Customer', '') or '未填公司'} · {row.get('Material', '')}")
                with meta_col:
                    st.caption("最後更新")
                    st.markdown(row.get("LastUpdate", "") or row.get("CreateDate", "") or "—")
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
        try:
            similar_ids = get_similar_formula_ids(search_id)
        except Exception:
            similar_ids = []
        if similar_ids:
            st.info("是否輸入有誤？找到以下相近的配方編號：")
            suggestion_columns = st.columns(min(len(similar_ids), 5))
            for column, formula_id in zip(suggestion_columns, similar_ids):
                with column:
                    st.button(
                        f"搜尋 {formula_id}",
                        key=f"similar_formula_{formula_id}",
                        on_click=_use_suggested_formula,
                        args=(formula_id,),
                        use_container_width=True,
                    )
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
        if f.get("FormulaSource"):
            st.caption(f"配方來源：{f['FormulaSource']}")

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
                    "重量 (g)": format_quantity(w)
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
