import streamlit as st
from pathlib import Path
from datetime import datetime

from config import SETTINGS

from services.embedding_service import embed_image, upsert_embedding
from services.formula_service import resolve_formula_mode
from services.google_drive import write_uploaded_bytes, resolve_local_image_path
from services.google_sheet import append_colorboard_row, update_embedding_status
from services.id_utils import build_board_id, build_image_path, normalize_material


# =========================
# CACHE (加速 embedding)
# =========================
_embedding_cache = {}


def get_cached_embedding(material, path, fn):
    key = f"{material}:{path}"
    if key in _embedding_cache:
        return _embedding_cache[key]
    emb = fn()
    _embedding_cache[key] = emb
    return emb


# =========================
# MAIN UI
# =========================
def render_upload_page():

    st.markdown(
        "<h2 style='font-size: 24px; font-weight: bold;'>上傳色板資料庫</h2>",
        unsafe_allow_html=True
    )

    # =========================
    # INPUT
    # =========================
    material = st.selectbox(
        "Material",
        ["PP", "ABS", "TPR", "NY", "PC", "PE", "PVC", "PS", "OTHER"]
    )

    formula_id = st.text_input("FormulaID")
    customer = st.text_input("Customer")
    color_name = st.text_input("ColorName")
    pantone = st.text_input("Pantone")
    remark = st.text_area("Remark")

    # =========================
    # 配方輸入（選填）
    # =========================
    with st.expander("🧪 輸入配方資料（選填）"):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            add_ratio = st.number_input("添加比例 (g/kg)", min_value=0.0, step=0.1, format="%.1f")
        with col_b:
            net_weight = st.number_input("淨重 (g)", min_value=0.0, step=0.1, format="%.1f")
        with col_c:
            total_type = st.selectbox(
                "合計類別",
                ["", "LA", "MA", "S", "CA", "T9", "其他"]
            )

        st.markdown("**色粉資料**")

        # 色粉編號：每列4個
        pigments = []
        weights = []

        cols_p = st.columns(4)
        for i in range(4):
            with cols_p[i]:
                p = st.text_input(f"色粉編號 {i+1}", key=f"pigment_{i+1}")
                pigments.append(p)

        cols_w = st.columns(4)
        for i in range(4):
            with cols_w[i]:
                w = st.number_input(f"重量 {i+1} (g)", min_value=0.0, step=0.01, format="%.2f", key=f"weight_{i+1}")
                weights.append(w)

        cols_p2 = st.columns(4)
        for i in range(4, 8):
            with cols_p2[i-4]:
                p = st.text_input(f"色粉編號 {i+1}", key=f"pigment_{i+1}")
                pigments.append(p)

        cols_w2 = st.columns(4)
        for i in range(4, 8):
            with cols_w2[i-4]:
                w = st.number_input(f"重量 {i+1} (g)", min_value=0.0, step=0.01, format="%.2f", key=f"weight_{i+1}")
                weights.append(w)

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            formula_remark = st.text_input("配方備註", key="formula_remark")

    uploaded = st.file_uploader("上傳色板照片", type=["jpg", "jpeg", "png"])

    recipe_status = st.selectbox(
        "RecipeStatus",
        ["OFFICIAL", "REFERENCE", "TRIAL", "FAILED"],
        index=0
    )

    uploaded_bytes = uploaded.getvalue() if uploaded else None

    # =========================
    # ID
    # =========================
    board_id = build_board_id(material, formula_id or None)
    extension = Path(uploaded.name).suffix if uploaded else ".jpg"
    image_path = build_image_path(material, board_id, extension)

    st.info(f"ID: {board_id}\nPath: {image_path}")

    # =========================
    # BUTTON
    # =========================
    if st.button("🚀 儲存並建立向量", disabled=uploaded is None):
        if not uploaded_bytes:
            st.error("No image")
            return

        if st.session_state.get("last_uploaded_id") == board_id:
            st.warning("⚠️ 已上傳過，請勿重複送出")
            return

        now = datetime.now().strftime("%Y/%m/%d %H:%M")
        create_date = datetime.now().strftime("%Y/%m/%d")

        try:
            # =====================
            # STEP 1 IMAGE
            # =====================
            from services.google_drive import write_uploaded_bytes_get_base64
            image_path, image_base64 = write_uploaded_bytes_get_base64(uploaded_bytes, image_path)
            image_full_path = SETTINGS.local_drive_root / image_path
            if not image_full_path.exists() or image_full_path.stat().st_size == 0:
                raise ValueError("Image write failed")

            # =====================
            # STEP 2 GOOGLE SHEET
            # =====================
            formula_mode = resolve_formula_mode(formula_id)
            row = {
                "ID": board_id,
                "FormulaID": formula_id.strip(),
                "Material": normalize_material(material),
                "ImagePath": image_path,
                "FormulaMode": str(formula_mode),
                "RecipeStatus": recipe_status,
                "EmbeddingStatus": "PROCESSING",
                "Customer": customer,
                "ColorName": color_name,
                "Pantone": pantone,
                "CreateDate": create_date,
                "LastUpdate": now,
                "Remark": remark,
                "ImageBase64": image_base64,
            }
            append_colorboard_row(row)

            # =====================
            # STEP 2b FORMULA（選填）
            # =====================
            has_formula = any(p.strip() for p in pigments)
            if has_formula and formula_id.strip():
                from services.google_sheet import append_formula_row
                formula_row = {
                    "FormulaID": formula_id.strip(),
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

            # =====================
            # STEP 3 EMBEDDING
            # =====================
            local_path = resolve_local_image_path(image_path)
            embedding = get_cached_embedding(
                material,
                image_path,
                lambda: embed_image(local_path)
            )
            upsert_embedding(material, {
                "id": board_id,
                "image_path": image_path,
                "formula_id": formula_id.strip(),
                "recipe_status": recipe_status
            }, embedding, now)

            update_embedding_status(board_id, "Y", now)

            # =====================
            # DONE
            # =====================
            st.success("✅ 上傳完成（Google Sheet + Vector + Image）")
            st.session_state["last_uploaded_id"] = board_id

        except Exception as e:
            import traceback
            st.error(f"❌ ERROR: {str(e)}")
            st.code(traceback.format_exc())
            try:
                update_embedding_status(board_id, "FAILED", now)
            except Exception as e2:
                st.error(f"update status failed: {e2}")
