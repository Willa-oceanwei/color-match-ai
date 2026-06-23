from dataclasses import dataclass


@dataclass(frozen=True)
class FormulaResolution:
    exists: bool
    formula_mode: str
    recipe_status: str


@dataclass(frozen=True)
class SearchResult:
    id: str
    similarity: float
    board: dict
    formula_rows: list[dict]

    @property
    def has_formula(self) -> bool:
        return bool(self.formula_rows)
