import json
from functools import lru_cache
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from config import SETTINGS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def _get_client():
    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def _get_colorboard_ws():
    client = _get_client()
    spreadsheet = client.open_by_key(SETTINGS.colorboard_spreadsheet_id)
    return spreadsheet.get_worksheet_by_id(0)

def _get_formula_ws():
    client = _get_client()
    return client.open_by_key(
        SETTINGS.formula_spreadsheet_id
    ).worksheet(
        SETTINGS.formula_worksheet_name
    )


def _get_vectors_ws():
    client = _get_client()
    spreadsheet = client.open_by_key(SETTINGS.colorboard_spreadsheet_id)
    return spreadsheet.get_worksheet_by_id(1827878360)

# =========================
# COLORBOARD
# =========================
def read_colorboard():
    ws = _get_colorboard_ws()
    return ws.get_all_records()


def append_colorboard_row(row: dict):
    import streamlit as st
    ws = _get_colorboard_ws()
    rows = ws.get_all_records()
    existing_ids = [r["ID"] for r in rows]
    if row["ID"] in {r["ID"] for r in rows}:
        raise ValueError(f"ColorBoard ID 已存在：{row['ID']}")
    ws.append_row(
        [
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
        ],
        value_input_option="USER_ENTERED"
    )


def update_embedding_status(board_id: str, status: str, last_update: str):
    ws = _get_colorboard_ws()
    rows = ws.get_all_records()
    for i, row in enumerate(rows, start=2):
        if row["ID"] == board_id:
            ws.update(f"G{i}", [[status]])            # ← [[value]]
            ws.update(f"L{i}", [[last_update]])       # ← [[value]]
            return
    raise ValueError(f"找不到 ColorBoard ID：{board_id}")

def get_all_colorboards(material: str = None):
    rows = read_colorboard()
    if material:
        material = material.strip().upper()
        return [
            r for r in rows
            if r.get("Material", "").strip().upper() == material
        ]
    return rows


# =========================
# VECTORS
# =========================
def save_vector_to_sheet(board_id: str, material: str, embedding, updated_at: str):
    ws = _get_vectors_ws()
    rows = ws.get_all_records()

    embedding_json = json.dumps(
        embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
    )

    for i, row in enumerate(rows, start=2):
        if row["ID"] == board_id:
            ws.update(f"C{i}", [[embedding_json]])   # ← [[value]]
            ws.update(f"D{i}", [[updated_at]])        # ← [[value]]
            return

    ws.append_row(
        [board_id, material.upper(), embedding_json, updated_at],
        value_input_option="USER_ENTERED"
    )


def load_vectors_from_sheet(material: str) -> list:
    import numpy as np
    ws = _get_vectors_ws()
    rows = ws.get_all_records()
    result = []
    for row in rows:
        if row.get("Material", "").strip().upper() == material.strip().upper():
            try:
                embedding = json.loads(row["Embedding"])
                result.append({
                    "id": row["ID"],
                    "embedding": embedding
                })
            except Exception:
                continue
    return result


# =========================
# FORMULA
# =========================
def read_formulas():
    ws = _get_formula_ws()
    return ws.get_all_records()


def lookup_formula_by_id(formula_id: str):
    if not formula_id:
        return []
    rows = read_formulas()
    return [
        r for r in rows
        if str(r["FormulaID"]) == str(formula_id)
    ]
