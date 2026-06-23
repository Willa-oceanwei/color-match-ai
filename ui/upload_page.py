from datetime import datetime
from pathlib import Path
import streamlit as st
from PIL import Image

from services.embedding_service import embed_image, upsert_embedding
from services.formula_service import resolve_formula_mode
from services.google_drive import write_uploaded_bytes, resolve_local_image_path
from services.google_sheet import append_colorboard_row, update_embedding_status
from services.id_utils import build_board_id, build_image_path, normalize_material


def render_upload_page() -> None:
    st.header("🎨 上傳色板資料庫")

    # =========================
    # 1️⃣ Material（下拉選單）
    # =========================
    material = st.selectbox(
        "Material（原料）",
        ["PP", "ABS", "TPR", "NY", "PC", "PE", "PVC", "PS", "OTHER"]
    )

    formula_id = st.text_input("FormulaID（可空白）")
    customer = st.text_input("Customer")
    color_name = st.text_input("ColorName")
    pantone = st.text_input("Pantone")
    remark = st.text_area("Remark")

    uploaded = st.file_uploader("上傳色板照片", type=["jpg", "jpeg", "png"])

    # =========================
    # 2️⃣ RecipeStatus（含說明）
    # =========================
    recipe_status_label = st.selectbox(
        "RecipeStatus（配方狀態）",
        [
            "OFFICIAL - 已量產/穩定配方",
            "TRIAL - 試樣/客戶測試中",
            "FAILED - 已淘汰配方",
            "REFERENCE - 僅供比對參考"
        ],
        index=0
    )

    # 轉回簡碼
    recipe_status = recipe_status_label.split(" - ")[0]

    # =========================
    # 3️⃣ 預覽圖片
    # =========================
    if uploaded:
        st.image(Image.open(uploaded), caption="上傳預覽", width=260)

    # =========================
    # 4️⃣ ID & 檔名規則
    # =========================
    board_id = build_board_id(material, formula_id or None)
    extension = Path(uploaded.name).suffix if uploaded else ".jpg"

    # 固定檔名規則：Material_FormulaID.jpg
    image_filename = f"{material}_{board_id}{extension}"
    image_path = build_image_path(material, image_filename, extension)

    resolution = resolve_formula_mode(formula_id)

    st.info(
        f"📌 ID: {board_id} | 檔名: {image_filename} | Path: {image_path} | Mode: {resolution.formula_mode}"
    )

    # =========================
    # 5️⃣ 儲存流程
    # =========================
    if st.button("🚀 儲存並建立向量", type="primary", disabled=uploaded is None):

        try:
            now = datetime.now().strftime("%Y/%m/%d %H:%M")
            create_date = datetime.now().strftime("%Y/%m/%d")

            # Step 1：存圖片
            st.info("📦 Step 1/3：儲存圖片中...")
            write_uploaded_bytes(uploaded.getvalue(), image_path)

            # Step 2：寫 Google Sheet
            st.info("🧾 Step 2/3：寫入 ColorBoard...")

            row = {
                "ID": board_id,
                "Material": normalize_material(material),
                "ImagePath": image_path,
                "FormulaID": formula_id.strip(),
                "FormulaMode": resolution.formula_mode,
                "RecipeStatus": recipe_status,
                "EmbeddingStatus": "N",
                "Customer": customer,
                "ColorName": color_name,
                "Pantone": pantone,
                "CreateDate": create_date,
                "LastUpdate": now,
                "Remark": remark,
            }

            append_colorboard_row(row)

            # Step 3：Embedding
            st.info("🧠 Step 3/3：建立向量中...")

            local_path = resolve_local_image_path(image_path)
            embedding = embed_image(local_path)

            upsert_embedding(
                row["Material"],
                {
                    "id": board_id,
                    "image_path": image_path,
                    "formula_id": formula_id.strip(),
                    "recipe_status": recipe_status,
                },
                embedding,
                now,
            )

            update_embedding_status(board_id, "Y", now)

            st.success("✅ 色板建立完成（圖片 + 資料 + 向量）")

        except Exception as e:
            st.error(f"❌ 建立失敗：{str(e)}")
