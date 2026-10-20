import streamlit as st
from datetime import datetime
from services.google_sheet import append_formula_row
from services.formula_repository import lookup_formula_by_id
from services.turso_db import (
    get_color_match_board_by_id,
    get_color_match_boards_by_formula_id,
    search_color_match_boards,
    update_color_match_board,
)
from services.embedding_service import embed_image, upsert_embedding
from services.google_drive import write_uploaded_bytes_get_base64, resolve_local_image_path
import base64
import io
from PIL import Image
from ui.design import render_page_header
from ui.photo_editor import render_photo_editor, photo_is_modified
from services.id_utils import build_image_path, build_sample_image_path


def _base64_to_image(b64: str):
    try:
        return Image.open(io.BytesIO(base64.b64decode(b64)))
    except Exception:
        return None


def render_edit_page():
    render_page_header(
        "BOARD EDITOR", "編輯色板",
        "搜尋既有色板後，更新基本資料、配方內容或照片。",
    )

    # =========================
    # 查詢
    # =========================
    search_formula = st.text_input(
        "搜尋 FormulaID、色板 ID、公司名稱或顏色",
        placeholder="例如：52824、公司名稱或紅色",
    )

    if st.button("查詢"):
        st.session_state.pop("edit_target", None)
        st.session_state.pop("edit_targets", None)
        if search_formula.strip():
            try:
                rows = get_color_match_boards_by_formula_id(search_formula.strip())
                if not rows:
                    board = get_color_match_board_by_id(search_formula.strip())
                    rows = [board] if board else []
                if not rows:
                    rows = search_color_match_boards(search_formula.strip())
            except Exception as error:
                st.error("無法讀取色板資料庫；這不是正常的同步等待。")
                st.caption(f"診斷訊息：{error}")
                return
            if rows:
                st.session_state["edit_targets"] = rows
                st.session_state["edit_target"] = rows[0]
            else:
                st.error(f"找不到配方、色板、公司或顏色：{search_formula}")
        else:
            st.warning("請輸入 FormulaID、色板 ID、公司名稱或顏色")

    # 如果 FormulaID 查到多筆，讓使用者選
    if "edit_targets" in st.session_state and len(st.session_state["edit_targets"]) > 1:
        targets = st.session_state["edit_targets"]
        options = [
            f"{r.get('ColorName', '') or '未填顏色'}（料號："
            f"{r.get('FormulaID', '') or r['ID']}）｜{r['ID']}"
            for r in targets
        ]
        selected = st.selectbox("找到多筆，請選擇要編輯的 ID", options)
        selected_index = options.index(selected)
        st.session_state["edit_target"] = targets[selected_index]

    if "edit_target" not in st.session_state:
        return

    row = st.session_state["edit_target"]
    board_id = row["ID"]
    st.success(f"已載入：{board_id}")

    # =========================
    # 編輯基本資料
    # =========================
    st.markdown("### 基本資料")
    col1, col2, col3 = st.columns(3)
    with col1:
        customer = st.text_input("Customer", value=row.get("Customer", ""), key="edit_customer")
    with col2:
        color_name = st.text_input("ColorName", value=row.get("ColorName", ""), key="edit_color_name")
    with col3:
        pantone = st.text_input("Pantone", value=row.get("Pantone", ""), key="edit_pantone")

    col4, col5, col6 = st.columns(3)
    with col4:
        recipe_status = st.selectbox(
            "RecipeStatus",
            ["OFFICIAL", "REFERENCE", "TRIAL", "FAILED"],
            index=["OFFICIAL", "REFERENCE", "TRIAL", "FAILED"].index(
                row.get("RecipeStatus", "OFFICIAL")
            ),
            key="edit_recipe_status"
        )
    with col5:
        remark = st.text_input("Remark", value=row.get("Remark", ""), key="edit_remark")
    with col6:
        new_image = st.file_uploader("更換色板照片（選填）", type=["jpg", "jpeg", "png"],
                                     key=f"edit_image_{board_id}")

    st.markdown('### 調整色板照片')
    photo_key = f'edit_board_photo_{board_id}'
    photo_source = new_image
    if photo_source is None:
        try:
            if row.get('ImageBase64'):
                photo_source = io.BytesIO(base64.b64decode(row['ImageBase64']))
            elif row.get('ImagePath'):
                local_photo = resolve_local_image_path(row['ImagePath'])
                if local_photo.is_file():
                    photo_source = io.BytesIO(local_photo.read_bytes())
        except (ValueError, OSError) as error:
            st.warning(f'無法載入現有照片，請上傳新照片：{error}')
    if photo_source is None:
        st.info('目前沒有可編輯的照片，可先上傳更換色板照片。')
    edited_photo = render_photo_editor(photo_source, key=photo_key, allow_crop=True)
    image_changed = new_image is not None or photo_is_modified(photo_key)

    # =========================
    # 客戶樣品留存
    # =========================
    sample_changes = []
    invalid_sample = False
    with st.expander("客戶樣品留存（選填）", expanded=False):
        st.caption("可補上或更換任一張照片，未更換的照片會保留。")
        sample_columns = st.columns(2)
        for sample_index, column in enumerate(sample_columns, start=1):
            with column:
                sample_upload = st.file_uploader(
                    f'上傳／更換樣品照 {sample_index}', type=['jpg', 'jpeg', 'png'],
                    key=f'edit_sample_upload_{board_id}_{sample_index}',
                )
                sample_bytes = render_photo_editor(
                    sample_upload, key=f'edit_sample_photo_{board_id}_{sample_index}',
                    allow_crop=True,
                )
                if sample_upload is not None:
                    if sample_bytes is None:
                        invalid_sample = True
                    else:
                        sample_changes.append((sample_index, sample_bytes))
                    continue
                sample_b64 = row.get(f'SampleImage{sample_index}Base64', '') or ''
                if sample_b64:
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
                    st.info(f"尚未留存客戶樣品照 {sample_index}")
        sample_description = st.text_area(
            '樣品說明', value=row.get('SampleDescription', '') or '',
            key=f'edit_sample_description_{board_id}', height=100,
        )

    # =========================
    # 配方資料
    # =========================
    with st.expander("配方資料（選填）", expanded=False):
        try:
            existing_formula = lookup_formula_by_id(str(row.get("FormulaID", "")))
        except Exception:
            existing_formula = []
            st.warning("色板已載入，但目前無法從配方表載入色粉明細。")
        f = existing_formula[0] if existing_formula else {}

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            add_ratio = st.number_input("添加比例 (g/kg)", value=float(f.get("AddRatio") or 0), step=0.1, format="%.1f", key="edit_add_ratio")
        with col_b:
            net_weight = st.number_input("淨重 (g)", value=float(f.get("NetWeight") or 0), step=0.1, format="%.1f", key="edit_net_weight")
        with col_c:
            total_type_options = ["", "LA", "MA", "S", "CA", "T9", "其他"]
            total_type_val = f.get("TotalType", "")
            total_type_idx = total_type_options.index(total_type_val) if total_type_val in total_type_options else 0
            total_type = st.selectbox("合計類別", total_type_options, index=total_type_idx, key="edit_total_type")

        st.markdown("**色粉資料**")
        pigments = []
        weights = []

        cols_p = st.columns(4)
        for i in range(4):
            with cols_p[i]:
                p = st.text_input(f"色粉編號 {i+1}", value=str(f.get(f"Pigment{i+1}") or ""), key=f"edit_pigment_{i+1}")
                pigments.append(p)

        cols_w = st.columns(4)
        for i in range(4):
            with cols_w[i]:
                w = st.number_input(f"重量 {i+1} (g)", value=float(f.get(f"Weight{i+1}") or 0), step=0.01, format="%.2f", key=f"edit_weight_{i+1}")
                weights.append(w)

        cols_p2 = st.columns(4)
        for i in range(4, 8):
            with cols_p2[i-4]:
                p = st.text_input(f"色粉編號 {i+1}", value=str(f.get(f"Pigment{i+1}") or ""), key=f"edit_pigment_{i+1}")
                pigments.append(p)

        cols_w2 = st.columns(4)
        for i in range(4, 8):
            with cols_w2[i-4]:
                w = st.number_input(f"重量 {i+1} (g)", value=float(f.get(f"Weight{i+1}") or 0), step=0.01, format="%.2f", key=f"edit_weight_{i+1}")
                weights.append(w)

        col_r1, _ = st.columns(2)
        with col_r1:
            formula_remark = st.text_input("配方備註", value=f.get("Remark", ""), key="edit_formula_remark")

    # =========================
    # 儲存
    # =========================
    if st.button("儲存更新", disabled=(photo_source is not None and edited_photo is None) or invalid_sample):
        now = datetime.now().strftime("%Y/%m/%d %H:%M")
        try:
            updates = {
                "Customer": customer,
                "ColorName": color_name,
                "Pantone": pantone,
                "RecipeStatus": recipe_status,
                "Remark": remark,
                "LastUpdate": now,
            }

            # 更換圖片
            if image_changed:
                image_path = build_image_path(row.get('Material', ''), board_id, '.png')
                image_path, image_base64 = write_uploaded_bytes_get_base64(edited_photo, image_path)
                updates["ImagePath"] = image_path
                updates["ImageBase64"] = image_base64
                updates["EmbeddingStatus"] = "PROCESSING"

            for sample_index, sample_bytes in sample_changes:
                sample_path = build_sample_image_path(
                    row.get('Material', ''), board_id, sample_index, '.png',
                )
                sample_path, sample_base64 = write_uploaded_bytes_get_base64(sample_bytes, sample_path)
                sample_local_path = resolve_local_image_path(sample_path)
                if not sample_local_path.is_file() or sample_local_path.stat().st_size == 0:
                    raise ValueError(f'客戶樣品照 {sample_index} 寫入失敗')
                updates[f'SampleImage{sample_index}Path'] = sample_path
                updates[f'SampleImage{sample_index}Base64'] = sample_base64
            if sample_description != (row.get('SampleDescription', '') or ''):
                updates['SampleDescription'] = sample_description

            update_color_match_board(board_id, updates)

            # 配方
            has_formula = any(p.strip() for p in pigments)
            formula_id = str(row.get("FormulaID", "")).strip()
            if has_formula and formula_id:
                formula_row = {
                    "FormulaID": formula_id,
                    "ColorName": color_name,
                    "Customer": customer,
                    "Pantone": pantone,
                    "AddRatio": add_ratio if add_ratio > 0 else "",
                    "NetWeight": net_weight if net_weight > 0 else "",
                    "Pigment1": pigments[0], "Pigment2": pigments[1],
                    "Pigment3": pigments[2], "Pigment4": pigments[3],
                    "Pigment5": pigments[4], "Pigment6": pigments[5],
                    "Pigment7": pigments[6], "Pigment8": pigments[7],
                    "Weight1": weights[0] if weights[0] > 0 else "",
                    "Weight2": weights[1] if weights[1] > 0 else "",
                    "Weight3": weights[2] if weights[2] > 0 else "",
                    "Weight4": weights[3] if weights[3] > 0 else "",
                    "Weight5": weights[4] if weights[4] > 0 else "",
                    "Weight6": weights[5] if weights[5] > 0 else "",
                    "Weight7": weights[6] if weights[6] > 0 else "",
                    "Weight8": weights[7] if weights[7] > 0 else "",
                    "TotalType": total_type,
                    "Remark": formula_remark,
                }
                append_formula_row(formula_row)

            # 重建向量（圖片更換時）
            if image_changed:
                local_path = resolve_local_image_path(updates['ImagePath'])
                embedding = embed_image(local_path)
                upsert_embedding(
                    row.get("Material", ""),
                    {
                        "id": board_id,
                        "image_path": updates['ImagePath'],
                        "formula_id": formula_id,
                        "recipe_status": recipe_status,
                    },
                    embedding,
                    now
                )
                update_color_match_board(
                    board_id,
                    {"EmbeddingStatus": "Y", "LastUpdate": now},
                )

            st.success("更新完成")
            st.session_state.pop("edit_target", None)
            st.session_state.pop("edit_targets", None)

        except Exception as e:
            import traceback
            st.error(f"ERROR: {str(e)}")
            st.code(traceback.format_exc())
