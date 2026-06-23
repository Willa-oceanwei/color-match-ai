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
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


@dataclass(frozen=True)
class Settings:
    storage_backend: str = os.getenv("COLOR_MATCH_STORAGE_BACKEND", "local")
    colorboard_csv_path: Path = Path(os.getenv("COLORBOARD_CSV_PATH", "data/colorboard.csv"))
    formula_csv_path: Path = Path(os.getenv("FORMULA_CSV_PATH", "data/formulas.csv"))
    local_drive_root: Path = Path(os.getenv("LOCAL_DRIVE_ROOT", "data/drive"))
    vector_dir: Path = Path(os.getenv("VECTOR_DIR", "data/vectors"))
    embedding_backend: str = os.getenv("EMBEDDING_BACKEND", "color_stats")
    openclip_model_name: str = os.getenv("OPENCLIP_MODEL_NAME", "ViT-B-32")
    openclip_pretrained: str = os.getenv("OPENCLIP_PRETRAINED", "openai")
    google_service_account_json: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    colorboard_spreadsheet_id: str = os.getenv("COLORBOARD_SPREADSHEET_ID", "")
    colorboard_worksheet_name: str = os.getenv("COLORBOARD_WORKSHEET_NAME", "ColorBoard")
    formula_spreadsheet_id: str = os.getenv("FORMULA_SPREADSHEET_ID", "")
    formula_worksheet_name: str = os.getenv("FORMULA_WORKSHEET_NAME", "Formula")
    google_drive_root_folder_id: str = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "")


SETTINGS = Settings()
COLORBOARD_COLUMNS = [
    "ID", "Material", "ImagePath", "FormulaID", "FormulaMode", "RecipeStatus",
    "EmbeddingStatus", "Customer", "ColorName", "Pantone", "CreateDate", "LastUpdate", "Remark",
]
