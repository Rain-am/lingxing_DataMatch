from __future__ import annotations

from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Callable, Iterator, Optional

import pymysql
from pymysql.err import OperationalError
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


def _month_windows(start_date: str, end_date: str) -> list[tuple[str, str, str]]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        return []

    windows: list[tuple[str, str, str]] = []
    cursor = start.replace(day=1)
    while cursor <= end:
        next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
        window_start = max(start, cursor)
        window_end = min(end, next_month - timedelta(days=1))
        windows.append((cursor.strftime("%Y-%m"), window_start.isoformat(), window_end.isoformat()))
        cursor = next_month
    return windows


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
        connect_timeout=settings.mysql_connect_timeout,
        read_timeout=settings.mysql_read_timeout,
        write_timeout=settings.mysql_write_timeout,
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
    progress_callback: Optional[Callable[..., None]] = None,
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

    store_mapping = fetch_store_mapping(source.store_mapping) if source.store_mapping.enabled else {}

    result: dict[tuple[str, str, str, str], Decimal] = {}
    for period_label, window_start, window_end in _month_windows(start_date, end_date):
        if progress_callback:
            progress_callback(stage="数仓取数", detail=f"{source.name} {period_label} 查询汇总数据", current_period=period_label)

        rows = _fetch_warehouse_rows(sql, (window_start, window_end), source.name, period_label)

        if progress_callback:
            progress_callback(
                stage="数仓取数",
                detail=f"{source.name} {period_label} 已取得 {len(rows)} 行",
                current_period=period_label,
                advance=1,
            )

        for row in rows:
            period = str(row["period"])
            store = _map_store(str(row["store"] or ""), store_mapping)
            for index, metric in enumerate(source.metrics):
                value = row.get(f"metric_{index}") or 0
                result[(period, store, metric.name, source.name)] = Decimal(str(value))
    return result


def _fetch_warehouse_rows(
    sql: str,
    params: tuple[str, str],
    source_name: str,
    period_label: str,
) -> list[dict[str, Any]]:
    last_error: OperationalError | None = None
    for attempt in range(2):
        try:
            with _warehouse_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
                    return list(cursor.fetchall())
        except OperationalError as exc:
            last_error = exc
            code = exc.args[0] if exc.args else None
            if code in {2006, 2013} and attempt == 0:
                continue
            break

    if last_error:
        raise RuntimeError(f"数仓查询失败：{source_name} {period_label}，{last_error}") from last_error
    return []


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
