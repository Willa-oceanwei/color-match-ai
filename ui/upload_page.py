import streamlit as st
from pathlib import Path
from datetime import datetime
import os

from config import SETTINGS

from services.embedding_service import embed_image, upsert_embedding
from services.formula_service import resolve_formula_mode

from services.google_drive import (
    write_uploaded_bytes,
    resolve_local_image_path
)

from services.google_sheet import (
    append_colorboard_row,
    update_embedding_status
)

from services.id_utils import (
    build_board_id,
    build_image_path,
    normalize_material
)


def render_upload_page():

    st.markdown(
        "<h2 style='font-size: 24px; font-weight: bold;'>上傳色板資料庫</h2>",
        unsafe_allow_html=True
    )

    import os
    from pathlib import Path
    from datetime import datetime

    # =========================
    # Material
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

    uploaded = st.file_uploader(
        "上傳色板照片",
        type=["jpg", "jpeg", "png"]
    )

    recipe_status_label = st.selectbox(
        "RecipeStatus",
        [
            "OFFICIAL - 已正式量產",
            "REFERENCE - 有配方但未正式管理",
            "TRIAL - 留樣測試",
            "FAILED - 已淘汰"
        ],
        index=0
    )

    recipe_status = recipe_status_label.split(" - ")[0]

    # =========================
    # DEBUG SYSTEM
    # =========================
    st.write("🔥 CWD =", os.getcwd())
    st.write("🔥 CSV Path =", SETTINGS.colorboard_csv_path)
    st.write("🔥 Vector Dir =", SETTINGS.vector_dir)

    uploaded_bytes = None

    # =========================
    # FILE PREVIEW
    # =========================
    if uploaded:
        uploaded_bytes = uploaded.getvalue()

        st.image(uploaded_bytes, caption="上傳預覽", width=260)
        st.write("UPLOAD SIZE =", len(uploaded_bytes))

    # =========================
    # ID
    # =========================
    board_id = build_board_id(material, formula_id or None)

    extension = Path(uploaded.name).suffix if uploaded else ".jpg"

    image_filename = f"{board_id}{extension}"

    image_path = build_image_path(material, board_id, extension)

    st.info(f"""
📌 ID：{board_id}
📁 檔名：{image_filename}
🖼 Path：{image_path}
""")

    # =========================
    # BUTTON
    # =========================
    if st.button("🚀 儲存並建立向量", type="primary", disabled=uploaded is None):

        st.write("👉 STEP CHECK: BUTTON CLICKED")

        if not uploaded_bytes:
            st.error("❌ uploaded_bytes is None")
            return

        now = datetime.now().strftime("%Y/%m/%d %H:%M")
        create_date = datetime.now().strftime("%Y/%m/%d")

        try:

            # =====================
            # STEP 1: SAVE IMAGE
            # =====================
            st.info("📦 Step 1/3 儲存圖片...")

            write_uploaded_bytes(uploaded_bytes, image_path)

            real_path = SETTINGS.local_drive_root / image_path

            st.write("IMAGE EXISTS =", real_path.exists())
            st.write("IMAGE SIZE =", real_path.stat().st_size if real_path.exists() else None)

            if not real_path.exists() or real_path.stat().st_size == 0:
                raise ValueError("圖片寫入失敗")

            st.write("👉 AFTER IMAGE SAVE OK")

            # =====================
            # STEP 2: CSV
            # =====================
            st.info("🧾 Step 2/3 寫入 ColorBoard...")

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
                "Remark": remark
            }

            st.write("👉 BEFORE CSV APPEND")
            append_colorboard_row(row)
            st.write("👉 AFTER CSV APPEND")

            st.write("DEBUG ROW =", row)

            # =====================
            # STEP 3: EMBEDDING
            # =====================
            st.info("🧠 Step 3/3 建立向量...")

            local_path = resolve_local_image_path(image_path)

            st.write("LOCAL PATH =", local_path)
            st.write("LOCAL EXISTS =", Path(local_path).exists())

            st.write("👉 BEFORE EMBEDDING")
            st.write("🔥 LOCAL PATH TYPE =", type(local_path))
            st.write("🔥 LOCAL PATH VALUE =", local_path)

            try:
                embedding = embed_image(local_path)
            except Exception as e:
                st.error("❌ EMBEDDING ERROR")
                st.exception(e)
                raise
                
            st.write("👉 AFTER EMBEDDING")

            st.write("EMBEDDING TYPE =", type(embedding))
            st.write("EMBEDDING LENGTH =", len(embedding) if embedding is not None else None)

            st.write("👉 BEFORE UPSERT")

            upsert_embedding(
                material,
                {
                    "id": board_id,
                    "image_path": image_path,
                    "formula_id": formula_id.strip(),
                    "recipe_status": recipe_status
                },
                embedding,
                now
            )

            st.write("👉 AFTER UPSERT")

            update_embedding_status(board_id, "Y", now)

            # =========================
            # FINAL VERIFICATION (100%)
            # =========================
            st.write("🔥 FINAL VERIFICATION START")
            
            csv_path = SETTINGS.colorboard_csv_path
            vector_path = SETTINGS.vector_dir / f"{material.upper()}_vectors.pkl"
            image_path_abs = SETTINGS.local_drive_root / image_path
            
            st.write("📄 CSV EXISTS =", csv_path.exists())
            st.write("📄 CSV PATH =", csv_path.resolve())
            
            st.write("🧠 VECTOR EXISTS =", vector_path.exists())
            st.write("🧠 VECTOR PATH =", vector_path.resolve())
            
            st.write("🖼 IMAGE EXISTS =", image_path_abs.exists())
            st.write("🖼 IMAGE SIZE =", image_path_abs.stat().st_size if image_path_abs.exists() else None)
            
            st.write("🔥 FINAL VERIFICATION DONE")
            st.success("✅ 色板建立完成（圖片 + 資料 + 向量）")
            
        except Exception as e:

            try:
                update_embedding_status(board_id, "FAILED", now)
            except:
                pass

            st.error(f"❌ 建立失敗：{str(e)}")
