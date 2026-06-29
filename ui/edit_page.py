import streamlit as st
from datetime import datetime
from services.google_sheet import (
    get_colorboard_by_id,
    get_colorboards_by_formula_id,
    update_colorboard_row,
    append_formula_row,
    lookup_formula_by_id,
)
from services.embedding_service import embed_image, upsert_embedding
from services.google_drive import write_uploaded_bytes_get_base64, resolve_local_image_path
import base64
import io
from PIL import Image


def _base64_to_image(b64: str):
    try:
        return Image.open(io.BytesIO(base64.b64decode(b64)))
    except Exception:
        return None


def render_edit_page():
    st.markdown(
        "<h2 style='font-size: 24px; font-weight: bold;'>修改色板資料</h2>",
        unsafe_allow_html=True
    )

    # =========================
    # 查詢
    # =========================
    search_formula = st.text_input("輸入 FormulaID", placeholder="例如：52824")

    if st.button("🔍 查詢"):
        st.session_state.pop("edit_target", None)
        st.session_state.pop("edit_targets", None)
        if search_formula.strip():
            rows = get_colorboards_by_formula_id(search_formula.strip())
            if rows:
                st.session_state["edit_targets"] = rows
                st.session_state["edit_target"] = rows[0]
            else:
                st.error(f"找不到 FormulaID：{search_formula}")
        else:
            st.warning("請輸入 FormulaID")

    # 如果 FormulaID 查到多筆，讓使用者選
    if "edit_targets" in st.session_state and len(st.session_state["edit_targets"]) > 1:
        targets = st.session_state["edit_targets"]
        options = [r["ID"] for r in targets]
        selected = st.selectbox("找到多筆，請選擇要編輯的 ID", options)
        for r in targets:
            if r["ID"] == selected:
                st.session_state["edit_target"] = r
                break

    if "edit_target" not in st.session_state:
        return

    row = st.session_state["edit_target"]
    board_id = row["ID"]
    st.success(f"✅ 已載入：{board_id}")

    # =========================
    # 現有圖片
    # =========================
    b64 = row.get("ImageBase64", "")
    if b64:
        img = _base64_to_image(b64)
        if img:
            st.image(img, width=200, caption="目前圖片")

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
        new_image = st.file_uploader("更換圖片（選填）", type=["jpg", "jpeg", "png"], key="edit_image")

    # =========================
    # 配方資料
    # =========================
    st.markdown("### 🧪 配方資料（選填）")
    existing_formula = lookup_formula_by_id(str(row.get("FormulaID", "")))
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
    if st.button("💾 儲存更新"):
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
            if new_image:
                content = new_image.getvalue()
                image_path = row.get("ImagePath", "")
                _, image_base64 = write_uploaded_bytes_get_base64(content, image_path)
                updates["ImageBase64"] = image_base64
                updates["EmbeddingStatus"] = "PROCESSING"

            update_colorboard_row(board_id, updates)

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
            if new_image:
                local_path = resolve_local_image_path(row.get("ImagePath", ""))
                embedding = embed_image(local_path)
                upsert_embedding(
                    row.get("Material", ""),
                    {
                        "id": board_id,
                        "image_path": row.get("ImagePath", ""),
                        "formula_id": formula_id,
                        "recipe_status": recipe_status,
                    },
                    embedding,
                    now
                )
                update_colorboard_row(board_id, {"EmbeddingStatus": "Y", "LastUpdate": now})

            st.success("✅ 更新完成！")
            st.session_state.pop("edit_target", None)
            st.session_state.pop("edit_targets", None)

        except Exception as e:
            import traceback
            st.error(f"❌ ERROR: {str(e)}")
            st.code(traceback.format_exc())
