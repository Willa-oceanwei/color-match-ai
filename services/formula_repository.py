from services.google_sheet import lookup_formula_by_id as lookup_sheet_formula_by_id
from services.turso_db import lookup_managed_formula_by_id


def lookup_formula_by_id(formula_id: str):
    """Prefer the shared Turso recipe tables, with Google Sheet as fallback."""
    if not str(formula_id or "").strip():
        return []
    try:
        formulas = lookup_managed_formula_by_id(formula_id)
        if formulas:
            return formulas
    except Exception:
        # Deployments that do not share color-powder-app's Turso database may
        # not contain the recipes tables yet. Keep Sheet available in transition.
        pass
    return lookup_sheet_formula_by_id(formula_id)
