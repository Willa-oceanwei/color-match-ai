from datetime import datetime
from services.id_utils import build_board_id, build_image_path, parse_board_id


def test_build_board_id_with_formula_id():
    assert build_board_id("abs", "27706") == "ABS_27706"


def test_build_board_id_without_formula_id_uses_trial_timestamp():
    now = datetime(2026, 6, 23, 15, 25, 0)
    assert build_board_id("ABS", None, now=now) == "ABS_TRIAL_20260623_152500"


def test_build_image_path_normalizes_material_and_extension():
    assert build_image_path("abs", "ABS_27706", "jpg") == "ABS/ABS_27706.jpg"


def test_parse_board_id():
    assert parse_board_id("ABS_27706") == {"material": "ABS", "suffix": "27706"}
