from services import turso_db


class FakeResult:
    def __init__(self, rows):
        self.rows = rows
        self.rows_affected = 1


class FakeConnection:
    def __init__(self, rows, sync_error=None):
        self.rows = rows
        self.sync_error = sync_error
        self.events = []
        self.query = ""
        self.params = ()

    def sync(self):
        self.events.append("sync")
        if self.sync_error:
            raise self.sync_error

    def execute(self, query, params=()):
        self.events.append("execute")
        self.query = query
        self.params = params
        return FakeResult(self.rows)

    def close(self):
        self.events.append("close")

    def commit(self):
        self.events.append("commit")


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


def test_read_uses_local_replica_when_sync_temporarily_fails(monkeypatch):
    connection = FakeConnection([_row()], sync_error=RuntimeError("offline"))
    monkeypatch.setattr(turso_db, "get_turso_client", lambda: connection)

    result = turso_db.get_color_match_boards_by_formula_id("52824")

    assert connection.events == ["sync", "execute", "close"]
    assert result[0]["FormulaID"] == "52824"


def test_update_color_match_board_writes_turso(monkeypatch):
    connection = FakeConnection([])
    monkeypatch.setattr(turso_db, "get_turso_client", lambda: connection)

    turso_db.update_color_match_board(
        "ABS_52824",
        {"Customer": "New customer", "RecipeStatus": "TRIAL"},
    )

    assert "customer = ?" in connection.query
    assert "recipe_status = ?" in connection.query
    assert connection.params == ("New customer", "TRIAL", "ABS_52824")
    assert connection.events == ["execute", "commit", "sync", "close"]


def test_get_color_match_board_by_id_returns_first_match(monkeypatch):
    connection = FakeConnection([_row()])
    monkeypatch.setattr(turso_db, "get_turso_client", lambda: connection)

    result = turso_db.get_color_match_board_by_id(" ABS_52824 ")

    assert result["ID"] == "ABS_52824"
    assert connection.params == ("ABS_52824", 1)
