from services.google_sheet import lookup_formula_by_id
from services.models import FormulaResolution


def resolve_formula_mode(formula_id: str | None) -> FormulaResolution:
    clean_id = (formula_id or "").strip()
    if not clean_id:
        return FormulaResolution(exists=False, formula_mode="MANUAL", recipe_status="TRIAL")
    if lookup_formula_by_id(clean_id):
        return FormulaResolution(exists=True, formula_mode="EXISTING", recipe_status="OFFICIAL")
    return FormulaResolution(exists=False, formula_mode="MANUAL", recipe_status="TRIAL")
