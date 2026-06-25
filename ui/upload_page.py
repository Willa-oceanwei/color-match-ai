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
            # STEP 2 GOOGLE SHEET（核心）
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

            append_colorboard_row(row)

            # =====================
            # STEP 3 EMBEDDING (CACHE)
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

        except Exception as e:
            try:
                update_embedding_status(board_id, "FAILED", now)
            except:
                pass

            st.error(f"❌ ERROR: {str(e)}")
