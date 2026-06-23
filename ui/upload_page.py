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
    st.markdown("""
        <div style="
            background: linear-gradient(135deg, #0b2f4a 0%, #0f3d5e 100%);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            padding: 18px 22px;
            margin-bottom: 20px;
        ">
            <div style="font-size:13px; color:#e06b3a; font-weight:600; letter-spacing:1px; margin-bottom:4px;">
                色板管理
            </div>
            <div style="font-size:20px; color:#ffffff; font-weight:700; margin-bottom:4px;">
                上傳色板
            </div>
            <div style="font-size:12px; color:#9fb6cc;">
                填寫色板資訊並上傳照片，系統將自動建立向量索引
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_form, col_preview = st.columns([1, 1], gap="large")

    with col_form:
        st.markdown("<div style='color:#e06b3a; font-size:10px; letter-spacing:1px; font-weight:600; margin-bottom:10px;'>基本資料</div>",
                    unsafe_allow_html=True)

        material   = st.text_input("Material", value="ABS")
        formula_id = st.text_input("FormulaID（可空白）")
        customer   = st.text_input("Customer")
        color_name = st.text_input("ColorName")
        pantone    = st.text_input("Pantone")
        remark     = st.text_area("Remark", height=80)

        st.markdown("<div style='color:#e06b3a; font-size:10px; letter-spacing:1px; font-weight:600; margin: 14px 0 10px 0;'>狀態設定</div>",
                    unsafe_allow_html=True)

        resolution = resolve_formula_mode(formula_id)
        recipe_status = st.selectbox(
            "RecipeStatus",
            ["OFFICIAL", "TRIAL", "FAILED", "REFERENCE"],
            index=0 if resolution.recipe_status == "OFFICIAL" else 1,
        )

    with col_preview:
        st.markdown("<div style='color:#e06b3a; font-size:10px; letter-spacing:1px; font-weight:600; margin-bottom:10px;'>色板照片</div>",
                    unsafe_allow_html=True)

        uploaded = st.file_uploader("上傳色板照片", type=["jpg", "jpeg", "png"])

        if uploaded:
            st.image(Image.open(uploaded), caption="上傳預覽", use_container_width=True)
        else:
            st.markdown("""
                <div style="
                    background: #111111;
                    border: 1px dashed rgba(255,255,255,0.1);
                    border-radius: 8px;
                    padding: 40px;
                    text-align: center;
                    color: #4a6070;
                    font-size: 13px;
                ">
                    尚未上傳照片
                </div>
            """, unsafe_allow_html=True)

    # ID Preview
    board_id   = build_board_id(material, formula_id or None)
    extension  = Path(uploaded.name).suffix if uploaded else ".jpg"
    image_path = build_image_path(material, board_id, extension)

    st.markdown(f"""
        <div style="
            background: #111827;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 12px 16px;
            margin: 16px 0;
            font-family: 'DM Mono', monospace;
            font-size: 12px;
            color: #9fb6cc;
            display: flex;
            gap: 24px;
        ">
            <span><span style='color:#e06b3a;'>ID</span> {board_id}</span>
            <span><span style='color:#e06b3a;'>Path</span> {image_path}</span>
            <span><span style='color:#e06b3a;'>Mode</span> {resolution.formula_mode}</span>
        </div>
    """, unsafe_allow_html=True)

    if st.button("⬆️ 儲存並建立向量", type="primary", disabled=uploaded is None):
        now         = datetime.now().strftime("%Y/%m/%d %H:%M")
        create_date = datetime.now().strftime("%Y/%m/%d")

        write_uploaded_bytes(uploaded.getvalue(), image_path)

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

        with st.spinner("寫入資料並建立向量中..."):
            append_colorboard_row(row)
            local_path = resolve_local_image_path(image_path)
            embedding  = embed_image(local_path)
            upsert_embedding(
                row["Material"],
                {"id": board_id, "image_path": image_path,
                 "formula_id": formula_id.strip(), "recipe_status": recipe_status},
                embedding, now
            )
            update_embedding_status(board_id, "Y", now)

        st.success("✅ 色板已寫入 ColorBoard，向量建立完成。")
