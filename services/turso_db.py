import streamlit as st
import libsql


COLOR_MATCH_COLUMNS = (
    "ID",
    "Material",
    "ImagePath",
    "FormulaID",
    "FormulaMode",
    "RecipeStatus",
    "EmbeddingStatus",
    "Customer",
    "ColorName",
    "Pantone",
    "CreateDate",
    "LastUpdate",
    "Remark",
    "ImageBase64",
)


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


def _rows_to_color_match_boards(rows):
    return [dict(zip(COLOR_MATCH_COLUMNS, row)) for row in rows]


def _sync_replica(conn):
    """Best-effort sync without making local reads unavailable."""
    sync = getattr(conn, "sync", None)
    if not callable(sync):
        return False

    try:
        sync()
        return True
    except Exception:
        # Turso may be temporarily unreachable during migration. The embedded
        # replica can still contain useful data, so continue with the local read.
        return False


def _read_color_match_boards(where_clause="", params=(), limit=None):
    conn = get_turso_client()
    try:
        # Pull remote writes before reading the embedded replica. This is important
        # while multiple Streamlit instances are writing to Turso. If Turso is
        # temporarily unavailable, continue with the local replica instead.
        _sync_replica(conn)

        query = """
        SELECT
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
        FROM color_match_boards
        """
        if where_clause:
            query += f" WHERE {where_clause}"
        query += " ORDER BY rowid DESC"
        query_params = list(params)
        if limit is not None:
            query += " LIMIT ?"
            query_params.append(limit)

        result = conn.execute(query, tuple(query_params))
        return _rows_to_color_match_boards(result.rows)
    finally:
        conn.close()


def get_all_color_match_boards():
    return _read_color_match_boards()


def get_color_match_boards_by_formula_id(formula_id: str):
    clean_formula_id = str(formula_id).strip()
    if not clean_formula_id:
        return []
    return _read_color_match_boards("TRIM(formula_id) = ?", (clean_formula_id,))


def get_color_match_board_by_id(board_id: str):
    clean_board_id = str(board_id).strip()
    if not clean_board_id:
        return None
    rows = _read_color_match_boards("id = ?", (clean_board_id,), limit=1)
    return rows[0] if rows else None


def get_recent_color_match_boards(limit: int = 20):
    safe_limit = max(1, min(int(limit), 100))
    return _read_color_match_boards(
        "formula_id IS NOT NULL AND TRIM(formula_id) != ''",
        limit=safe_limit,
    )


def update_color_match_board(board_id: str, updates: dict):
    column_map = {
        "Material": "material",
        "ImagePath": "image_path",
        "FormulaID": "formula_id",
        "FormulaMode": "formula_mode",
        "RecipeStatus": "recipe_status",
        "EmbeddingStatus": "embedding_status",
        "Customer": "customer",
        "ColorName": "color_name",
        "Pantone": "pantone",
        "CreateDate": "create_date",
        "LastUpdate": "last_update",
        "Remark": "remark",
        "ImageBase64": "image_base64",
    }
    valid_updates = [
        (column_map[key], value)
        for key, value in updates.items()
        if key in column_map
    ]
    if not valid_updates:
        return

    conn = get_turso_client()
    try:
        assignments = ", ".join(f"{column} = ?" for column, _ in valid_updates)
        params = [value for _, value in valid_updates]
        params.append(str(board_id).strip())
        result = conn.execute(
            f"UPDATE color_match_boards SET {assignments} WHERE id = ?",
            tuple(params),
        )
        if getattr(result, "rows_affected", 1) == 0:
            raise ValueError(f"找不到 ColorBoard ID：{board_id}")
        conn.commit()
        conn.sync()
    finally:
        conn.close()
