from services import formula_service
from services.formula_service import resolve_formula_mode


def test_resolve_formula_mode_existing_formula(monkeypatch):
    monkeypatch.setattr(formula_service, "lookup_formula_by_id", lambda value: [{}])
    result = resolve_formula_mode("27706")
    assert result.exists is True
    assert result.formula_mode == "OFFICIAL"
    assert result.recipe_status == "OFFICIAL"


def test_resolve_formula_mode_manual_when_blank():
    result = resolve_formula_mode("")
    assert result.exists is False
    assert result.formula_mode == "TRIAL"
    assert result.recipe_status == "TRIAL"


def test_resolve_formula_mode_manual_when_missing(monkeypatch):
    monkeypatch.setattr(formula_service, "lookup_formula_by_id", lambda value: [])
    result = resolve_formula_mode("NO_SUCH_FORMULA")
    assert result.exists is False
    assert result.formula_mode == "REFERENCE"
    assert result.recipe_status == "REFERENCE"
