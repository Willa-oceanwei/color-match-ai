import streamlit as st

from ui.edit_page import render_edit_page
from ui.sample_archive_page import render_sample_archive_page
from ui.upload_page import render_upload_page


def render_board_management_page():
    tabs = st.tabs(["新增色板", "樣品留存", "編輯色板"])
    with tabs[0]:
        render_upload_page()
    with tabs[1]:
        render_sample_archive_page()
    with tabs[2]:
        render_edit_page()
