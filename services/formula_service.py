from services.google_sheet import lookup_formula_by_id
from services.models import FormulaResolution


def resolve_formula_mode(formula_id: str | None):

    clean_id = (formula_id or "").strip()

    # 沒有配方 = 留樣
    if clean_id == "":
        return FormulaResolution(
            exists=False,
            formula_mode="TRIAL",
            recipe_status="TRIAL"
        )

    # 有正式配方
    if lookup_formula_by_id(clean_id):

        return FormulaResolution(
            exists=True,
            formula_mode="OFFICIAL",
            recipe_status="OFFICIAL"
        )

    # 有配方號但不在正式配方管理
    return FormulaResolution(
        exists=False,
        formula_mode="REFERENCE",
        recipe_status="REFERENCE"
    )
