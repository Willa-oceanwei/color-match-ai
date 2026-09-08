import streamlit as st


def render_page_header(icon: str, eyebrow: str, title: str, description: str):
    st.markdown(
        f"""
        <div class="page-hero">
            <div class="page-icon">{icon}</div>
            <div>
                <div class="page-eyebrow">{eyebrow}</div>
                <div class="page-title">{title}</div>
                <div class="page-description">{description}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
