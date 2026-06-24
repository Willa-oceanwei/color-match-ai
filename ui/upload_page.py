from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image

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
    "<h2 style='font-size: 24px; font-weight: bold; color: #333333;'>上傳色板資料庫</h2>", 
    unsafe_allow_html=True
    )

    # =========================
    # Material
    # =========================

    material = st.selectbox(
        "Material（原料）",
        [
            "PP",
            "ABS",
            "TPR",
            "NY",
            "PC",
            "PE",
            "PVC",
            "PS",
            "OTHER"
        ]
    )

    # =========================
    # 基本資料
    # =========================

    formula_id = st.text_input(
        "FormulaID（可空白）"
    )

    customer = st.text_input(
        "Customer"
    )

    color_name = st.text_input(
        "ColorName"
    )

    pantone = st.text_input(
        "Pantone"
    )

    remark = st.text_area(
        "Remark"
    )

    uploaded = st.file_uploader(
        "上傳色板照片",
        type=["jpg", "jpeg", "png"]
    )

    # =========================
    # Recipe Status
    # =========================

    recipe_status_label = st.selectbox(
        "RecipeStatus（配方狀態）",
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
    # FormulaMode
    # =========================

    resolution = resolve_formula_mode(formula_id)

    with st.expander("📘 狀態說明（點擊展開）"):
        st.markdown("""
    ##### 🧪 FormulaMode

    - **OFFICIAL**：已存在正式配方  
    - **REFERENCE**：有配方但未正式管理  
    - **TRIAL**：留樣無正式配方  

    ---

    ##### 🧠 EmbeddingStatus

    - **PROCESSING**：建立向量中  
    - **Y**：已建立完成  
    - **FAILED**：建立失敗  
     """)

    # =========================
    # 圖片預覽
    # =========================

    if uploaded:

        st.image(
            Image.open(uploaded),
            caption="上傳預覽",
            width=260
        )

    # =========================
    # ID
    # =========================

    board_id = build_board_id(
        material,
        formula_id or None
    )

    extension = (
        Path(uploaded.name).suffix
        if uploaded
        else ".jpg"
    )

    image_filename = f"{board_id}{extension}"

    image_path = build_image_path(
        material,
        board_id,
        extension
    )

    st.info(
        f"""
📌 ID：{board_id}

📁 檔名：{image_filename}

🖼 Path：{image_path}

📝 FormulaMode：{resolution.formula_mode}

    st.markdown("<small style='color: #666666;'>💡 備註：樣品占 60~80%；灰底占 20~40%；512*512</small>", unsafe_allow_html=True)
"""
    )

    # =========================
    # 儲存
    # =========================

    if st.button(
            "🚀 儲存並建立向量",
            type="primary",
            disabled=uploaded is None):

        now = datetime.now().strftime(
            "%Y/%m/%d %H:%M"
        )

        create_date = datetime.now().strftime(
            "%Y/%m/%d"
        )

        try:

            # Step1

            st.info(
                "📦 Step 1/3 儲存圖片..."
            )

            write_uploaded_bytes(
                uploaded.getvalue(),
                image_path
            )

            # Step2

            st.info(
                "🧾 Step 2/3 寫入 ColorBoard..."
            )

            row = {

                "ID": board_id,

                "FormulaID":
                formula_id.strip(),

                "Material":
                normalize_material(material),

                "ImagePath":
                image_path,

                "FormulaMode":
                resolution.formula_mode,

                "RecipeStatus":
                recipe_status,

                "EmbeddingStatus":
                "PROCESSING",

                "Customer":
                customer,

                "ColorName":
                color_name,

                "Pantone":
                pantone,

                "CreateDate":
                create_date,

                "LastUpdate":
                now,

                "Remark":
                remark
            }

            append_colorboard_row(row)

            # Step3

            st.info(
                "🧠 Step 3/3 建立向量..."
            )

            local_path = resolve_local_image_path(
                image_path
            )

            embedding = embed_image(
                local_path
            )

            upsert_embedding(

                material,

                {

                    "id":
                    board_id,

                    "image_path":
                    image_path,

                    "formula_id":
                    formula_id.strip(),

                    "recipe_status":
                    recipe_status

                },

                embedding,

                now

            )

            update_embedding_status(
                board_id,
                "Y",
                now
            )

            st.success(
                "✅ 色板建立完成（圖片 + 資料 + 向量）"
            )

        except Exception as e:

            try:

                update_embedding_status(
                    board_id,
                    "FAILED",
                    now
                )

            except:
                pass

            st.error(
                f"❌ 建立失敗：{str(e)}"
            )
