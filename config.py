from dataclasses import dataclass
from pathlib import Path
import os


def load_env_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(
            key.strip(),
            value.strip().strip('"').strip("'")
        )


load_env_file()


def _get(key: str, default: str = "") -> str:
    try:
        import streamlit as st
        val = st.secrets.get(key, None)
        if val is not None:
            return str(val)
    except Exception:
        pass
    return os.getenv(key, default)


@dataclass(frozen=True)
class Settings:
    storage_backend: str = _get(
        "COLOR_MATCH_STORAGE_BACKEND", "local"
    )
    colorboard_csv_path: Path = Path(
        _get("COLORBOARD_CSV_PATH", "data/colorboard.csv")
    )
    formula_csv_path: Path = Path(
        _get("FORMULA_CSV_PATH", "data/formulas.csv")
    )
    local_drive_root: Path = Path(
        _get("LOCAL_DRIVE_ROOT", "data/drive")
    )
    vector_dir: Path = Path(
        _get("VECTOR_DIR", "data/vectors")
    )
    embedding_backend: str = _get(
        "EMBEDDING_BACKEND", "color_stats"
    )
    openclip_model_name: str = _get(
        "OPENCLIP_MODEL_NAME", "ViT-B-32"
    )
    openclip_pretrained: str = _get(
        "OPENCLIP_PRETRAINED", "openai"
    )
    google_service_account_json: str = _get(
        "GOOGLE_SERVICE_ACCOUNT_JSON", ""
    )
    colorboard_spreadsheet_id: str = _get(
        "COLORBOARD_SPREADSHEET_ID", "1s3wfckJbCnJYHHftEzy4N5kEo1KMe767IwaGZzamYqA"
    )
    colorboard_worksheet_name: str = _get(
        "COLORBOARD_WORKSHEET_NAME", "ColorBoard"
    )
    formula_spreadsheet_id: str = _get(
        "FORMULA_SPREADSHEET_ID", "1s3wfckJbCnJYHHftEzy4N5kEo1KMe767IwaGZzamYqA"
    )
    formula_worksheet_name: str = _get(
        "FORMULA_WORKSHEET_NAME", "Formula"
    )
    google_drive_root_folder_id: str = _get(
        "GOOGLE_DRIVE_ROOT_FOLDER_ID", ""
    )
    google_drive_vectors_folder_id: str = _get(
        "GOOGLE_DRIVE_VECTORS_FOLDER_ID", ""
    )


SETTINGS = Settings()

COLORBOARD_COLUMNS = [
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
]
