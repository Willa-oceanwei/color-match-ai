import streamlit as st
from services.google_drive import resolve_local_image_path
from services.models import SearchResult


def render_result_card(rank: int, result: SearchResult) -> None:
    board = result.board
    status_label = "正式配方" if result.has_formula else "歷史案例 / 試樣"
    status_icon = "✅" if result.has_formula else "🟨"
    with st.container(border=True):
        st.subheader(f"#{rank} {board.get('ID', result.id)} — 相似度 {result.similarity:.3f}")
        image_path = board.get("ImagePath", "")
        local_image = resolve_local_image_path(image_path) if image_path else None
        if local_image and local_image.exists():
            st.image(str(local_image), caption=image_path, width=220)
        st.markdown(f"{status_icon} **{status_label}**")
        st.write({
            "Material": board.get("Material", ""),
            "FormulaID": board.get("FormulaID", ""),
            "RecipeStatus": board.get("RecipeStatus", ""),
            "Customer": board.get("Customer", ""),
            "ColorName": board.get("ColorName", ""),
            "Pantone": board.get("Pantone", ""),
            "Remark": board.get("Remark", ""),
        })
        if result.has_formula:
            st.dataframe(result.formula_rows, use_container_width=True)
        else:
            st.warning("此色板尚未存在於正式配方管理，請以歷史打樣紀錄參考。")
