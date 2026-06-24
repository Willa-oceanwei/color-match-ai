from pathlib import Path
import streamlit as st

from ui.result_components import render_result_card
from services.search_service import search_top_k


def render_search_page():

    st.title("相近色板比對")

    # =====================
    # INPUT
    # =====================

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

    # =====================
    # SEARCH BUTTON
    # =====================

    if st.button("🔍 Start Matching", disabled=uploaded is None):

        try:
            # Step 1: save temp image
            tmp_path = Path("tmp/query.jpg")
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_bytes(uploaded.getvalue())

            # Step 2: search
            with st.spinner("AI Matching..."):

                results = search_top_k(material, tmp_path, top_k=5)

            # Step 3: render
            if not results:
                st.warning("No data found")

            else:
                for i, r in enumerate(results, 1):
                    render_result_card(i, r)

        except Exception as e:
            st.error(f"Search error: {e}")
