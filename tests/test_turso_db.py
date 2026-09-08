from services import turso_db


class FakeResult:
    def __init__(self, rows):
        self.rows = rows


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.events = []
        self.query = ""
        self.params = ()

    def sync(self):
        self.events.append("sync")

    def execute(self, query, params=()):
        self.events.append("execute")
        self.query = query
        self.params = params
        return FakeResult(self.rows)

    def close(self):
        self.events.append("close")


def _row(formula_id="52824"):
    return (
        "ABS_52824", "ABS", "ABS/image.jpg", formula_id, "EXISTING",
        "OFFICIAL", "Y", "Customer", "Red", "186 C", "2026/09/08",
        "2026/09/08 10:00", "", "base64",
    )


def test_formula_lookup_syncs_replica_and_maps_result(monkeypatch):
    connection = FakeConnection([_row()])
    monkeypatch.setattr(turso_db, "get_turso_client", lambda: connection)

    result = turso_db.get_color_match_boards_by_formula_id(" 52824 ")

    assert connection.events == ["sync", "execute", "close"]
    assert connection.params == ("52824",)
    assert result[0]["FormulaID"] == "52824"
    assert result[0]["ColorName"] == "Red"


def test_recent_formula_boards_uses_bounded_limit(monkeypatch):
    connection = FakeConnection([_row()])
    monkeypatch.setattr(turso_db, "get_turso_client", lambda: connection)

    turso_db.get_recent_color_match_boards(limit=500)

    assert "TRIM(formula_id) != ''" in connection.query
    assert connection.params == (100,)
