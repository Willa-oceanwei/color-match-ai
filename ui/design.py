import streamlit as st
from decimal import Decimal, InvalidOperation


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


def format_quantity(value):
    """Format numeric quantities without a meaningless trailing decimal zero."""
    if value in (None, ""):
        return ""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    if number == number.to_integral():
        return str(int(number))
    return format(number.normalize(), "f")
