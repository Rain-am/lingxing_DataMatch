from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from typing import Any, Iterator

import pymysql
from pymysql.cursors import DictCursor

from app.config import get_settings
from app.schemas import Granularity, Rule, Source, StoreMapping


def _quote_identifier(identifier: str) -> str:
    return f"`{identifier}`"


def _period_sql(field: str, granularity: Granularity) -> str:
    # PyMySQL uses percent-style placeholders, so literal MySQL DATE_FORMAT
    # percent signs must be escaped as %% inside the query string.
    fmt = "%%Y-%%m-%%d" if granularity == "day" else "%%Y-%%m-01"
    return f"DATE_FORMAT({_quote_identifier(field)}, '{fmt}')"


def _map_store(raw_store: str, mapping: dict[str, str]) -> str:
    return mapping.get(raw_store, raw_store)


@contextmanager
def _warehouse_connection() -> Iterator[pymysql.connections.Connection]:
    settings = get_settings()
    tunnel = None
    host = settings.mysql_host
    port = settings.mysql_port

    if settings.ssh_tunnel_enabled:
        if not all([settings.ssh_host, settings.ssh_user, settings.ssh_remote_host]):
            raise RuntimeError("SSH tunnel is enabled but SSH_HOST, SSH_USER, or SSH_REMOTE_HOST is missing")
        from sshtunnel import SSHTunnelForwarder

        tunnel = SSHTunnelForwarder(
            (settings.ssh_host, settings.ssh_port),
            ssh_username=settings.ssh_user,
            ssh_password=settings.ssh_password,
            remote_bind_address=(settings.ssh_remote_host, settings.ssh_remote_port),
            local_bind_address=("127.0.0.1", 0),
        )
        tunnel.start()
        host = "127.0.0.1"
        port = int(tunnel.local_bind_port)

    connection = pymysql.connect(
        host=host,
        port=port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        connect_timeout=20,
        read_timeout=60,
        write_timeout=60,
    )
    try:
        yield connection
    finally:
        connection.close()
        if tunnel:
            tunnel.stop()


def fetch_warehouse_source_values(
    source: Source,
    start_date: str,
    end_date: str,
    granularity: Granularity,
) -> dict[tuple[str, str, str, str], Decimal]:
    metric_selects: list[str] = []
    for index, metric in enumerate(source.metrics):
        alias = f"metric_{index}"
        if metric.aggregation == "count":
            expression = "*" if metric.warehouse_expression.strip() == "*" else metric.warehouse_expression
            metric_selects.append(f"COUNT({expression}) AS `{alias}`")
        else:
            metric_selects.append(f"COALESCE(SUM({metric.warehouse_expression}), 0) AS `{alias}`")

    period_expr = _period_sql(source.date_field, granularity)
    table_name = _quote_identifier(source.table_or_path)
    date_field = _quote_identifier(source.date_field)
    store_field = _quote_identifier(source.store_field)
    sql = f"""
        SELECT
            {period_expr} AS period,
            CAST({store_field} AS CHAR) AS store,
            {", ".join(metric_selects)}
        FROM {table_name}
        WHERE {date_field} >= %s AND {date_field} < DATE_ADD(%s, INTERVAL 1 DAY)
        GROUP BY period, store
        ORDER BY period, store
    """

    with _warehouse_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, (start_date, end_date))
            rows: list[dict[str, Any]] = cursor.fetchall()
        store_mapping = fetch_store_mapping_for_source(source, connection)

    result: dict[tuple[str, str, str, str], Decimal] = {}
    for row in rows:
        period = str(row["period"])
        store = _map_store(str(row["store"] or ""), store_mapping)
        for index, metric in enumerate(source.metrics):
            value = row.get(f"metric_{index}") or 0
            result[(period, store, metric.name, source.name)] = Decimal(str(value))
    return result


def fetch_store_mapping(mapping: StoreMapping) -> dict[str, str]:
    with _warehouse_connection() as connection:
        return _fetch_store_mapping(mapping, connection)


def fetch_store_mapping_for_source(source: Source, connection: pymysql.connections.Connection) -> dict[str, str]:
    if not source.store_mapping.enabled:
        return {}
    return _fetch_store_mapping(source.store_mapping, connection)


def _fetch_store_mapping(mapping: StoreMapping, connection: pymysql.connections.Connection) -> dict[str, str]:
    if not mapping.enabled:
        return {}
    table = _quote_identifier(mapping.table)
    id_field = _quote_identifier(mapping.id_field)
    name_field = _quote_identifier(mapping.name_field)
    sql = f"""
        SELECT CAST({id_field} AS CHAR) AS store_id, CAST({name_field} AS CHAR) AS store_name
        FROM {table}
        WHERE {id_field} IS NOT NULL
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows: list[dict[str, Any]] = cursor.fetchall()
    return {str(row["store_id"]): str(row["store_name"] or row["store_id"]) for row in rows}


def fetch_warehouse_aggregate(
    rule: Rule,
    start_date: str,
    end_date: str,
    granularity: Granularity,
) -> dict[tuple[str, str, str], Decimal]:
    source = Source(
        name="数仓",
        type="warehouse",
        table_or_path=rule.warehouse_table,
        date_field=rule.warehouse_date_field,
        store_field=rule.warehouse_store_field,
        metrics=rule.metrics,
    )
    values = fetch_warehouse_source_values(source, start_date, end_date, granularity)
    return {(period, store, metric): value for (period, store, metric, _source), value in values.items()}
