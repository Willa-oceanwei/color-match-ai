from types import SimpleNamespace

from services import google_sheet


def test_lookup_formula_supports_formula_management_chinese_header(monkeypatch):
    monkeypatch.setattr(
        google_sheet,
        "read_formulas",
        lambda: [
            {"配方編號": " A1503C ", "Pigment1": "RED"},
            {"配方編號": "B1000", "Pigment1": "BLUE"},
        ],
    )

    result = google_sheet.lookup_formula_by_id("a1503c")

    assert result == [{"配方編號": " A1503C ", "Pigment1": "RED"}]


def test_formula_worksheet_prefers_configured_name_then_management(monkeypatch):
    class Worksheet:
        def __init__(self, title):
            self.title = title

    class Spreadsheet:
        def worksheets(self):
            return [Worksheet("配方管理"), Worksheet("Formula")]

    class Client:
        def open_by_key(self, spreadsheet_id):
            return Spreadsheet()

    monkeypatch.setattr(google_sheet, "_get_client", lambda: Client())
    monkeypatch.setattr(
        google_sheet,
        "SETTINGS",
        SimpleNamespace(
            formula_spreadsheet_id="sheet-id",
            formula_worksheet_name="不存在",
        ),
    )

    assert google_sheet._get_formula_ws().title == "配方管理"
