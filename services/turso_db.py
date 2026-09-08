import streamlit as st
import libsql


def get_turso_client():
    url = st.secrets["TURSO_DATABASE_URL"]
    auth_token = st.secrets["TURSO_AUTH_TOKEN"]

    return libsql.connect(
        "color_match_local.db",
        sync_url=url,
        auth_token=auth_token,
    )


def init_color_match_tables():
    conn = get_turso_client()

    conn.execute("""
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

    conn.commit()
    conn.sync()
    conn.close()


def append_color_match_board(row: dict):
    conn = get_turso_client()

    conn.execute(
        """
        INSERT INTO color_match_boards (
            id,
            material,
            image_path,
            formula_id,
            formula_mode,
            recipe_status,
            embedding_status,
            customer,
            color_name,
            pantone,
            create_date,
            last_update,
            remark,
            image_base64
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.get("ID", ""),
            row.get("Material", ""),
            row.get("ImagePath", ""),
            row.get("FormulaID", ""),
            row.get("FormulaMode", ""),
            row.get("RecipeStatus", ""),
            row.get("EmbeddingStatus", ""),
            row.get("Customer", ""),
            row.get("ColorName", ""),
            row.get("Pantone", ""),
            row.get("CreateDate", ""),
            row.get("LastUpdate", ""),
            row.get("Remark", ""),
            row.get("ImageBase64", ""),
        ),
    )

    conn.commit()
    conn.sync()
    conn.close()


def update_color_match_embedding_status(
    board_id: str,
    status: str,
    last_update: str
):
    conn = get_turso_client()

    conn.execute(
        """
        UPDATE color_match_boards
        SET embedding_status = ?,
            last_update = ?
        WHERE id = ?
        """,
        (
            status,
            last_update,
            board_id,
        ),
    )

    conn.commit()
    conn.sync()
    conn.close()
