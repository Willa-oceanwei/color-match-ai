from datetime import datetime
import re

_ID_PATTERN = re.compile(
    r"^(?P<material>[A-Za-z0-9]+)_(?P<formula>.+)$"
)


def normalize_material(material: str) -> str:
    return material.strip().upper()


def parse_board_id(board_id: str):

    match = _ID_PATTERN.match(board_id.strip())

    if not match:
        raise ValueError(
            "ID 必須符合 Material_xxx，例如 ABS_27706"
        )

    return {
        "material": normalize_material(match.group("material")),
        "suffix": match.group("formula")
    }


def build_board_id(
        material: str,
        formula_id: str | None = None,
        now: datetime | None = None):

    material = normalize_material(material)

    formula_id = (formula_id or "").strip()

    # 有配方編號
    if formula_id:

        return f"{material}_{formula_id}"

    # 無配方，留樣
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")

    return f"{material}_TRIAL_{timestamp}"


def build_image_path(
        material: str,
        board_id: str,
        extension: str = ".jpg"):

    material = normalize_material(material)

    ext = extension.lower()

    if not ext.startswith("."):
        ext = "." + ext

    return f"{material}/{board_id}{ext}"
