import streamlit as st
import libsql
from difflib import SequenceMatcher
from config import SETTINGS


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

COLOR_MATCH_SCHEMA = {
    "id": "TEXT",
    "material": "TEXT",
    "image_path": "TEXT",
    "formula_id": "TEXT",
    "formula_mode": "TEXT",
    "recipe_status": "TEXT",
    "embedding_status": "TEXT",
    "customer": "TEXT",
    "color_name": "TEXT",
    "pantone": "TEXT",
    "create_date": "TEXT",
    "last_update": "TEXT",
    "remark": "TEXT",
    "image_base64": "TEXT",
}


def _fetch_rows(cursor):
    """Return query rows for both DB-API cursors and legacy libsql results."""
    fetchall = getattr(cursor, "fetchall", None)
    if callable(fetchall):
        return fetchall()
    return getattr(cursor, "rows", cursor)


def get_turso_client():
    url = st.secrets["TURSO_DATABASE_URL"]
    auth_token = st.secrets["TURSO_AUTH_TOKEN"]

    return libsql.connect(
        "color_match_local.db",
        sync_url=url,
        auth_token=auth_token,
    )


def get_formula_turso_client():
    url = SETTINGS.formula_turso_database_url or st.secrets["TURSO_DATABASE_URL"]
    auth_token = (
        SETTINGS.formula_turso_auth_token or st.secrets["TURSO_AUTH_TOKEN"]
    )
    return libsql.connect(
        "formula_management_local.db",
        sync_url=url,
        auth_token=auth_token,
    )


def init_color_match_tables():
    conn = get_turso_client()
    try:
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

        # CREATE TABLE IF NOT EXISTS does not add columns to databases created
        # by older deployments. Migrate those databases before any SELECT tries
        # to read newer fields such as image_base64.
        existing_columns = {
            row[1]
            for row in _fetch_rows(
                conn.execute("PRAGMA table_info(color_match_boards)")
            )
        }
        for column, column_type in COLOR_MATCH_SCHEMA.items():
            if column not in existing_columns:
                conn.execute(
                    f"ALTER TABLE color_match_boards ADD COLUMN {column} {column_type}"
                )

        conn.commit()
        conn.sync()
    finally:
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


def import_color_match_boards(rows: list[dict]):
    """Import legacy Sheet rows without overwriting records already in Turso."""
    conn = get_turso_client()
    inserted = 0
    skipped = 0
    try:
        for row in rows:
            board_id = str(row.get("ID", "") or "").strip()
            if not board_id:
                skipped += 1
                continue

            cursor = conn.execute(
                """
                INSERT INTO color_match_boards (
                    id, material, image_path, formula_id, formula_mode,
                    recipe_status, embedding_status, customer, color_name,
                    pantone, create_date, last_update, remark, image_base64
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (
                    board_id,
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
            if getattr(cursor, "rowcount", 1) == 0:
                skipped += 1
            else:
                inserted += 1

        conn.commit()
        conn.sync()
        return {"inserted": inserted, "skipped": skipped, "total": len(rows)}
    finally:
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


def _read_color_match_boards(
    where_clause="",
    params=(),
    limit=None,
    order_by="rowid DESC",
):
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
        query += f" ORDER BY {order_by}"
        query_params = list(params)
        if limit is not None:
            query += " LIMIT ?"
            query_params.append(limit)

        cursor = conn.execute(query, tuple(query_params))
        return _rows_to_color_match_boards(_fetch_rows(cursor))
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
    # Legacy Sheet rows may be imported after newer Turso rows, so rowid does
    # not represent the actual creation time. Slash-separated timestamps are
    # normalized for SQLite before sorting.
    return _read_color_match_boards(
        limit=safe_limit,
        order_by=(
            "COALESCE("
            "datetime(REPLACE(NULLIF(TRIM(last_update), ''), '/', '-')), "
            "datetime(REPLACE(NULLIF(TRIM(create_date), ''), '/', '-'))"
            ") DESC, rowid DESC"
        ),
    )


def search_color_match_boards(keyword: str, limit: int = 50):
    clean_keyword = str(keyword or "").strip()
    if not clean_keyword:
        return []
    safe_limit = max(1, min(int(limit), 100))
    escaped_keyword = (
        clean_keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    like_keyword = f"%{escaped_keyword}%"
    return _read_color_match_boards(
        "(customer LIKE ? ESCAPE '\\' COLLATE NOCASE "
        "OR color_name LIKE ? ESCAPE '\\' COLLATE NOCASE)",
        (like_keyword, like_keyword),
        limit=safe_limit,
    )


def get_similar_formula_ids(formula_id: str, limit: int = 5):
    """Return likely formula IDs for a mistyped or near-matching ID."""
    clean_formula_id = str(formula_id or "").strip()
    if len(clean_formula_id) < 2:
        return []

    safe_limit = max(1, min(int(limit), 10))
    prefix = clean_formula_id[:2].replace("\\", "\\\\")
    prefix = prefix.replace("%", "\\%").replace("_", "\\_")
    candidates = _read_color_match_boards(
        "formula_id IS NOT NULL AND TRIM(formula_id) != '' "
        "AND formula_id LIKE ? ESCAPE '\\' COLLATE NOCASE",
        (f"{prefix}%",),
        limit=100,
    )

    unique_ids = {
        str(row.get("FormulaID", "") or "").strip()
        for row in candidates
        if str(row.get("FormulaID", "") or "").strip()
    }
    scored_ids = [
        (
            SequenceMatcher(None, clean_formula_id.casefold(), candidate.casefold()).ratio(),
            candidate,
        )
        for candidate in unique_ids
        if candidate.casefold() != clean_formula_id.casefold()
    ]
    return [
        candidate
        for score, candidate in sorted(scored_ids, key=lambda item: (-item[0], item[1]))
        if score >= 0.65
    ][:safe_limit]


def lookup_managed_formula_by_id(formula_id: str):
    """Read a recipe and its components from color-powder-app tables."""
    clean_formula_id = str(formula_id or "").strip()
    if not clean_formula_id:
        return []

    conn = get_formula_turso_client()
    try:
        _sync_replica(conn)
        recipe_rows = _fetch_rows(conn.execute(
            """
            SELECT recipe_id, color, customer_name, pantone_code,
                   ratio1, ratio2, ratio3, net_weight, net_weight_unit,
                   total_category, notes
            FROM recipes
            WHERE recipe_id = ? COLLATE NOCASE
              AND COALESCE(lifecycle_status, 'active') = 'active'
            LIMIT 1
            """,
            (clean_formula_id,),
        ))
        if not recipe_rows:
            return []

        recipe = recipe_rows[0]
        component_rows = _fetch_rows(conn.execute(
            """
            SELECT rc.colorpowder_id, rc.weight
            FROM recipe_components AS rc
            WHERE rc.recipe_id = ? COLLATE NOCASE
            ORDER BY rc.position
            LIMIT 8
            """,
            (clean_formula_id,),
        ))
        ratios = [str(value).strip() for value in recipe[4:7] if value not in (None, "")]
        result = {
            "FormulaID": recipe[0],
            "ColorName": recipe[1] or "",
            "Customer": recipe[2] or "",
            "Pantone": recipe[3] or "",
            "AddRatio": " / ".join(ratios),
            "NetWeight": recipe[7] if recipe[7] is not None else "",
            "NetWeightUnit": recipe[8] or "",
            "TotalType": recipe[9] or "",
            "Remark": recipe[10] or "",
            "FormulaSource": "Turso 配方管理",
        }
        for position, component in enumerate(component_rows, start=1):
            result[f"Pigment{position}"] = component[0]
            result[f"Weight{position}"] = component[1]
        return [result]
    finally:
        conn.close()


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
        cursor = conn.execute(
            f"UPDATE color_match_boards SET {assignments} WHERE id = ?",
            tuple(params),
        )
        affected_rows = getattr(cursor, "rowcount", None)
        if affected_rows is None:
            affected_rows = getattr(cursor, "rows_affected", 1)
        if affected_rows == 0:
            raise ValueError(f"找不到 ColorBoard ID：{board_id}")
        conn.commit()
        conn.sync()
    finally:
        conn.close()
