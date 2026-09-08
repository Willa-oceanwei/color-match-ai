import streamlit as st
from libsql_client import create_client_sync


def get_turso_client():
    url = st.secrets["TURSO_DATABASE_URL"]
    auth_token = st.secrets["TURSO_AUTH_TOKEN"]

    return create_client_sync(
        url=url,
        auth_token=auth_token,
    )


def init_color_match_tables():
    client = get_turso_client()

    client.execute("""
        CREATE TABLE IF NOT EXISTS color_match_boards (
            id TEXT PRIMARY KEY,
            material TEXT,
            image_path TEXT,
            formula_id TEXT,
            formula_mode TEXT,
            recipe_status TEXT,
            embedding_status TEXT,
            customer TEXT,
            color_name TEXT,
            pantone TEXT,
            create_date TEXT,
            last_update TEXT,
            remark TEXT,
            image_base64 TEXT
        )
    """)

    client.close()
