from services import turso_db


class FakeResult:
    def __init__(self, rows):
        self.rows = rows
        self.rows_affected = 1


class FakeDbApiCursor:
    def __init__(self, rows, rowcount=1):
        self._rows = rows
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows


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


class SchemaConnection(FakeConnection):
    def __init__(self, columns):
        super().__init__([])
        self.columns = columns
        self.queries = []

    def execute(self, query, params=()):
        self.events.append("execute")
        self.queries.append(query)
        if query.startswith("PRAGMA"):
            return FakeResult([(index, column) for index, column in enumerate(self.columns)])
        return FakeResult([])


class DbApiSchemaConnection(SchemaConnection):
    def execute(self, query, params=()):
        self.events.append("execute")
        self.queries.append(query)
        if query.startswith("PRAGMA"):
            rows = [(index, column) for index, column in enumerate(self.columns)]
            return FakeDbApiCursor(rows)
        return FakeDbApiCursor([])


class DbApiReadConnection(FakeConnection):
    def execute(self, query, params=()):
        self.events.append("execute")
        self.query = query
        self.params = params
        return FakeDbApiCursor(self.rows)


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


def test_formula_lookup_supports_db_api_cursor(monkeypatch):
    connection = DbApiReadConnection([_row()])
    monkeypatch.setattr(turso_db, "get_turso_client", lambda: connection)

    result = turso_db.get_color_match_boards_by_formula_id("52824")

    assert result[0]["FormulaID"] == "52824"
    assert connection.events == ["sync", "execute", "close"]


def test_recent_boards_includes_rows_without_formula_and_bounds_limit(monkeypatch):
    connection = FakeConnection([_row()])
    monkeypatch.setattr(turso_db, "get_turso_client", lambda: connection)

    turso_db.get_recent_color_match_boards(limit=500)

    assert " WHERE " not in connection.query
    assert "datetime(REPLACE" in connection.query
    assert "last_update" in connection.query
    assert "create_date" in connection.query
    assert connection.params == (100,)


def test_search_boards_by_customer_or_color_escapes_like_wildcards(monkeypatch):
    connection = FakeConnection([_row()])
    monkeypatch.setattr(turso_db, "get_turso_client", lambda: connection)

    result = turso_db.search_color_match_boards(" ACME_100% ")

    assert result[0]["ColorName"] == "Red"
    assert "customer LIKE" in connection.query
    assert "color_name LIKE" in connection.query
    assert connection.params == ("%ACME\\_100\\%%", "%ACME\\_100\\%%", 50)


def test_similar_formula_ids_rank_nearest_match(monkeypatch):
    rows = [
        _row("A1503C"),
        _row("A1508B"),
        _row("A1503C"),
        _row("A9999Z"),
    ]
    connection = FakeConnection(rows)
    monkeypatch.setattr(turso_db, "get_turso_client", lambda: connection)

    result = turso_db.get_similar_formula_ids("A1503A")

    assert result[0] == "A1503C"
    assert result.count("A1503C") == 1
    assert connection.params == ("A1%", 100)


def test_similar_formula_ids_ignores_short_queries(monkeypatch):
    monkeypatch.setattr(
        turso_db,
        "get_turso_client",
        lambda: (_ for _ in ()).throw(AssertionError("must not connect")),
    )

    assert turso_db.get_similar_formula_ids("A") == []


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


def test_init_adds_columns_missing_from_an_existing_database(monkeypatch):
    old_columns = set(turso_db.COLOR_MATCH_SCHEMA) - {"image_base64", "last_update"}
    connection = SchemaConnection(old_columns)
    monkeypatch.setattr(turso_db, "get_turso_client", lambda: connection)

    turso_db.init_color_match_tables()

    alter_queries = [query for query in connection.queries if query.startswith("ALTER")]
    assert set(alter_queries) == {
        "ALTER TABLE color_match_boards ADD COLUMN image_base64 TEXT",
        "ALTER TABLE color_match_boards ADD COLUMN last_update TEXT",
    }
    assert connection.events[-3:] == ["commit", "sync", "close"]


def test_init_supports_db_api_cursor_without_rows_attribute(monkeypatch):
    connection = DbApiSchemaConnection(turso_db.COLOR_MATCH_SCHEMA)
    monkeypatch.setattr(turso_db, "get_turso_client", lambda: connection)

    turso_db.init_color_match_tables()

    assert not [query for query in connection.queries if query.startswith("ALTER")]
    assert connection.events[-3:] == ["commit", "sync", "close"]


def test_import_legacy_boards_skips_existing_and_blank_ids(monkeypatch):
    class ImportConnection(FakeConnection):
        def __init__(self):
            super().__init__([])
            self.calls = []

        def execute(self, query, params=()):
            self.events.append("execute")
            self.calls.append((query, params))
            return FakeDbApiCursor([], rowcount=0 if params[0] == "EXISTING" else 1)

    connection = ImportConnection()
    monkeypatch.setattr(turso_db, "get_turso_client", lambda: connection)

    result = turso_db.import_color_match_boards([
        {"ID": "OLD_1", "FormulaID": "10001", "Material": "ABS"},
        {"ID": "EXISTING", "FormulaID": "10002", "Material": "PP"},
        {"ID": "", "FormulaID": "10003", "Material": "PC"},
    ])

    assert result == {"inserted": 1, "skipped": 2, "total": 3}
    assert len(connection.calls) == 2
    assert "ON CONFLICT(id) DO NOTHING" in connection.calls[0][0]
    assert connection.events[-3:] == ["commit", "sync", "close"]
