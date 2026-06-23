from pathlib import Path
import csv
from config import COLORBOARD_COLUMNS, SETTINGS

FORMULA_COLUMNS = ["FormulaID", "Material", "FormulaName", "Colorant", "Ratio", "Remark"]


def _ensure_csv(path: Path, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()


def _read_csv(path: Path, columns: list[str]) -> list[dict]:
    _ensure_csv(path, columns)
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [{column: (row.get(column) or "") for column in columns} for row in reader]


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows([{column: row.get(column, "") for column in columns} for row in rows])


def read_colorboard() -> list[dict]:
    return _read_csv(SETTINGS.colorboard_csv_path, COLORBOARD_COLUMNS)


def append_colorboard_row(row: dict) -> None:
    rows = read_colorboard()
    if row["ID"] in {existing["ID"] for existing in rows}:
        raise ValueError(f"ColorBoard ID 已存在：{row['ID']}")
    rows.append({column: row.get(column, "") for column in COLORBOARD_COLUMNS})
    _write_csv(SETTINGS.colorboard_csv_path, COLORBOARD_COLUMNS, rows)


def update_embedding_status(board_id: str, status: str, last_update: str) -> None:
    rows = read_colorboard()
    found = False
    for row in rows:
        if row["ID"] == board_id:
            row["EmbeddingStatus"] = status
            row["LastUpdate"] = last_update
            found = True
    if not found:
        raise ValueError(f"找不到 ColorBoard ID：{board_id}")
    _write_csv(SETTINGS.colorboard_csv_path, COLORBOARD_COLUMNS, rows)


def read_formulas() -> list[dict]:
    return _read_csv(SETTINGS.formula_csv_path, FORMULA_COLUMNS)


def lookup_formula_by_id(formula_id: str) -> list[dict]:
    if not formula_id:
        return []
    return [row for row in read_formulas() if str(row["FormulaID"]) == str(formula_id)]
