from ui import board_search_page


def test_find_boards_uses_database_filter_when_available(monkeypatch):
    expected = [{"ID": "ABS_1"}]
    monkeypatch.setattr(
        board_search_page.turso_db,
        "find_color_match_boards",
        lambda filters: expected,
    )

    assert board_search_page._find_boards({"Material": "ABS"}) == expected


def test_find_boards_falls_back_when_filtered_export_is_stale(monkeypatch):
    monkeypatch.setattr(
        board_search_page.turso_db,
        "find_color_match_boards",
        None,
    )
    monkeypatch.setattr(
        board_search_page.turso_db,
        "get_all_color_match_boards",
        lambda: [
            {"ID": "ABS_1", "Material": "ABS", "Customer": "Ocean"},
            {"ID": "PP_2", "Material": "PP", "Customer": "Other"},
        ],
    )

    result = board_search_page._find_boards({
        "Material": "abs",
        "Customer": "oce",
    })

    assert result == [{"ID": "ABS_1", "Material": "ABS", "Customer": "Ocean"}]


def test_lookup_board_formula_uses_selected_board_formula_id(monkeypatch):
    expected = [{"FormulaID": "A1503C"}]
    captured = {}

    def fake_lookup(formula_id):
        captured["formula_id"] = formula_id
        return expected

    monkeypatch.setattr(board_search_page, "lookup_formula_by_id", fake_lookup)

    result = board_search_page._lookup_board_formula({"FormulaID": " A1503C "})

    assert captured["formula_id"] == "A1503C"
    assert result == expected


def test_lookup_board_formula_skips_blank_formula_id(monkeypatch):
    monkeypatch.setattr(
        board_search_page,
        "lookup_formula_by_id",
        lambda formula_id: (_ for _ in ()).throw(AssertionError("Lookup must not run")),
    )

    assert board_search_page._lookup_board_formula({"FormulaID": " "}) == []


def test_formula_pigment_rows_supports_wide_formula_format():
    result = board_search_page._formula_pigment_rows([{
        "Pigment1": "RED",
        "Weight1": "1.0",
        "Pigment2": "BLUE",
        "Weight2": "0.25",
    }])

    assert result == [
        {"色粉編號": "RED", "重量 (g)": "1"},
        {"色粉編號": "BLUE", "重量 (g)": "0.25"},
    ]


def test_formula_pigment_rows_supports_legacy_row_formula_format():
    result = board_search_page._formula_pigment_rows([
        {"Colorant": "Titanium White", "Ratio": "2.5"},
        {"Colorant": "Yellow Toner", "Ratio": "0.030"},
    ])

    assert result == [
        {"色粉編號": "Titanium White", "重量 (g)": "2.5"},
        {"色粉編號": "Yellow Toner", "重量 (g)": "0.03"},
    ]
