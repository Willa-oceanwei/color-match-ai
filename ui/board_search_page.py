import base64
import io

import streamlit as st
from PIL import Image

from services import turso_db
from ui.design import render_page_header


def _base64_to_image(value: str):
    try:
        return Image.open(io.BytesIO(base64.b64decode(value)))
    except Exception:
        return None


def _render_image(value: str, empty_message: str, caption: str):
    if not value:
        st.info(empty_message)
        return
    image = _base64_to_image(value)
    if image:
        st.image(image, use_container_width=True, caption=caption)
    else:
        st.warning(f"{caption}無法顯示")


def _find_boards(filters: dict):
    """Use the filtered query, with a safe fallback for rolling deployments.

    Streamlit can briefly retain an older imported ``turso_db`` module while
    deploying the UI files. Importing the module instead of a newly added symbol
    keeps application startup available during that window.
    """
    finder = getattr(turso_db, "find_color_match_boards", None)
    if callable(finder):
        return finder(filters)

    # Compatibility path for an older in-memory service module. This is only
    # evaluated after the user submits at least one filter, never on page load.
    rows = turso_db.get_all_color_match_boards()
    matches = []
    for row in rows:
        matched = True
        for key, expected in filters.items():
            expected = str(expected or "").strip()
            if not expected:
                continue
            actual = str(row.get(key, "") or "").strip()
            if key == "Material":
                matched = actual.casefold() == expected.casefold()
            else:
                matched = expected.casefold() in actual.casefold()
            if not matched:
                break
        if matched:
            matches.append(row)
    return matches[:100]


def render_board_search_page():
    render_page_header(
        "COLOR BOARD SEARCH",
        "色板查詢",
        "依色板資料查詢歷史紀錄，選擇單筆後查看照片與完整內容。",
    )

    first_row = st.columns(3)
    with first_row[0]:
        formula_id = st.text_input("FormulaID", key="board_search_formula_id")
    with first_row[1]:
        customer = st.text_input("Customer", key="board_search_customer")
    with first_row[2]:
        color_name = st.text_input("ColorName", key="board_search_color_name")

    second_row = st.columns(3)
    with second_row[0]:
        pantone = st.text_input("Pantone", key="board_search_pantone")
    with second_row[1]:
        material = st.selectbox(
            "Material",
            ["", "PP", "ABS", "TPR", "NY", "PC", "PE", "PVC", "PS", "OTHER"],
            key="board_search_material",
        )
    with second_row[2]:
        board_id = st.text_input("Board ID", key="board_search_id")

    if st.button("查詢色板", key="board_search_submit"):
        filters = {
            "FormulaID": formula_id,
            "Customer": customer,
            "ColorName": color_name,
            "Pantone": pantone,
            "Material": material,
            "ID": board_id,
        }
        if not any(str(value).strip() for value in filters.values()):
            st.warning("請至少輸入一項搜尋條件")
            st.session_state.pop("board_search_results", None)
        else:
            try:
                st.session_state["board_search_results"] = _find_boards(filters)
            except Exception as error:
                st.error("無法讀取色板資料庫")
                st.caption(f"診斷訊息：{error}")
                st.session_state.pop("board_search_results", None)

    if "board_search_results" not in st.session_state:
        return
    rows = st.session_state["board_search_results"]
    if not rows:
        st.info("找不到符合條件的色板")
        return

    st.markdown("### 查詢結果")
    st.dataframe(
        [{
            "FormulaID": row.get("FormulaID", ""),
            "Customer": row.get("Customer", ""),
            "Material": row.get("Material", ""),
            "ColorName": row.get("ColorName", ""),
            "Pantone": row.get("Pantone", ""),
            "CreateDate": row.get("CreateDate", ""),
            "Board ID": row.get("ID", ""),
        } for row in rows],
        use_container_width=True,
        hide_index=True,
    )
    options = {
        (
            f"{row.get('FormulaID', '') or '無配方編號'} | "
            f"{row.get('Customer', '') or '未填客戶'} | "
            f"{row.get('ColorName', '') or '未填顏色'} | {row.get('ID', '')}"
        ): row
        for row in rows
    }
    selected = options[st.selectbox("選擇要查看的色板", list(options))]

    st.markdown("### 完整資料")
    detail_columns = st.columns(3)
    details = [
        ("配方編號", selected.get("FormulaID", "")),
        ("客戶", selected.get("Customer", "")),
        ("材質", selected.get("Material", "")),
        ("顏色", selected.get("ColorName", "")),
        ("Pantone", selected.get("Pantone", "")),
        ("RecipeStatus", selected.get("RecipeStatus", "")),
        ("建立日期", selected.get("CreateDate", "")),
        ("最後更新", selected.get("LastUpdate", "")),
        ("Board ID", selected.get("ID", "")),
    ]
    for index, (label, value) in enumerate(details):
        with detail_columns[index % 3]:
            st.caption(label)
            st.write(value or "—")
    st.markdown(f"**備註：** {selected.get('Remark', '') or '—'}")

    photo_columns = st.columns(2)
    with photo_columns[0]:
        st.markdown("**色板照片**")
        _render_image(selected.get("ImageBase64", "") or "", "無色板照片", "色板照片")
    with photo_columns[1]:
        st.markdown("**客戶樣品留存**")
        samples = [
            (index, selected.get(f"SampleImage{index}Base64", "") or "")
            for index in (1, 2)
        ]
        if not any(value for _, value in samples):
            st.info("尚未留存客戶樣品")
        else:
            sample_columns = st.columns(2)
            for column, (index, value) in zip(sample_columns, samples):
                with column:
                    _render_image(value, f"尚未留存客戶樣品照 {index}", f"客戶樣品照 {index}")
        st.markdown(f"**樣品說明：** {selected.get('SampleDescription', '') or '—'}")
