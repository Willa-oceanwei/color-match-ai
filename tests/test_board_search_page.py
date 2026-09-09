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
