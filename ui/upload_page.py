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
    st.header("上傳色板")
    material = st.text_input("Material", value="ABS")
    formula_id = st.text_input("FormulaID（可空白）")
    customer = st.text_input("Customer")
    color_name = st.text_input("ColorName")
    pantone = st.text_input("Pantone")
    remark = st.text_area("Remark")
    uploaded = st.file_uploader("上傳色板照片", type=["jpg", "jpeg", "png"])

    resolution = resolve_formula_mode(formula_id)
    recipe_status = st.selectbox(
        "RecipeStatus",
        ["OFFICIAL", "TRIAL", "FAILED", "REFERENCE"],
        index=0 if resolution.recipe_status == "OFFICIAL" else 1,
    )
    board_id = build_board_id(material, formula_id or None)
    extension = Path(uploaded.name).suffix if uploaded else ".jpg"
    image_path = build_image_path(material, board_id, extension)

    st.info(f"預覽：ID={board_id}，ImagePath={image_path}，FormulaMode={resolution.formula_mode}")

    if uploaded:
        st.image(Image.open(uploaded), caption="上傳預覽", width=260)

    if st.button("儲存並建立向量", type="primary", disabled=uploaded is None):
        now = datetime.now().strftime("%Y/%m/%d %H:%M")
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
        append_colorboard_row(row)
        local_path = resolve_local_image_path(image_path)
        embedding = embed_image(local_path)
        upsert_embedding(row["Material"], {
            "id": board_id,
            "image_path": image_path,
            "formula_id": formula_id.strip(),
            "recipe_status": recipe_status,
        }, embedding, now)
        update_embedding_status(board_id, "Y", now)
        st.success("色板已寫入 ColorBoard，並完成向量建立。")
