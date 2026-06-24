from pathlib import Path
import streamlit as st
from ui.result_components import render_result_card
from services.search_service import search_top_k


def render_search_page():

    st.title("🎨 Color Matching AI (Factory V3)")

    material = st.selectbox(
        "Material",
        ["PP", "ABS", "TPR", "NY", "PC", "PE", "PVC", "PS"]
    )

    uploaded = st.file_uploader(
        "上傳樣品",
        type=["jpg", "png", "jpeg"]
    )

    if uploaded:
        st.image(uploaded, caption="Query Sample")

    if st.button("🔍 Start Matching", disabled=uploaded is None):

        tmp_path = Path("tmp/query.jpg")
        tmp_path.parent.mkdir(exist_ok=True)
        tmp_path.write_bytes(uploaded.getvalue())

        with st.spinner("AI Matching..."):

            results = search_top_k(material, tmp_path, top_k=5)

        if not results:
            st.warning("No data")

        else:
            for i, r in enumerate(results, 1):
                render_result_card(i, r)
