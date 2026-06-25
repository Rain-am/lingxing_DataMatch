from app.schemas import StoreMapping
from app.warehouse import _fetch_store_mapping


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed_sql = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql):
        self.executed_sql = sql

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = FakeCursor(rows)

    def cursor(self):
        return self.cursor_instance


def test_fetch_store_mapping_reads_id_name_pairs() -> None:
    connection = FakeConnection([
        {"store_id": "110", "store_name": "US Store"},
        {"store_id": "120", "store_name": "EU Store"},
    ])
    mapping = StoreMapping(enabled=True, table="seller", id_field="sid", name_field="seller_name")

    result = _fetch_store_mapping(mapping, connection)

    assert result == {"110": "US Store", "120": "EU Store"}
    assert "FROM `seller`" in connection.cursor_instance.executed_sql
    assert "`sid`" in connection.cursor_instance.executed_sql
    assert "`seller_name`" in connection.cursor_instance.executed_sql


def test_fetch_store_mapping_keeps_id_when_name_missing() -> None:
    connection = FakeConnection([{"store_id": "110", "store_name": None}])
    mapping = StoreMapping(enabled=True, table="seller", id_field="sid", name_field="seller_name")

    assert _fetch_store_mapping(mapping, connection) == {"110": "110"}


def test_fetch_store_mapping_disabled_skips_query() -> None:
    connection = FakeConnection([{"store_id": "110", "store_name": "US Store"}])

    assert _fetch_store_mapping(StoreMapping(enabled=False), connection) == {}
    assert connection.cursor_instance.executed_sql == ""
