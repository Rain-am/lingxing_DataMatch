from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from typing import Iterator
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from app.config import get_settings
from app.schemas import Granularity, Rule


def _quote_identifier(identifier: str) -> str:
    return f"`{identifier}`"


def _period_sql(field: str, granularity: Granularity) -> str:
    # PyMySQL uses percent-style placeholders, so literal MySQL DATE_FORMAT
    # percent signs must be escaped as %% inside the query string.
    fmt = "%%Y-%%m-%%d" if granularity == "day" else "%%Y-%%m-01"
    return f"DATE_FORMAT({_quote_identifier(field)}, '{fmt}')"


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


def fetch_warehouse_aggregate(
    rule: Rule,
    start_date: str,
    end_date: str,
    granularity: Granularity,
) -> dict[tuple[str, str, str], Decimal]:
    metric_selects: list[str] = []
    for index, metric in enumerate(rule.metrics):
        alias = f"metric_{index}"
        if metric.aggregation == "count":
            expression = "*" if metric.warehouse_expression.strip() == "*" else metric.warehouse_expression
            metric_selects.append(f"COUNT({expression}) AS `{alias}`")
        else:
            metric_selects.append(f"COALESCE(SUM({metric.warehouse_expression}), 0) AS `{alias}`")

    period_expr = _period_sql(rule.warehouse_date_field, granularity)
    table_name = _quote_identifier(rule.warehouse_table)
    date_field = _quote_identifier(rule.warehouse_date_field)
    store_field = _quote_identifier(rule.warehouse_store_field)
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

    result: dict[tuple[str, str, str], Decimal] = {}
    for row in rows:
        period = str(row["period"])
        store = str(row["store"] or "")
        for index, metric in enumerate(rule.metrics):
            value = row.get(f"metric_{index}") or 0
            result[(period, store, metric.name)] = Decimal(str(value))
    return result
