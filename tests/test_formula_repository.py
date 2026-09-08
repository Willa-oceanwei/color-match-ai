from services import formula_repository


def test_formula_lookup_prefers_turso(monkeypatch):
    turso_formula = [{"FormulaID": "A1503C", "FormulaSource": "Turso 配方管理"}]
    monkeypatch.setattr(
        formula_repository, "lookup_managed_formula_by_id", lambda formula_id: turso_formula
    )
    monkeypatch.setattr(
        formula_repository,
        "lookup_sheet_formula_by_id",
        lambda formula_id: (_ for _ in ()).throw(AssertionError("Sheet must not run")),
    )

    assert formula_repository.lookup_formula_by_id("A1503C") == turso_formula


def test_formula_lookup_falls_back_to_sheet_when_turso_tables_are_unavailable(monkeypatch):
    sheet_formula = [{"FormulaID": "A1503C"}]
    monkeypatch.setattr(
        formula_repository,
        "lookup_managed_formula_by_id",
        lambda formula_id: (_ for _ in ()).throw(RuntimeError("no such table")),
    )
    monkeypatch.setattr(
        formula_repository, "lookup_sheet_formula_by_id", lambda formula_id: sheet_formula
    )

    assert formula_repository.lookup_formula_by_id("A1503C") == sheet_formula
