from datetime import datetime
from pathlib import Path

import streamlit as st

from services.google_drive import resolve_local_image_path, write_uploaded_bytes_get_base64
from services.id_utils import build_sample_image_path
from services.turso_db import search_color_match_boards, update_color_match_sample_archive
from ui.board_search_page import _render_image
from ui.design import render_page_header


def render_sample_archive_page():
    render_page_header(
        "SAMPLE ARCHIVE",
        "樣品留存",
        "先確認正確的歷史色板，再補登或更換客戶樣品照片。",
    )
    keyword = st.text_input(
        "搜尋配方編號、客戶、顏色名稱、Pantone 或色板 ID",
        key="sample_archive_query",
    )
    if st.button("搜尋色板", key="sample_archive_search"):
        if not keyword.strip():
            st.warning("請輸入搜尋條件")
            st.session_state.pop("sample_archive_results", None)
        else:
            try:
                st.session_state["sample_archive_results"] = search_color_match_boards(keyword)
            except Exception as error:
                st.error("無法讀取色板資料庫")
                st.caption(f"診斷訊息：{error}")
                st.session_state.pop("sample_archive_results", None)

    if "sample_archive_results" not in st.session_state:
        return
    rows = st.session_state["sample_archive_results"]
    if not rows:
        st.info("找不到符合條件的色板")
        return

    labels = [
        f"{row.get('FormulaID', '') or row.get('ID', '')} | "
        f"{row.get('Customer', '') or '未填客戶'} | "
        f"{row.get('ColorName', '') or '未填顏色'} | "
        f"{row.get('Material', '')} | {row.get('Pantone', '') or '未填 Pantone'}"
        for row in rows
    ]
    selected = rows[labels.index(st.selectbox("選擇正確的 Color Board", labels))]

    st.markdown("### 目前選擇的色板")
    fields = [
        ("配方編號", selected.get("FormulaID", "")),
        ("客戶", selected.get("Customer", "")),
        ("材質", selected.get("Material", "")),
        ("顏色", selected.get("ColorName", "")),
        ("Pantone", selected.get("Pantone", "")),
        ("建立日期", selected.get("CreateDate", "")),
        ("Board ID", selected.get("ID", "")),
    ]
    columns = st.columns(4)
    for index, (label, value) in enumerate(fields):
        with columns[index % 4]:
            st.caption(label)
            st.write(value or "—")
    st.markdown("**歷史色板照片**")
    _render_image(selected.get("ImageBase64", "") or "", "無色板照片", "色板照片")

    st.markdown("### 客戶樣品留存")
    sample_columns = st.columns(2)
    uploads = []
    for index, column in enumerate(sample_columns, start=1):
        with column:
            _render_image(
                selected.get(f"SampleImage{index}Base64", "") or "",
                f"尚未留存客戶樣品照 {index}",
                f"客戶樣品照 {index}",
            )
            uploads.append(st.file_uploader(
                f"上傳 / 更換客戶樣品照 {index}",
                type=["jpg", "jpeg", "png"],
                key=f"sample_archive_upload_{selected['ID']}_{index}",
            ))
    description = st.text_area(
        "樣品說明",
        value=selected.get("SampleDescription", "") or "",
        height=100,
        key=f"sample_archive_description_{selected['ID']}",
    )

    if st.button("儲存樣品留存", key=f"sample_archive_save_{selected['ID']}"):
        updates = {
            "SampleDescription": description,
            "LastUpdate": datetime.now().strftime("%Y/%m/%d %H:%M"),
        }
        try:
            for index, upload in enumerate(uploads, start=1):
                if upload is None:
                    continue
                path = build_sample_image_path(
                    selected.get("Material", ""), selected["ID"], index,
                    Path(upload.name).suffix,
                )
                path, image_base64 = write_uploaded_bytes_get_base64(upload.getvalue(), path)
                local_path = resolve_local_image_path(path)
                if not local_path.exists() or local_path.stat().st_size == 0:
                    raise ValueError(f"客戶樣品照 {index} 寫入失敗")
                updates[f"SampleImage{index}Path"] = path
                updates[f"SampleImage{index}Base64"] = image_base64
            update_color_match_sample_archive(selected["ID"], updates)
            selected.update(updates)
            st.success("樣品留存已儲存")
        except Exception as error:
            st.error(f"樣品留存儲存失敗：{error}")
