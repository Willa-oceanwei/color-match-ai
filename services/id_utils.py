from datetime import datetime
import re

_ID_PATTERN = re.compile(r"^(?P<material>[A-Za-z0-9]+)_(?P<formula>.+)$")


def normalize_material(material: str) -> str:
    return material.strip().upper()


def parse_board_id(board_id: str) -> dict[str, str]:
    match = _ID_PATTERN.match(board_id.strip())
    if not match:
        raise ValueError("ID 必須符合 Material_識別碼，例如 ABS_27706")
    return {"material": normalize_material(match.group("material")), "suffix": match.group("formula")}


def build_board_id(material: str, formula_id: str | None = None, now: datetime | None = None) -> str:
    material_code = normalize_material(material)
    clean_formula = (formula_id or "").strip()
    if clean_formula:
        return f"{material_code}_{clean_formula}"
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"{material_code}_TRIAL_{timestamp}"


def build_image_path(material: str, board_id: str, extension: str = ".jpg") -> str:
    suffix = extension.lower()
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    return f"{normalize_material(material)}/{board_id}{suffix}"
