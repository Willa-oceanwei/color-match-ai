import json
import re
from functools import lru_cache
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from config import SETTINGS

# =========================
# AUTH
# =========================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@lru_cache
def _get_client():
    raw = st.secrets["gcp_service_account"]
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

# =========================
# SHEETS
# =========================
def _get_colorboard_ws():

    client = _get_client()

    return client.open_by_key(
        SETTINGS.colorboard_spreadsheet_id
    ).worksheet(
        SETTINGS.colorboard_worksheet_name
    )


def _get_formula_ws():

    client = _get_client()

    return client.open_by_key(
        SETTINGS.formula_spreadsheet_id
    ).worksheet(
        SETTINGS.formula_worksheet_name
    )


# =========================
# COLORBOARD
# =========================
def read_colorboard():

    ws = _get_colorboard_ws()

    return ws.get_all_records()


def append_colorboard_row(row: dict):

    ws = _get_colorboard_ws()

    rows = ws.get_all_records()

    # check duplicate
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
        ],
        value_input_option="USER_ENTERED"
    )


def update_embedding_status(board_id: str, status: str, last_update: str):

    ws = _get_colorboard_ws()

    rows = ws.get_all_records()

    for i, row in enumerate(rows, start=2):  # row 1 = header

        if row["ID"] == board_id:

            # G = EmbeddingStatus
            ws.update(f"G{i}", status)

            # L = LastUpdate
            ws.update(f"L{i}", last_update)

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
